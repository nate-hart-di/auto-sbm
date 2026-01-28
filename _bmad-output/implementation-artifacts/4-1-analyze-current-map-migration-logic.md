# Story 4.1: Analyze Current Map Migration Logic

Status: ready-for-dev

## Story

As a Developer,
I want to thoroughly analyze the existing `sbm/core/maps.py` and `sbm/oem/lexus.py` code,
So that I understand exactly how map components are currently identified and migrated for Lexus sites.

## Acceptance Criteria

**Given** the codebase with map migration logic
**When** I read and analyze `sbm/core/maps.py` and `sbm/oem/lexus.py`
**Then** I can document the complete logic flow for map component detection
**And** I can explain the decision logic for placing styles in `sb-inside.scss` vs `style.scss`
**And** I can identify all conditionals, pattern matching, and OEM-specific handling
**And** I create a flowchart or detailed documentation of the current process

## Tasks / Subtasks

- [ ] Analyze map detection logic in maps.py (AC: Complete logic flow documentation)
  - [ ] Document `migrate_map_components()` orchestration flow
  - [ ] Document `find_commontheme_map_imports()` pattern matching
  - [ ] Document `find_map_shortcodes_in_functions()` shortcode detection
  - [ ] Document `derive_map_imports_from_partials()` fallback logic
- [ ] Analyze SCSS migration logic (AC: Explain style placement decisions)
  - [ ] Document `migrate_map_scss_content()` file targeting
  - [ ] Document when styles go to `sb-inside.scss` vs `sb-home.scss` vs `style.scss`
  - [ ] Document the deduplication and pre-scan logic
- [ ] Analyze PHP partial migration logic (AC: Identify OEM-specific handling)
  - [ ] Document `migrate_map_partials()` flow
  - [ ] Document `find_template_parts_in_file()` pattern detection
  - [ ] Document `copy_partial_to_dealer_theme()` with fuzzy matching
- [ ] Analyze Lexus OEM handler (AC: Document all conditionals)
  - [ ] Document `LexusHandler.get_map_partial_patterns()` regex patterns
  - [ ] Document `should_force_map_migration()` behavior
  - [ ] Identify how Lexus patterns differ from default/other OEMs
- [ ] Create comprehensive documentation artifact (AC: Flowchart/detailed docs)
  - [ ] Create visual flowchart showing decision tree
  - [ ] Document entry points and exit conditions
  - [ ] Document all keyword lists and regex patterns used
  - [ ] Create summary document in `_bmad-output/planning-artifacts/`

## Dev Notes

### Current System Understanding

**Map Migration Architecture:**
The system uses a multi-phase detection approach:

1. **Phase 1: Direct Import Detection** - Scans `style.scss` for CommonTheme @import statements containing map keywords
2. **Phase 2: Shortcode Detection** - Scans `functions.php` and included files for map shortcode registrations
3. **Phase 3: Partial Derivation** - Derives SCSS paths from discovered PHP partials
4. **Phase 4: SCSS Migration** - Appends transformed SCSS content to `sb-inside.scss` and `sb-home.scss`
5. **Phase 5: Partial Migration** - Copies PHP template parts from CommonTheme to DealerTheme

**Critical Detection Patterns:**
- **MAP_KEYWORDS** (Line 25-36 in maps.py): Core keywords for detection
  - `mapsection`, `section-map`, `map-row`, `maprow`, `map_rt`, `mapbox`, `mapboxdirections`, `full-map`, `get-directions`, `getdirections`
- **Lexus-Specific Patterns** (lexus.py:35-41):
  - `dealer-groups/lexus/lexusoem\d+/_?section-map`
  - `dealer-groups/lexus/lexusoem\d+/mapsection\d*`
  - `dealer-groups/([^/]+)/map-row-\d+`
  - Additional patterns for `directions`, `location`

**Style Placement Logic:**
- **Implicit imports** (derived from shortcodes): Migrated to `sb-inside.scss` and `sb-home.scss`
- **Explicit imports** (found in style.scss): Handled by main migrate_styles process (inlined into style.scss)
- **Deduplication**: Pre-scans existing SCSS files to avoid duplicate content

**Key Design Decision (Lines 161-164):**
```python
# CHANGE: We ONLY migrate SCSS for 'implicit' imports (derived from shortcodes) here.
# 'Explicit' imports found in style.scss (map_imports detected above) are handled
# by the main migrate_styles process (which inlines them into style.scss).
# Migrating them here again would cause duplication (once in style.scss, once in sb-inside.scss).
```

### Architecture Compliance

**Technical Stack:**
- Python 3.9+ with regex-based parsing
- No external SCSS parser dependency (uses tinycss2 indirectly via processor)
- Integration points: `SCSSProcessor` for content transformation (Line 109-112)

**Code Structure:**
- `sbm/core/maps.py` - Main map migration orchestration (1134 lines)
- `sbm/oem/lexus.py` - Lexus-specific OEM handler (50 lines)
- `sbm/oem/base.py` - BaseOEMHandler abstract class
- Integration with `sbm/scss/processor.py` for SCSS transformation

**Security Requirements:**
- File system operations with proper error handling
- Safe path resolution to prevent directory traversal
- UTF-8 encoding with error handling for international characters

**Testing Standards:**
- Current test coverage unknown (needs investigation)
- Should have unit tests for pattern matching logic
- Should have integration tests for full migration flow

### Library & Framework Requirements

**Dependencies:**
- `pathlib.Path` - File system operations
- `re` - Regex pattern matching (extensive use)
- `shutil` - File copying operations
- `click` - CLI interaction (interactive mode)
- `sbm.ui.console.SBMConsole` - UI output
- `sbm.utils.logger.logger` - Logging

**Critical Constants:**
- `COMMON_THEME_DIR` (Line 21): `/Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme`
- `MAP_KEYWORDS` (Line 25-36): List of map-related keywords
- `MAP_REGEX_PATTERN` (Line 39): Compiled regex pattern for map detection

### File Structure Requirements

**Analysis Output Location:**
- Primary documentation: `_bmad-output/planning-artifacts/lexus-map-migration-analysis/`
- Create subdirectory: `current-logic-analysis/`
- Flowchart: Save as `map-migration-flowchart.md` (Mermaid format)
- Detailed analysis: Save as `map-migration-logic-analysis.md`

**Files to Analyze:**
- ✅ `sbm/core/maps.py` - Already read (1134 lines)
- ✅ `sbm/oem/lexus.py` - Already read (50 lines)
- Required: `sbm/oem/base.py` - Need to read for BaseOEMHandler interface
- Required: `sbm/oem/default.py` - Need to read for DefaultHandler comparison
- Optional: `sbm/scss/processor.py` - For understanding transformation logic
- Optional: `sbm/scss/classifiers.py` - For understanding style classification

### Testing Requirements

**Analysis Validation:**
- Document must be comprehensive enough for another developer to understand the system
- Flowchart must cover all decision paths
- Pattern documentation must include actual regex with examples
- Must identify at least 3 potential failure modes from code inspection

**Evidence Requirements:**
- Quote specific line numbers from source code
- Include actual regex patterns and keyword lists
- Document all entry points and function call chains
- Identify all file system operations and their paths

### Previous Story Intelligence

No previous story in this epic. This is the first story in Epic 4 (Lexus Map Migration Analysis).

### Git Intelligence Summary

Recent commits show active development on Firebase sync and stats features (Epics 1 & 2):
- Focus has been on `sbm/cli.py`, `sbm/utils/firebase_sync.py`, `sbm/oem/base.py`, `sbm/oem/factory.py`
- Map migration code (`sbm/core/maps.py`) has NOT been modified recently
- Lexus handler (`sbm/oem/lexus.py`) is a newly created file (shows in untracked)
- This epic is completely independent of recent Firebase work

**Important:** This is a **pure analysis story** - NO CODE CHANGES should be made to map migration logic. Only documentation artifacts should be created.

### Latest Tech Information

**Documentation Tools:**
- Mermaid.js for flowcharts (supported in Markdown)
- GitHub-flavored Markdown for technical documentation
- Use code fencing with language identifiers for syntax highlighting

**Analysis Best Practices:**
- Start with entry point functions and trace execution paths
- Document decision points (if/else, pattern matching)
- Identify all external dependencies and file system operations
- Look for edge cases and error handling gaps

### Project Context Reference

From CLAUDE.md:
- File organization: Analysis docs go in `_bmad-output/planning-artifacts/`
- All PRPs go in `PRPs/` directory (if creating any supporting docs)
- Documentation uses GitHub-flavored Markdown
- Code quality: Document must be thorough and evidence-based

### Story Completion Status

**Status:** ready-for-dev

**Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created. This story is ready for implementation by a dev agent.

**Next Steps:**
1. Run `dev-story` workflow to execute this analysis story
2. Output will be comprehensive documentation in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/`
3. Story 4.2 will build on this analysis to trace SCSS processing flow
4. Story 4.3 will use this understanding to analyze specific problem PRs

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
