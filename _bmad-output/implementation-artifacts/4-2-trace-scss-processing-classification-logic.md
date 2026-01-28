# Story 4.2: Trace SCSS Processing & Classification Logic

Status: ready-for-dev

## Story

As a Developer,
I want to trace how SCSS styles flow through the processor and classifier,
So that I understand how style placement decisions are made and where Lexus map styles might be misclassified.

## Acceptance Criteria

**Given** the SCSS transformation pipeline
**When** I analyze `sbm/scss/processor.py` and `sbm/scss/classifiers.py`
**Then** I can document the data flow: Legacy theme → SCSS Processor → OEM Handler → Map Migrator → File placement
**And** I can identify all classification rules that determine style placement
**And** I can pinpoint where map-related styles are processed
**And** I document any Lexus-specific processing paths

## Tasks / Subtasks

- [ ] Analyze SCSS Processor initialization and flow (AC: Document data flow)
  - [ ] Document `SCSSProcessor.__init__()` setup and dependencies
  - [ ] Document `transform_scss_content()` transformation pipeline
  - [ ] Document variable processing and CSS custom property conversion
  - [ ] Document mixin parser integration (`CommonThemeMixinParser`)
- [ ] Analyze Style Classifier logic (AC: Identify classification rules)
  - [ ] Document `StyleClassifier` and `ProfessionalStyleClassifier` differences
  - [ ] Document exclusion patterns: `HEADER_PATTERNS`, `NAVIGATION_PATTERNS`, `FOOTER_PATTERNS`
  - [ ] Document `should_exclude_rule()` decision logic
  - [ ] Document `parse_css_rules()` CSS parsing strategy
- [ ] Trace map-specific SCSS processing (AC: Pinpoint map-related processing)
  - [ ] Identify where map styles enter the processor
  - [ ] Document how map styles are transformed (variable mapping, etc.)
  - [ ] Identify if map styles are subject to classification/exclusion
  - [ ] Document final output destination logic
- [ ] Identify potential misclassification scenarios (AC: Lexus-specific processing paths)
  - [ ] Check if map keyword patterns could match exclusion patterns
  - [ ] Identify edge cases where map styles might be classified as header/nav/footer
  - [ ] Document any OEM-specific processing hooks in the pipeline
  - [ ] Identify gaps in Lexus map style handling
- [ ] Create SCSS pipeline documentation (AC: Complete data flow documentation)
  - [ ] Create detailed flowchart of SCSS transformation pipeline
  - [ ] Document all decision points and classification logic
  - [ ] Document integration points with map migration
  - [ ] Save analysis in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/scss-processing-analysis.md`

## Dev Notes

### Current System Understanding

**SCSS Processing Pipeline Architecture:**

The SCSS processor is a sophisticated transformation engine that:
1. Takes legacy CommonTheme SCSS as input
2. Applies variable remapping to prevent Site Builder override conflicts
3. Parses and adapts CommonTheme mixins for Site Builder compatibility
4. Classifies styles to exclude header/footer/navigation components
5. Outputs clean, self-contained SCSS with no external @import statements

**Key Components:**

**1. SCSSProcessor (processor.py)**
- Initialization (Line 87-107):
  - Takes `slug` and `exclude_nav_styles` parameters
  - Creates `CommonThemeMixinParser` instance
  - Creates style classifier (tries `ProfessionalStyleClassifier`, falls back to `StyleClassifier`)
- Variable Mapping (Lines 21-78):
  - `VARIABLE_MAPPING`: Simple 1:1 Classic → Site Builder variable renames
  - `COMPLEX_MAPPINGS`: Multi-variable combinations (e.g., border + color)
  - `GROUP_MAPPINGS`: One Classic variable → Multiple SB variables (headings)
- Variable Processing (Lines 109-150):
  - `_process_scss_variables()`: Removes SCSS declarations, converts to CSS custom properties
  - `_convert_scss_variables_intelligently()`: Context-aware conversion (skips mixins, maps, loops)

**2. StyleClassifier (classifiers.py)**
- Exclusion Patterns (Lines 32-52):
  - **HEADER_PATTERNS**: `r"header"`, `r"\.masthead"`, `r"\.banner"`
  - **NAVIGATION_PATTERNS**: `r"\.nav"`, `r"\.navbar"`, `r"menu-item"`, `r"\.menu-"`
  - **FOOTER_PATTERNS**: `r"footer"`, `r"\.main-footer"`, `r"\.site-footer"`, etc.
- Classification Logic (Lines 70-95):
  - `should_exclude_rule()`: Checks if CSS rule matches any exclusion pattern
  - Returns tuple: (should_exclude: bool, category: str|None)
- CSS Parsing (Lines 97+):
  - `parse_css_rules()`: Parses content into complete CSS rules (not line-by-line)
  - Returns: (list of CSSRule objects, list of non-rule lines)

**Critical Integration Point:**
The map migration logic in `maps.py` calls `processor.transform_scss_content()` (Line 667):
```python
if processor:
    logger.debug(f"Transforming map SCSS content for {map_import['filename']}...")
    scss_content = processor.transform_scss_content(scss_content)
```

This means map styles go through the FULL transformation pipeline including classification/exclusion.

### Potential Misclassification Scenarios

**Scenario 1: Map styles with "nav" in selector**
- If a map component has `.map-nav` or `.directions-nav` in its selectors
- Could match `NAVIGATION_PATTERNS` like `r"\.nav"`
- Would be excluded from migration

**Scenario 2: Map styles in header/footer regions**
- If map shortcode is called within header.php or footer.php
- Selectors might include `header .map-section` or `footer .directions`
- Could match `HEADER_PATTERNS` or `FOOTER_PATTERNS`
- Would be excluded from migration

**Scenario 3: Lexus-specific selectors**
- Lexus OEM patterns: `dealer-groups/lexus/lexusoem3/section-map`
- Need to verify these DON'T match exclusion patterns
- Need to verify proper classification path

**Question for Investigation:**
- Does the map migration bypass classification, or do map styles go through exclusion logic?
- Are there OEM-specific processing hooks that Lexus handler could use?
- Is the `exclude_nav_styles` flag respected for map migrations?

### Architecture Compliance

**Data Flow Architecture:**
```
Legacy Theme SCSS
  ↓
find_commontheme_map_imports() [maps.py:242]
  ↓
migrate_map_scss_content() [maps.py:567]
  ↓
processor.transform_scss_content() [maps.py:667]
  ↓
SCSSProcessor Pipeline:
  - _process_scss_variables()
  - Mixin parser transformations
  - Style classification (if exclude_nav_styles=True)
  ↓
Append to sb-inside.scss / sb-home.scss [maps.py:688-714]
```

**Technical Stack:**
- Python regex for pattern matching (extensive use)
- No external CSS parser (custom parser in classifiers.py)
- Integration with `CommonThemeMixinParser` for mixin adaptation

**Code Structure:**
- `sbm/scss/processor.py` - Main transformation engine (~1500+ lines estimated)
- `sbm/scss/classifiers.py` - Style classification (~500+ lines estimated)
- `sbm/scss/mixin_parser.py` - CommonTheme mixin parser
- `sbm/utils/helpers.py` - Color manipulation functions (darken_hex, lighten_hex)

### Library & Framework Requirements

**Dependencies:**
- `re` - Extensive regex pattern matching
- `subprocess` - Dart Sass compilation (validation)
- `tempfile` - Temporary file operations
- `pathlib.Path` - File system operations
- `dataclasses` - CSSRule dataclass
- `typing.NamedTuple` - ExclusionResult tuple
- `logging.logger` - Logging throughout processor

**Critical Functions to Analyze:**
- `SCSSProcessor.transform_scss_content()` - Main entry point for map SCSS transformation
- `StyleClassifier.should_exclude_rule()` - Classification decision logic
- `StyleClassifier.parse_css_rules()` - CSS parsing strategy
- `ProfessionalStyleClassifier` - Enhanced parser (need to understand differences)

### File Structure Requirements

**Analysis Output Location:**
- Primary documentation: `_bmad-output/planning-artifacts/lexus-map-migration-analysis/`
- SCSS analysis: `scss-processing-analysis.md`
- Pipeline flowchart: `scss-pipeline-flowchart.md` (Mermaid format)
- Classification matrix: `style-classification-matrix.md` (pattern matching table)

**Files to Analyze:**
- ✅ `sbm/scss/processor.py` - Partially read (first 150 lines)
- ✅ `sbm/scss/classifiers.py` - Partially read (first 100 lines)
- Required: Complete read of both files
- Required: `sbm/scss/mixin_parser.py` - For mixin transformation understanding
- Optional: `sbm/utils/helpers.py` - For variable transformation helpers

### Testing Requirements

**Analysis Validation:**
- Must trace COMPLETE data flow from input to output
- Must document ALL classification patterns with examples
- Must identify specific misclassification scenarios for Lexus map styles
- Must provide evidence from actual code (line numbers, function names)

**Evidence Requirements:**
- Quote specific classification patterns
- Document actual transformation steps with code examples
- Identify integration points with map migration (function calls, parameters)
- Create example: "Given selector X, processor does Y, output is Z"

### Previous Story Intelligence

**From Story 4.1:**
- Identified that map SCSS content is passed to `processor.transform_scss_content()` (maps.py:667)
- Documented that map styles are appended to `sb-inside.scss` and `sb-home.scss`
- Identified differentiation between "implicit" (shortcode-derived) and "explicit" (style.scss imports)
- Established that Lexus handler has `should_force_map_migration()` returning True

**Questions from 4.1 to Answer in 4.2:**
1. Does `transform_scss_content()` apply classification/exclusion to map styles?
2. Could map selectors accidentally match header/nav/footer exclusion patterns?
3. Are there OEM-specific hooks in the processor for Lexus customization?
4. What is the difference between `StyleClassifier` and `ProfessionalStyleClassifier`?

### Git Intelligence Summary

No recent changes to SCSS processor or classifiers. Last modifications were part of v2.0 refactoring. Code is stable but may have latent bugs in classification logic that haven't been triggered until Lexus map migrations.

**Important:** This is still a **pure analysis story** - NO CODE CHANGES. Only documentation artifacts.

### Latest Tech Information

**CSS Parsing Best Practices:**
- Modern approach: Use tinycss2 or cssutils for robust parsing
- Current implementation: Custom regex-based parser (faster but more brittle)
- Edge cases to consider: Media queries, nested selectors, comma-separated selectors

**SCSS Variable Handling:**
- SCSS variables ($var) are compile-time
- CSS custom properties (--var) are runtime
- Processor converts SCSS → CSS custom properties for SB compatibility

### Project Context Reference

From CLAUDE.md:
- Analysis docs go in `_bmad-output/planning-artifacts/`
- Must be evidence-based with specific line numbers and code quotes
- Create visual flowcharts using Mermaid.js
- Document must be comprehensive enough for implementation team

### Story Completion Status

**Status:** ready-for-dev

**Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created. This story builds directly on Story 4.1's findings and will enable Story 4.3's PR analysis by providing complete understanding of the transformation pipeline.

**Next Steps:**
1. Run `dev-story` workflow to execute this analysis story
2. Output will be SCSS pipeline documentation in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/`
3. Story 4.3 will use this understanding to analyze specific problem PRs with classification context
4. Story 4.4 will combine both analyses for historical comparison

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
