# Map Migration Logic Analysis

## Overview
This document analyzes the current logic in `sbm/core/maps.py` for identifying and migrating map components. The analysis is based on code version `2.0.0` (as per `CLAUDE.md`).

## 1. Orchestration Flow (`migrate_map_components`)

The main entry point is `migrate_map_components(slug, oem_handler, interactive, console, processor)`. It orchestrates the migration in a multi-phase approach:

### Phase 1: Detection
1.  **Direct Import Detection (`find_commontheme_map_imports`)**:
    *   Scans `css/style.scss` in the dealer theme.
    *   Looks for `@import` statements referencing CommonTheme files.
    *   Matches filenames against OEM-specific patterns (if provided by `oem_handler`) or generic keywords.
    *   **Generic Keywords**: `mapsection`, `section-map`, `map-row`, `maprow`, `map_rt`,
        `mapbox`, `mapboxdirections`, `full-map`, `get-directions`, `getdirections`.
    *   **Regex**: `DealerInspireCommonTheme[^'\"]*(?:/|_)\b(?:{keyword_list})`

2.  **Shortcode/Partial Detection (`find_map_shortcodes_in_functions`)**:
    *   Scans `functions.php` and recursively follows `require/include` statements to shared function files (specifically looking for paths containing "dealer-groups" or filenames containing "function").
    *   **Shortcode Registration**: Looks for `add_shortcode('full-map', ...)` and extracts the handler function name.
    *   **Template Part Extraction**:
        *   Inside the handler function body, looks for `get_template_part('path/to/partial')`.
        *   Also scans the global scope of the file for `get_template_part` calls matching map keywords.
        *   Specifically looks for `homecontent-getdirections`.

3.  **Partial-Derived SCSS (`derive_map_imports_from_partials`)**:
    *   If partials are found via shortcodes, it attempts to guess the corresponding SCSS file in CommonTheme.
    *   Rule: `partials/path/to/file` -> `css/path/to/file.scss`.

### Phase 2: Logic Branching
*   **No Components Found**: If neither imports nor shortcodes/partials are found, migration skips and reports "none_found".
*   **Imports Only**: Proceeds to migrate partials corresponding to those imports.
*   **Shortcodes Only**: Proceeds to migrate partials found via shortcodes AND derives SCSS from them.
*   **Both Found**: Merges the lists.

### Phase 3: SCSS Migration (`migrate_map_scss_content`)
*   **Target Selection**:
    *   CRITICAL DECISION: Only "implicit" imports (derived from shortcodes) are migrated here.
    *   "Explicit" imports (found in `style.scss`) are SKIPPED here because they are handled by the main style migration process (inlining).
*   **Deduplication**: Checks `sb-inside.scss`, `sb-home.scss`, and `style.scss` to see if the file is already imported/present.
*   **Transformation**: Uses `SCSSProcessor` (if available) to transform content.
*   **Output**: Appends content to `sb-inside.scss` and `sb-home.scss` with a `/* === MAP COMPONENTS === */` marker.

### Phase 4: Partial Migration (`migrate_map_partials`)
*   **Target Selection**: Migrates partials found via imports (guessing `css/` -> `partials/` logic was REMOVED in code but `guess_partial_paths_from_scss` exists - logic in `migrate_map_partials` relies on `find_template_parts_in_file` and `extra_partials` from shortcodes).
*   **Copy Logic (`copy_partial_to_dealer_theme`)**:
    1.  Checks if partial already exists in Dealer Theme (Skipped if exists).
    2.  Checks for EXACT match in CommonTheme.
    3.  Checks for FUZZY match in CommonTheme (if exact missing): `*{keyword}*.php`.
    4.  **Inheritance Check**: If file exists in CommonTheme, it returns `skipped_inheritance` and DOES NOT COPY. *This is a key logic point - it relies on WordPress template hierarchy.*
    5.  **Fallback**: If strict and fuzzy fail, asks user (interactive) or skips (non-interactive).

## 2. Key Logic & Patterns

### Keyword Lists
`MAP_KEYWORDS` constant defines the universe of "map" components:
```python
MAP_KEYWORDS = [
    "mapsection", "section-map", "map-row", "maprow", "map_rt",
    "mapbox", "mapboxdirections", "full-map", "get-directions", "getdirections"
]
```

### OEM-Specific Handling
The code supports `oem_handler.get_map_partial_patterns()`. If an OEM handler provides this, the generic keyword search is REPLACED by the OEM-specific patterns.

### Conditional Logic Analysis
*   **Inheritance vs Copy**: The system prefers inheritance (`skipped_inheritance`) over copying. It only copies if it *can't* find the file in CommonTheme? No, wait.
    *   `if commontheme_source.exists(): return "skipped_inheritance"`
    *   This implies it **NEVER** copies partials if they exist in CommonTheme. This assumes the Dealer Theme will inherit them.
    *   **POTENTIAL ISSUE**: If the Dealer Theme structure changes or if we are moving away from CommonTheme dependency, this logic prevents the file from being brought over.

*   **SCSS Placement**:
    *   Implicit (Shortcode-derived) -> `sb-inside.scss` & `sb-home.scss`.
    *   Explicit (style.scss import) -> Inlined into `style.scss` (by separate process).

## 3. Potential Failure Modes Identified
1.  **Recursion Limit**: `find_map_shortcodes_in_functions` has a hard limit of 100 files. Complex themes might exceed this.
2.  **Inheritance Assumption**: `copy_partial_to_dealer_theme` explicitly skips copying if the file exists in CommonTheme. If the goal of SBM is to decouple from CommonTheme, this logic is counter-productive for partials.
3.  **SCSS Context**: Implicit SCSS is dumped into `sb-inside` and `sb-home`. If the map relies on variables defined in `style.scss` but not available in the Site Builder context (unlikely but possible), styles might break.
4.  **Regex Fragility**: `MAP_REGEX_PATTERN` assumes keywords are surrounded by non-word characters `\W`. `foo-mapsection` might be missed if it's not `foo-mapsection`.

## 4. SCSS Migration & Style Placement (`migrate_map_scss_content`)

This section details the specific logic for how SCSS content is targeted, transformed, and placed.

### Decision Logic: File Placement
The system makes a binary decision based on the **source** of the map component:

| Source Type | Detected Via | Action | Destination | Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Explicit Import** | `@import` in `style.scss` | **SKIP** | `style.scss` (Inlined) | Handled by main `migrate_styles` process. Re-migrating here would cause duplication. |
| **Implicit Import** | Derived from Shortcode/Partial | **MIGRATE** | `sb-inside.scss` AND `sb-home.scss` | These styles are NOT in `style.scss`, so they must be explicitly added to Site Builder files to ensure they load. |

### Deduplication Logic
Before appending content, the system performs a pre-scan check:
1.  **Reads Check Files**: Scans `sb-inside.scss`, `sb-home.scss`, `style.scss`, `inside.scss` (legacy), and `css/style.scss`.
2.  **Extracts Base Names**: Finds all existing `@import` filenames (e.g., `_map-row.scss` -> `map-row`).
3.  **Comparison**: If the map component's filename (base) exists in ANY of these files, it skips migration.
    *   *Log*: "Skipping SCSS migration for {base} (already imported)"

### Content Transformation
If a `processor` (SCSSProcessor) is available:
*   The content is passed through `processor.transform_scss_content()`.
*   This likely handles path adjustments, variable replacements, or syntax modernization (detailed analysis of `processor.py` pending in Story 4.2).

### File Targeting
For Implicit Imports, content is appended to **BOTH**:
1.  `sb-inside.scss`: For inner pages.
2.  `sb-home.scss`: For the home page.
*   **Marker**: A comment `/* === MAP COMPONENTS === */` is added to section off these styles.

## 5. PHP Partial Migration (`migrate_map_partials`)

This section details how PHP template parts are identified and handled.

### Detection Logic (`find_template_parts_in_file`)
The system scans `front-page.php`, `index.php`, `page.php`, `home.php`, `functions.php`, and all files in `partials/`.

1.  **Regex Matching**:
    *   **Generic**: `get_template_part\s*\(\s*['\"]([^'\"]*\b(?:{MAP_KEYWORDS})\b[^'\"]*)['\"]`
    *   **Shortcode Function**: Looks for `function ... { ... get_template_part(...) ... }` blocks where the function name matches map keywords.
    *   **Home Content**: Specifically looks for `homecontent-getdirections`.

2.  **OEM Overrides**:
    *   If `oem_handler` is present and has `get_map_partial_patterns()`, those patterns **completely replace** the generic keyword search.

### Copy Logic (`copy_partial_to_dealer_theme`)
This function handles the physical file transfer and decision making.

1.  **Existence Check (Dealer Theme)**:
    *   If `path/to/partial.php` already exists in the Dealer Theme, it returns `already_exists`.
    *   *Action*: No copy.

2.  **Existence Check (CommonTheme)**:
    *   Looks for exact match in CommonTheme.
    *   **Fuzzy Matching**: If exact match fails, it looks for `*{filename}*.php` in the same directory.
        *   *Example*: `map-section` might match `_map-section.php`.

3.  **Inheritance Logic (CRITICAL)**:
    *   If the file exists in CommonTheme (either exact or fuzzy match), the system returns `skipped_inheritance`.
    *   **Implication**: **Files found in CommonTheme are NEVER copied to the Dealer Theme automatically.**
    *   *Reasoning*: WordPress child themes inherit template parts. If we don't need to modify it, we shouldn't copy it (reduces maintenance burden).
    *   *Risk*: If SBM is intended to produce a standalone theme (breaking CommonTheme dependency), this logic is **INCORRECT**.

4.  **Fallback**:
    *   If not found in CommonTheme even after fuzzy matching:
        *   **Interactive**: Prompts user (suggests similar files).
        *   **Non-Interactive**: Returns `skipped_missing`.

## 6. Lexus OEM Handler (`sbm/oem/lexus.py`)

The `LexusHandler` overrides default behavior with specific patterns and flags.

### Regex Patterns (`get_map_partial_patterns`)
These patterns replace the generic keyword search when the site is identified as Lexus.

1.  `r"dealer-groups/lexus/lexusoem\d+/_?section-map"`
    *   Matches: `dealer-groups/lexus/lexusoem1/section-map` (and with underscore)
    *   Note: Specific to `lexusoem` followed by digits.

2.  `r"dealer-groups/lexus/lexusoem\d+/mapsection\d*"`
    *   Matches: `dealer-groups/lexus/lexusoem2/mapsection` or `mapsection1`

3.  `r"dealer-groups/([^/]+)/map-row-\d+"`
    *   Matches: `dealer-groups/ANYTHING/map-row-1`
    *   **BROAD**: This captures map-rows from *other* dealer groups if referenced? No, `([^/]+)` is within `dealer-groups/`.

4.  `r"dealer-groups/([^/]+)/directions"`
5.  `r"dealer-groups/([^/]+)/location"`

### Forced Migration (`should_force_map_migration`)
*   Returns `True`.
*   **Impact**: This method exists in the class but is **NOT USED** in `sbm/core/maps.py`.
    *   *Code Audit*: `grep "should_force_map_migration" sbm/core/maps.py` yields NO results.
    *   *Conclusion*: This flag is currently dead code or used in a part of the system not analyzed here (checked `base.py` usage? No, only defined).

### Differences from Default
*   **Strictness**: Lexus handler relies on directory structure (`dealer-groups/lexus/...`) rather than just filename keywords.
*   **Specificity**: Targeted at `lexusoem#` folders.
*   **Missing Keywords**: Does NOT include generic `mapbox` or `getdirections` unless they match the directory patterns above. This might be why some map components are missed if they don't follow the `dealer-groups` structure strictly.
