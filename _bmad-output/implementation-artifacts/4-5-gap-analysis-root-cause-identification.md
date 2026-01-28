# Story 4.5: Gap Analysis & Root Cause Identification

Status: ready-for-dev

## Story

As a Developer,
I want to compare successful vs failed migrations to pinpoint exact failure conditions,
So that I can definitively state why certain Lexus sites fail while others succeed.

## Acceptance Criteria

**Given** data from successful migrations and failed migrations
**When** I perform comparative analysis
**Then** I identify the exact differences in SCSS patterns between successful and failed sites
**And** I document edge cases and conditions that trigger failures
**And** I explain why the current logic fails for `lexusofatlanticcity`, `tustinlexus`, `lexusofalbuquerque`
**And** I explain why it succeeded for other Lexus sites
**And** I document all root causes with evidence from PR data

## Tasks / Subtasks

- [ ] Comparative pattern analysis (AC: Identify exact differences)
  - [ ] Create side-by-side comparison of successful vs failed site patterns
  - [ ] Compare CommonTheme import paths (successful vs failed)
  - [ ] Compare selector patterns (successful vs failed)
  - [ ] Compare keyword matches (successful vs failed)
  - [ ] Compare file structure and partial locations (successful vs failed)
- [ ] Classification mismatch analysis (AC: Document edge cases)
  - [ ] Check if failed sites have selectors matching exclusion patterns
  - [ ] Verify if map styles were detected but misclassified
  - [ ] Identify if SCSS processor excluded map styles as header/nav/footer
  - [ ] Document specific selectors that triggered misclassification
- [ ] Detection logic gap analysis (AC: Explain why logic fails)
  - [ ] Identify patterns in failed sites NOT covered by MAP_KEYWORDS
  - [ ] Identify Lexus handler patterns that don't match failed site imports
  - [ ] Check if shortcode detection missed custom shortcodes
  - [ ] Verify if partial derivation logic failed for failed sites
- [ ] Success factor validation (AC: Explain why succeeded for others)
  - [ ] Confirm successful sites match MAP_KEYWORDS patterns
  - [ ] Confirm successful sites match Lexus handler patterns
  - [ ] Confirm successful sites don't match exclusion patterns
  - [ ] Identify what successful sites have that failed sites lack
- [ ] Root cause documentation (AC: Document all root causes with evidence)
  - [ ] Root Cause 1: [Specific detection failure with evidence]
  - [ ] Root Cause 2: [Specific classification failure with evidence]
  - [ ] Root Cause 3: [Specific transformation failure with evidence]
  - [ ] Root Cause N: [Additional causes if identified]
- [ ] Create comprehensive gap analysis and root cause report
  - [ ] Save report in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/gap-analysis-root-cause.md`
  - [ ] Include comparison tables and evidence
  - [ ] Include specific line numbers and code references
  - [ ] Include recommendations for Epic 5 (solution strategy)

## Dev Notes

### Current System Understanding

**Analysis Inputs:**

**From Story 4.1:**
- Complete understanding of map detection logic
- MAP_KEYWORDS list and Lexus patterns
- Detection flow: imports → shortcodes → partials → migration

**From Story 4.2:**
- Complete understanding of SCSS processor pipeline
- Classification patterns that could exclude map styles
- Style placement decision logic

**From Story 4.3:**
- Concrete evidence from 3 failed sites
- Actual file changes and selector patterns
- Error messages and manual fixes

**From Story 4.4:**
- Baseline of successful patterns
- Categorization of success patterns
- Frequency analysis of keywords and selectors

**Analysis Methodology:**
```
Step 1: For each failed site
  - Extract: CommonTheme imports, selectors, keywords

Step 2: Compare with successful baseline
  - Which successful category is most similar?
  - What differences exist?

Step 3: Trace through detection logic
  - Would MAP_KEYWORDS detect this pattern? (Story 4.1)
  - Would Lexus handler detect this pattern? (Story 4.1)
  - Would shortcode detection find this? (Story 4.1)

Step 4: Trace through classification logic
  - Would any selector match exclusion patterns? (Story 4.2)
  - Would SCSS processor exclude these styles? (Story 4.2)

Step 5: Identify gap
  - Detection gap: Pattern not covered by keywords/handler
  - Classification gap: Pattern incorrectly excluded
  - Transformation gap: Pattern detected but not migrated correctly

Step 6: Document root cause
  - Specific pattern that causes failure
  - Specific code logic that mishandles pattern
  - Evidence from actual failed PRs
```

**Expected Root Cause Categories:**

1. **Detection Failure**
   - Pattern exists but not covered by MAP_KEYWORDS
   - CommonTheme import path doesn't match Lexus handler patterns
   - Shortcode not detected due to custom naming
   - Partial path derivation logic incorrect

2. **Classification Failure**
   - Map selector matches exclusion pattern (header/nav/footer)
   - SCSS processor incorrectly excludes map styles
   - Style placed in wrong file due to classification

3. **Transformation Failure**
   - SCSS processor transformation breaks selectors
   - Variable mapping causes style issues
   - Mixin parser fails on map-specific mixins

4. **Integration Failure**
   - Map migration runs but styles not appended
   - File write operation fails or is skipped
   - Deduplication logic incorrectly skips new content

### Architecture Compliance

**Root Cause Documentation Format:**
```markdown
## Root Cause 1: [Title]

**Failure Condition:**
The system fails when [specific condition].

**Evidence:**
- Failed Site: lexusofatlanticcity
- PR: 21434
- Selector: `.section-map-wrapper .directions-box`
- Expected: Append to `sb-inside.scss`
- Actual: Stayed in `style.scss`

**Code Reference:**
File: `sbm/core/maps.py`
Function: `find_commontheme_map_imports()`
Line: 275
Logic: Pattern matching uses `r"DealerInspireCommonTheme[^'\"]*(?:/|_)\\b(?:{keyword_list})"`

**Why It Failed:**
The import path is `dealer-groups/lexus/lexusoem3/homecontent-directions`
The keyword `directions` is in MAP_KEYWORDS, but the pattern requires `\\b` (word boundary)
The path has `homecontent-directions` which doesn't have word boundary before `directions`
Pattern: `homecontent-directions` doesn't match `\\b(?:directions)\\b`

**Successful Comparison:**
Successful sites have: `dealer-groups/lexus/lexusoem2/section-map`
Pattern matches: `\\b(?:section-map)\\b` ✓

**Fix Required:**
Remove word boundary requirement or add compound keywords like `homecontent-directions` to MAP_KEYWORDS.
```

### Library & Framework Requirements

**Analysis Tools:**
- Python `difflib` - For text diffing and comparison
- Python `re` - For pattern testing and validation
- Python `json` - For loading data from previous stories
- Visual diff tools - For side-by-side comparison

**Pattern Testing:**
```python
import re

# Test if failed site pattern matches keyword regex
failed_pattern = "homecontent-directions"
keyword_list = "|".join([re.escape(k) for k in MAP_KEYWORDS])
regex = f"\\b(?:{keyword_list})\\b"

if re.search(regex, failed_pattern, re.IGNORECASE):
    print("MATCH: Would be detected")
else:
    print("NO MATCH: Would NOT be detected")
```

### File Structure Requirements

**Output Structure:**
```
_bmad-output/planning-artifacts/lexus-map-migration-analysis/
├── current-logic-analysis/ (Story 4.1)
├── scss-processing-analysis.md (Story 4.2)
├── pr-analysis/ (Story 4.3)
│   ├── pr-21434-lexusofatlanticcity.md
│   └── ...
├── historical-analysis.md (Story 4.4)
│   └── data/merged-dataset.json
└── gap-analysis-root-cause.md (THIS STORY)
    └── evidence/
        ├── pattern-comparison-tables.md
        ├── detection-logic-trace.md
        └── classification-logic-trace.md
```

**Gap Analysis Report Template:**
```markdown
# Gap Analysis & Root Cause Identification

## Executive Summary
This analysis compares 3 failed Lexus sites against XX successful sites to identify exact failure conditions.

**Failed Sites:**
- lexusofatlanticcity (PR 21434)
- tustinlexus (PR 21462)
- lexusofalbuquerque (PR 21393)

**Key Findings:**
1. Root Cause 1: [Summary]
2. Root Cause 2: [Summary]
3. Root Cause 3: [Summary]

## Comparative Pattern Analysis

### Failed Site Patterns
| Site | CommonTheme Import | Selectors | Keywords | File Placement |
|------|-------------------|-----------|----------|----------------|
| lexusofatlanticcity | ... | ... | ... | style.scss (incorrect) |
| tustinlexus | ... | ... | ... | style.scss (incorrect) |
| lexusofalbuquerque | ... | ... | ... | missing |

### Successful Site Patterns (Sample)
| Site | CommonTheme Import | Selectors | Keywords | File Placement |
|------|-------------------|-----------|----------|----------------|
| lexusofbradenton | ... | ... | ... | sb-inside.scss (correct) |
| ... | ... | ... | ... | ... |

### Pattern Differences
1. **Import Path Format:**
   - Failed: `dealer-groups/lexus/lexusoem3/homecontent-directions`
   - Successful: `dealer-groups/lexus/lexusoem2/section-map`
   - Difference: Compound keyword (`homecontent-directions`) vs simple keyword (`section-map`)

2. **Selector Patterns:**
   - Failed: `.homecontent .directions-wrapper`
   - Successful: `.section-map .map-container`
   - Difference: [Explain]

3. **Shortcode Usage:**
   - Failed: `[full-map]` not detected or custom shortcode
   - Successful: `[full-map]` detected correctly
   - Difference: [Explain]

## Detection Logic Trace

### Test Case: lexusofatlanticcity
**Input:** CommonTheme import `dealer-groups/lexus/lexusoem3/homecontent-directions`

**Step 1: Check MAP_KEYWORDS**
```python
keyword_list = "mapsection|section-map|map-row|maprow|map_rt|mapbox|mapboxdirections|full-map|get-directions|getdirections"
pattern = f"\\b(?:{keyword_list})\\b"
match = re.search(pattern, "homecontent-directions", re.IGNORECASE)
# Result: NO MATCH (word boundary issue)
```

**Step 2: Check Lexus Handler Patterns**
```python
lexus_patterns = [
    r"dealer-groups/lexus/lexusoem\d+/_?section-map",
    r"dealer-groups/lexus/lexusoem\d+/mapsection\d*",
    ...
]
match = any(re.search(p, "dealer-groups/lexus/lexusoem3/homecontent-directions") for p in lexus_patterns)
# Result: NO MATCH (none of the patterns match "homecontent-directions")
```

**Conclusion:** Import would NOT be detected by current logic.

### Test Case: [Successful Site]
**Input:** CommonTheme import `dealer-groups/lexus/lexusoem2/section-map`

**Step 1: Check MAP_KEYWORDS**
```python
match = re.search(pattern, "section-map", re.IGNORECASE)
# Result: MATCH ✓
```

**Conclusion:** Import would be detected.

## Classification Logic Trace

### Test Case: lexusofatlanticcity Selectors
**Input:** Selectors from map styles

**Step 1: Check Exclusion Patterns**
```python
header_patterns = [r"header", r"\.masthead", r"\.banner"]
nav_patterns = [r"\.nav", r"\.navbar", r"menu-item", r"\.menu-"]
footer_patterns = [r"footer", r"\.main-footer", ...]

selector = ".homecontent .directions-wrapper"
excluded = any(re.search(p, selector, re.IGNORECASE) for p in all_patterns)
# Result: [TRUE/FALSE - document which pattern matched if excluded]
```

**Conclusion:** [Would/Would Not] be excluded by classifier.

## Root Causes

### Root Cause 1: Compound Keyword Detection Failure

**Failure Condition:**
When CommonTheme import path contains compound keywords (e.g., `homecontent-directions` instead of `directions`), the word boundary regex pattern `\\b(?:directions)\\b` fails to match because `directions` is not preceded by a word boundary.

**Evidence:**
- Failed sites use: `homecontent-directions`, `homecontent-getdirections`, `lexusoem3-mapsection`
- Successful sites use: `section-map`, `mapsection`, `map-row`
- Code: `sbm/core/maps.py:275` - Pattern requires word boundaries

**Impact:**
- Failed sites: 3 (100% of analyzed failures)
- Successful sites: 0 (none use compound keywords)

**Code Reference:**
```python
# sbm/core/maps.py:275
keyword_list = "|".join([re.escape(k) for k in MAP_KEYWORDS])
search_patterns = [f"DealerInspireCommonTheme[^'\"]*(?:/|_)\\b(?:{keyword_list})"]
```

**Fix Required:**
1. Remove word boundary requirement: Change `\\b(?:keyword)\\b` to `(?:keyword)`
2. OR add compound keywords to MAP_KEYWORDS: `homecontent-directions`, `homecontent-getdirections`
3. OR modify Lexus handler to include these patterns

### Root Cause 2: [Second Root Cause]

[Repeat format for additional root causes]

### Root Cause 3: [Third Root Cause]

[Repeat format for additional root causes]

## Why Successful Sites Succeed

1. **Pattern Compliance:** All successful sites use import paths that match MAP_KEYWORDS with word boundaries
2. **Standard Structure:** Follow `dealer-groups/lexus/lexusoem\d+/<keyword>` format
3. **No Exclusion Conflicts:** Selectors don't match header/nav/footer exclusion patterns
4. **Proper Shortcode Registration:** If using shortcodes, they match `[full-map]` pattern

## Why Failed Sites Fail

1. **Compound Keywords:** Use `homecontent-directions` instead of `directions` alone
2. **Non-Standard Patterns:** Don't match Lexus handler specific patterns
3. **Possible Exclusion:** [If applicable] Selectors match exclusion patterns
4. **Shortcode Issues:** [If applicable] Custom shortcodes not detected

## Edge Cases Identified

1. **Edge Case 1:** Sites with hyphenated OEM groups (e.g., `lexus-oem-3` vs `lexusoem3`)
2. **Edge Case 2:** Sites with nested partials not following standard structure
3. **Edge Case 3:** Sites with custom map implementations not using CommonTheme

## Recommendations for Epic 5

Based on root cause analysis, Epic 5 (Solution Strategy) should address:

1. **Keyword Detection:**
   - Expand MAP_KEYWORDS to include compound variations
   - OR modify regex pattern to handle compound keywords
   - OR add Lexus-specific compound patterns to handler

2. **Lexus Handler Enhancement:**
   - Add patterns for `homecontent-*` variations
   - Add patterns for non-standard OEM group formats
   - Add fallback detection for edge cases

3. **Classification Logic:**
   - [If applicable] Whitelist map selectors to prevent exclusion
   - [If applicable] Add context-aware classification for map components

4. **Testing:**
   - Create test cases for all failed site patterns
   - Ensure solution handles both successful and previously-failed patterns
   - Add regression tests for edge cases

## Conclusion

The primary root cause of Lexus map migration failures is **compound keyword detection failure** due to overly-strict word boundary requirements in the pattern matching logic. Secondary causes include [list other causes if identified].

The solution requires enhancing the detection patterns to handle compound keywords while maintaining backward compatibility with successful patterns.
```

### Testing Requirements

**Analysis Validation:**
- Must identify at least 1 primary root cause with concrete evidence
- Must explain why ALL 3 failed sites failed
- Must explain why successful sites succeed
- Must provide specific code references (file, function, line number)
- Must include pattern testing with actual failed patterns

**Evidence Requirements:**
- Actual import paths and selectors from PRs
- Pattern matching test results (match/no match)
- Code snippets showing problematic logic
- Comparison tables showing differences

### Previous Story Intelligence

**From Story 4.1:**
- MAP_KEYWORDS pattern: `r"(?i)\W(?:mapsection|section-map|map-row|...)\W"`
- Word boundary usage: `\\b(?:{keyword_list})` in line 275

**From Story 4.2:**
- Classification exclusion patterns documented
- SCSS processor pipeline understood

**From Story 4.3:**
- Failed sites: lexusofatlanticcity, tustinlexus, lexusofalbuquerque
- Concrete selectors and import paths extracted

**From Story 4.4:**
- Successful baseline established
- Common patterns identified

**Critical Question This Story Must Answer:**
"What EXACTLY causes these 3 sites to fail while others succeed?"

### Git Intelligence Summary

No code changes should be made in this story. This is pure analysis leading into Epic 5 implementation.

### Latest Tech Information

**Root Cause Analysis Best Practices:**
- Use "5 Whys" technique to drill down to fundamental cause
- Distinguish symptoms from causes
- Verify root cause explains ALL failures
- Ensure fix won't break successful cases

### Project Context Reference

From PRD:
- **FR4: Gap Analysis** - Explicitly state why current logic fails for problematic sites and why it succeeded for others
- **FR5: Root Cause Identification** - Define the exact conditions that cause migration failure, covering all edge cases
- **NFR2: Accuracy** - Findings must be evidence-based from actual PR data

From Epic 4 Goal:
- "Identify the exact root causes of migration failures"
- "Document gap analysis"

### Story Completion Status

**Status:** ready-for-dev

**Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created. This is the final analysis story in Epic 4 that brings together all evidence to definitively identify root causes. Output feeds directly into Epic 5 (Solution Strategy).

**Next Steps:**
1. Run `dev-story` workflow to execute this analysis story
2. Output will be definitive root cause documentation in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/`
3. Epic 4 is complete after this story
4. Epic 5 will use root cause findings to design bulletproof solution strategy

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
