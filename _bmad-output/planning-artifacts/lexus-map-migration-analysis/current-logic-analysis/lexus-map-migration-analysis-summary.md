# Map Migration Logic Analysis Summary

**Date:** 2026-01-28
**Story:** 4.1 Analyze Current Map Migration Logic
**Scope:** `sbm/core/maps.py` and `sbm/oem/lexus.py`

## Executive Summary
The current map migration logic employs a multi-phase detection strategy (Imports -> Shortcodes -> Partials) with specific handling for Lexus dealers. While robust in its primary detection methods, it relies on several critical assumptions (inheritance, file existence) that may cause failures in edge cases.

## Key Findings

1.  **Orchestration**: The system prioritizes "Implicit" imports (derived from shortcodes) for migration to Site Builder files (`sb-inside.scss`, `sb-home.scss`). Explicit imports found in `style.scss` are explicitly skipped here to be handled by the main inlining process.
2.  **Lexus Handling**: The `LexusHandler` uses strict directory-based regex patterns (`dealer-groups/lexus/...`) instead of generic keywords. This increases precision but may miss non-standard file locations.
3.  **Dead Code**: The `should_force_map_migration()` method in `LexusHandler` appears to be unused in the core logic.
4.  **Inheritance Assumption**: The system **intentionally skips** copying PHP partials if they exist in the CommonTheme, assuming WordPress template inheritance will handle them. This is a potential failure point if the goal is standalone theme generation.

## Artifacts
*   **Detailed Logic Analysis**: [map-migration-logic-analysis.md](map-migration-logic-analysis.md)
*   **Logic Flowchart**: [map-migration-flowchart.md](map-migration-flowchart.md)

## Recommendations for Next Steps
1.  **Verify Inheritance**: Confirm if the `skipped_inheritance` logic aligns with the project's "standalone" goals.
2.  **Audit Regex**: The generic `MAP_REGEX_PATTERN` requires non-word boundaries (`\W`), which might miss hyphenated keywords in some contexts.
3.  **Clean Up**: Remove unused methods like `should_force_map_migration` if confirmed dead.
