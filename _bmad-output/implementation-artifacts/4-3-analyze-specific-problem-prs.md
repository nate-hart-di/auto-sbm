# Story 4.3: Analyze Specific Problem PRs

Status: ready-for-dev

## Story

As a Developer,
I want to extract and analyze the specific PRs for failed migrations (21434, 21462, 21393, 21391),
So that I can see exactly what patterns, file changes, and issues occurred in the problematic sites.

## Acceptance Criteria

**Given** the PR numbers for failed migrations
**When** I use `gh` CLI to fetch PR details, file diffs, and commit messages
**Then** I extract all SCSS changes for `lexusofatlanticcity`, `tustinlexus`, and `lexusofalbuquerque`
**And** I identify which styles ended up in wrong files
**And** I document the specific patterns present in these sites
**And** I note any error messages, manual fixes, or special handling applied

## Tasks / Subtasks

- [ ] Extract PR data using gh CLI (AC: Fetch PR details, file diffs, commit messages)
  - [ ] Fetch PR 21434 (lexusofatlanticcity) data: `gh pr view 21434 --json title,body,files,commits`
  - [ ] Fetch PR 21462 (tustinlexus) data: `gh pr view 21462 --json title,body,files,commits`
  - [ ] Fetch PR 21393 (lexusofalbuquerque) data: `gh pr view 21393 --json title,body,files,commits`
  - [ ] Fetch PR 21391 (related reference) data: `gh pr view 21391 --json title,body,files,commits`
- [ ] Analyze file changes in each PR (AC: Identify styles in wrong files)
  - [ ] Extract all SCSS file modifications (style.scss, sb-inside.scss, sb-home.scss)
  - [ ] Use `gh pr diff` to get actual style changes per file
  - [ ] Identify map-related styles in each file
  - [ ] Document which map styles were placed incorrectly (style.scss vs sb-inside.scss)
- [ ] Extract and analyze SCSS patterns (AC: Document specific patterns)
  - [ ] For each site, identify CommonTheme import paths for map components
  - [ ] Document selector patterns in map styles (classes, IDs, element types)
  - [ ] Check for keyword matches against MAP_KEYWORDS from Story 4.1
  - [ ] Check for classification pattern matches (header/nav/footer) from Story 4.2
- [ ] Document errors and manual fixes (AC: Note error messages, special handling)
  - [ ] Extract PR comments and review feedback
  - [ ] Identify any compilation errors or Sass errors mentioned
  - [ ] Document any manual adjustments made post-automation
  - [ ] Note any special handling or workarounds applied
- [ ] Create problem PR analysis report (AC: Complete extraction and documentation)
  - [ ] Create individual PR analysis for each site in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/pr-analysis/`
  - [ ] Create comparative summary showing common failure patterns
  - [ ] Document file placement errors with specific line numbers and selectors
  - [ ] Save evidence files (diffs, comments) for reference

## Dev Notes

### Current System Understanding

**Problem Context:**
From PRD and Epic description:
- **Target Sites:** `lexusofatlanticcity`, `tustinlexus`, `lexusofalbuquerque`
- **Target PRs:** 21434, 21462, 21393, 21391
- **Problem:** Map styles not migrating to `sb-inside.scss` (staying in `style.scss` or missing)
- **Impact:** Broken forms and dealer info boxes due to incorrect style placement
- **Reference Branch:** `pcon-727-lexusofatlanticcity-sbm0126`

**What We Know from Stories 4.1 & 4.2:**
- Map detection uses keyword-based pattern matching (MAP_KEYWORDS)
- Lexus handler has specific patterns: `dealer-groups/lexus/lexusoem\d+/_?section-map`
- SCSS processor applies classification/exclusion (header/nav/footer patterns)
- Map styles should go to `sb-inside.scss` and `sb-home.scss`, NOT `style.scss`

**What We Need to Find:**
1. Did the automation run at all for these sites?
2. Were map styles detected but misclassified?
3. Were map styles detected but placed in wrong file?
4. Were map styles not detected at all?
5. What specific selectors/patterns are present in the failed migrations?

### GitHub CLI Commands

**PR Data Extraction:**
```bash
# Basic PR info with files and commits
gh pr view 21434 --json title,body,state,files,commits,comments,reviews

# Full diff output
gh pr diff 21434 > pr-21434-diff.txt

# Individual file diffs
gh pr diff 21434 -- themes/lexusofatlanticcity/css/style.scss
gh pr diff 21434 -- themes/lexusofatlanticcity/sb-inside.scss

# PR timeline with comments
gh pr view 21434 --comments
```

**Repository Context:**
- Repo: `dealerinspire/di-websites-platform` (assumed from CLAUDE.md GITHUB_ORG=dealerinspire)
- Branch pattern: Likely `sbm-<sitename>` or similar
- File paths: `themes/<sitename>/css/style.scss`, `themes/<sitename>/sb-inside.scss`

### Architecture Compliance

**Analysis Methodology:**
1. Extract raw data from GitHub API via `gh` CLI
2. Parse SCSS diffs to identify map-related changes
3. Cross-reference with MAP_KEYWORDS and Lexus patterns
4. Identify classification matches/mismatches
5. Document evidence-based findings

**Technical Stack:**
- `gh` CLI - GitHub API access (must be authenticated)
- `jq` - JSON parsing (optional but recommended)
- Bash/Python - Script for automated extraction
- Regex - Pattern matching against known keywords

**Code Structure:**
- Analysis script: `scripts/analyze_prs.py` or `scripts/analyze_prs.sh`
- Output directory: `_bmad-output/planning-artifacts/lexus-map-migration-analysis/pr-analysis/`
- Individual PR reports: `pr-21434-lexusofatlanticcity.md`, etc.
- Comparative summary: `pr-analysis-summary.md`

### Library & Framework Requirements

**Dependencies:**
- `gh` CLI (GitHub CLI) - Must be installed and authenticated
- `git` - For checking out branches if needed
- Python `requests` (optional) - For direct API calls if `gh` CLI insufficient
- `jq` (optional) - For JSON parsing in bash scripts

**GitHub CLI Setup:**
```bash
# Check if gh CLI is installed
gh --version

# Authenticate (if not already)
gh auth login

# Set default repo (if needed)
gh repo set-default dealerinspire/di-websites-platform
```

### File Structure Requirements

**Analysis Output Structure:**
```
_bmad-output/planning-artifacts/lexus-map-migration-analysis/
├── current-logic-analysis/ (from Story 4.1)
├── scss-processing-analysis.md (from Story 4.2)
└── pr-analysis/
    ├── pr-21434-lexusofatlanticcity.md
    ├── pr-21462-tustinlexus.md
    ├── pr-21393-lexusofalbuquerque.md
    ├── pr-21391-reference.md
    ├── pr-analysis-summary.md
    └── evidence/
        ├── pr-21434-diff.txt
        ├── pr-21434-style.scss-diff.txt
        ├── pr-21434-sb-inside.scss-diff.txt
        └── ... (repeat for each PR)
```

**Individual PR Report Template:**
```markdown
# PR Analysis: PR #XXXXX - <sitename>

## PR Metadata
- **PR Number:** XXXXX
- **Site:** <sitename>
- **Branch:** <branch-name>
- **Status:** merged/closed
- **Related Issue:** PCON-XXX

## Files Changed
- style.scss: +XXX -YYY lines
- sb-inside.scss: +XXX -YYY lines
- sb-home.scss: +XXX -YYY lines
- Others: ...

## Map-Related SCSS Changes

### Expected Location: sb-inside.scss
(Map styles that SHOULD be here)

### Actual Location: style.scss
(Map styles that INCORRECTLY ended up here)

### Missing Styles
(Map styles that were not migrated at all)

## Pattern Analysis

### CommonTheme Import Paths
- List of @import statements from style.scss

### Selector Patterns
- Classes: .map-section, .directions, etc.
- IDs: #map-container, etc.
- Elements: div, section, etc.

### Keyword Matches
- MAP_KEYWORDS matches: [list]
- Lexus pattern matches: [list]
- Classification matches: [header/nav/footer patterns that matched]

## Error Messages & Manual Fixes
- Compilation errors: [if any]
- Manual adjustments: [documented from PR comments]
- Workarounds: [special handling]

## Root Cause Hypothesis
Based on pattern analysis, the likely failure reason is...
```

### Testing Requirements

**Analysis Validation:**
- Must successfully extract data from all 4 PRs
- Must identify at least 3 specific SCSS patterns per site
- Must document actual file placement vs expected placement
- Must provide evidence with line numbers and selector examples

**Evidence Requirements:**
- Full PR diffs saved as artifacts
- Specific SCSS selectors quoted from actual code
- PR comments and review feedback extracted
- Cross-reference with MAP_KEYWORDS and classification patterns

### Previous Story Intelligence

**From Story 4.1:**
- MAP_KEYWORDS list: `mapsection`, `section-map`, `map-row`, `maprow`, `map_rt`, `mapbox`, `mapboxdirections`, `full-map`, `get-directions`, `getdirections`
- Lexus patterns: `dealer-groups/lexus/lexusoem\d+/_?section-map`, etc.
- Map styles should append to `sb-inside.scss` and `sb-home.scss` with marker `/* === MAP COMPONENTS === */`

**From Story 4.2:**
- Classification patterns that could cause misplacement:
  - HEADER_PATTERNS: `r"header"`, `r"\.masthead"`, `r"\.banner"`
  - NAVIGATION_PATTERNS: `r"\.nav"`, `r"\.navbar"`, `r"menu-item"`, `r"\.menu-"`
  - FOOTER_PATTERNS: `r"footer"`, `r"\.main-footer"`, etc.
- Potential misclassification scenarios identified
- SCSS processor pipeline understood

**Questions to Answer:**
1. Do any of the failed sites have selectors matching classification exclusion patterns?
2. Were map imports detected by `find_commontheme_map_imports()` but not migrated?
3. Were map shortcodes detected by `find_map_shortcodes_in_functions()` but not migrated?
4. Are there patterns in the failed sites that are NOT covered by current MAP_KEYWORDS?

### Git Intelligence Summary

**Reference Branch:** `pcon-727-lexusofatlanticcity-sbm0126`
- This branch may contain manual fixes or investigation work
- Should check out this branch to see working solution or attempts
- Compare branch's approach vs automated approach

**Git Commands for Investigation:**
```bash
# Check out reference branch
git fetch origin pcon-727-lexusofatlanticcity-sbm0126
git checkout pcon-727-lexusofatlanticcity-sbm0126

# Compare files
diff themes/lexusofatlanticcity/sb-inside.scss themes/lexusofatlanticcity-automated/sb-inside.scss

# Check commit messages
git log --oneline --grep="lexus" --grep="map"
```

### Latest Tech Information

**GitHub CLI Best Practices:**
- Use `--json` flag for machine-readable output
- Use `jq` for parsing JSON responses
- Cache API responses to avoid rate limiting
- Use `--repo` flag if working across multiple repos

**PR Diff Analysis:**
- Unified diff format (+/-) shows additions and deletions
- Look for `/* === MAP COMPONENTS === */` marker
- Look for CommonTheme import statements
- Look for map-related class selectors and IDs

### Project Context Reference

From PRD:
- **NFR2: Accuracy** - Findings must be evidence-based from actual PR data
- **NFR3: Safety** - No code changes during this phase
- This is pure investigation and documentation

From CLAUDE.md:
- Repository: `dealerinspire/di-websites-platform` (inferred from GITHUB_ORG)
- Must authenticate with `GITHUB_TOKEN` environment variable

### Story Completion Status

**Status:** ready-for-dev

**Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created. This story extracts concrete evidence from actual failed migrations to enable root cause identification in Stories 4.4 and 4.5.

**Next Steps:**
1. Run `dev-story` workflow to execute this analysis story
2. Ensure `gh` CLI is authenticated and configured
3. Output will be PR analysis reports in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/pr-analysis/`
4. Story 4.4 will use this concrete evidence for comprehensive historical comparison
5. Story 4.5 will combine all findings for gap analysis and root cause identification

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
