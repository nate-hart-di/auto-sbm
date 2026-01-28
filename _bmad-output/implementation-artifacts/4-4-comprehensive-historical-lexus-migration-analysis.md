# Story 4.4: Comprehensive Historical Lexus Migration Analysis

Status: ready-for-dev

## Story

As a Developer,
I want to analyze every single successful Lexus migration in the project history,
So that I can identify patterns that worked and create a baseline for comparison.

## Acceptance Criteria

**Given** access to GitHub PR history via `gh` CLI or Firebase migration data
**When** I query for all Lexus-related migration PRs with status "merged" or "success"
**Then** I create a comprehensive dataset with: site slug, PR number, files changed, SCSS patterns, outcome
**And** I identify common patterns in successful migrations
**And** I document any variations in successful approaches
**And** I categorize Lexus sites by migration success patterns

## Tasks / Subtasks

- [ ] Extract all Lexus migration history (AC: Query for all Lexus PRs)
  - [ ] Query GitHub for all PRs with "lexus" in title or branch name
  - [ ] Query Firebase migration data for all Lexus site runs
  - [ ] Filter for "merged" or "success" status only
  - [ ] Create complete list of successful Lexus migrations with metadata
- [ ] Analyze successful migration patterns (AC: Create comprehensive dataset)
  - [ ] For each successful site, extract SCSS file changes
  - [ ] Document which files contain map styles (sb-inside.scss vs style.scss)
  - [ ] Document CommonTheme import paths used
  - [ ] Document selector patterns and keywords present
- [ ] Identify common success patterns (AC: Identify common patterns)
  - [ ] Group sites by similar SCSS patterns
  - [ ] Identify consistent OEM groups (lexusoem1, lexusoem2, lexusoem3, etc.)
  - [ ] Document which MAP_KEYWORDS appear most frequently
  - [ ] Identify any manual interventions or special handling
- [ ] Document variations in approaches (AC: Document variations)
  - [ ] Identify sites with unusual patterns that still succeeded
  - [ ] Document edge cases that worked despite not matching typical patterns
  - [ ] Identify any sites that required manual fixes post-automation
- [ ] Create success categorization (AC: Categorize by success patterns)
  - [ ] Category A: "Standard lexusoem pattern" sites
  - [ ] Category B: "Custom shortcode" sites
  - [ ] Category C: "Manual intervention" sites
  - [ ] Category D: "Edge case" sites
- [ ] Create comprehensive historical analysis report
  - [ ] Save report in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/historical-analysis.md`
  - [ ] Include data tables with all successful sites
  - [ ] Include pattern frequency analysis
  - [ ] Include success categorization breakdown

## Dev Notes

### Current System Understanding

**Historical Data Sources:**

**1. GitHub PR History**
- Query via `gh` CLI: `gh pr list --search "lexus in:title" --state merged --limit 1000`
- Filter for Site Builder migration PRs (likely contain "sbm" or "migration" in title/branch)
- Extract PR numbers, merge dates, and file changes

**2. Firebase Migration Data**
- From Story 2.2 context: Firebase contains team-wide migration history
- Query Firebase for runs where slug contains "lexus"
- Filter for `status: "success"` or `outcome: "merged"`
- Extract: slug, timestamp, duration, lines_migrated, pr_number

**3. Local Migration History**
- Check `~/.sbm_migrations.json` for local Lexus migration history
- May contain additional metadata not in GitHub

**Expected Dataset Schema:**
```
{
  "site_slug": "lexusofbradenton",
  "pr_number": 21234,
  "merge_date": "2024-XX-XX",
  "outcome": "success",
  "files_changed": ["style.scss", "sb-inside.scss", "sb-home.scss"],
  "map_styles_location": "sb-inside.scss",
  "commontheme_imports": ["dealer-groups/lexus/lexusoem2/section-map"],
  "oem_group": "lexusoem2",
  "keywords_matched": ["section-map", "mapsection"],
  "manual_fixes": false,
  "category": "standard_lexusoem_pattern"
}
```

**Analysis Goals:**
1. Identify the "happy path" - What patterns consistently succeed?
2. Identify outliers - What unusual patterns still succeed?
3. Identify commonalities - Do all successful sites share certain characteristics?
4. Establish baseline - What should "normal" look like?

### Architecture Compliance

**Data Collection Strategy:**
```
Step 1: GitHub PR Query
  ↓
Step 2: Firebase Query (if available)
  ↓
Step 3: Merge datasets (deduplicate by slug)
  ↓
Step 4: For each site:
  - Extract PR diff
  - Parse SCSS changes
  - Identify patterns
  ↓
Step 5: Aggregate and categorize
  ↓
Step 6: Generate analysis report
```

**Technical Stack:**
- `gh` CLI for GitHub API access
- Python script for data aggregation and analysis
- Firebase Admin SDK (if querying Firebase directly)
- Regex for pattern matching
- Pandas/CSV for data manipulation (optional)

**Code Structure:**
- Analysis script: `scripts/analyze_lexus_history.py`
- Data cache: `_bmad-output/planning-artifacts/lexus-map-migration-analysis/data/`
- Report output: `_bmad-output/planning-artifacts/lexus-map-migration-analysis/historical-analysis.md`

### Library & Framework Requirements

**Dependencies:**
- `gh` CLI (GitHub API access)
- `firebase-admin` (if querying Firebase)
- Python `json` (for parsing data)
- Python `re` (for pattern matching)
- Python `collections.Counter` (for frequency analysis)
- Optional: `pandas` for data analysis

**GitHub CLI Queries:**
```bash
# Find all Lexus-related merged PRs
gh pr list --search "lexus in:title" --state merged --json number,title,mergedAt,files --limit 1000

# Find PRs by author (sbm bot or automation)
gh pr list --author "sbm-bot" --search "lexus" --state merged

# Find all SBM migration PRs
gh pr list --search "sbm in:title OR migration in:title" --state merged --label "lexus"
```

**Firebase Query (Pseudocode):**
```python
import firebase_admin
from firebase_admin import db

# Query all runs
ref = db.reference('/users')
all_runs = ref.get()

# Filter for Lexus sites
lexus_runs = [
    run for user_runs in all_runs.values()
    for run in user_runs.get('runs', {}).values()
    if 'lexus' in run.get('slug', '').lower()
    and run.get('status') == 'success'
]
```

### File Structure Requirements

**Output Structure:**
```
_bmad-output/planning-artifacts/lexus-map-migration-analysis/
├── data/
│   ├── github-prs.json (cached GitHub PR data)
│   ├── firebase-runs.json (cached Firebase migration data)
│   ├── merged-dataset.json (deduplicated combined data)
│   └── pr-diffs/ (cached PR diffs for each site)
└── historical-analysis.md (final report)
```

**Historical Analysis Report Template:**
```markdown
# Comprehensive Historical Lexus Migration Analysis

## Executive Summary
- Total Lexus migrations analyzed: XXX
- Success rate: XX%
- Date range: YYYY-MM-DD to YYYY-MM-DD

## Dataset Overview
| Site Slug | PR # | Merge Date | OEM Group | Map Location | Category |
|-----------|------|------------|-----------|--------------|----------|
| ... | ... | ... | ... | ... | ... |

## Success Pattern Analysis

### Pattern 1: Standard lexusoem Pattern (XX sites)
**Characteristics:**
- CommonTheme import: `dealer-groups/lexus/lexusoem\d+/section-map`
- Map styles placed in: `sb-inside.scss`
- Keywords matched: `section-map`, `mapsection`
- Manual fixes: None

**Example Sites:** lexusofbradenton, lexusofcerritos, ...

### Pattern 2: Custom Shortcode Pattern (XX sites)
**Characteristics:**
- Shortcode: `[full-map]` or `[get-directions]`
- Partial path: `partials/directions` or similar
- Map styles placed in: `sb-inside.scss` and `sb-home.scss`
- Keywords matched: `getdirections`, `full-map`

**Example Sites:** ...

### Pattern 3: Manual Intervention Pattern (XX sites)
**Characteristics:**
- Initial automation incomplete
- Post-merge manual adjustments documented in PR comments
- Final outcome successful

**Example Sites:** ...

## OEM Group Distribution
- lexusoem1: XX sites
- lexusoem2: XX sites
- lexusoem3: XX sites
- lexusoem4: XX sites
- Custom/Other: XX sites

## Keyword Frequency Analysis
| Keyword | Occurrences | % of Sites |
|---------|-------------|------------|
| section-map | XX | XX% |
| mapsection | XX | XX% |
| full-map | XX | XX% |
| ... | ... | ... |

## File Placement Analysis
- Map styles in sb-inside.scss: XX sites (XX%)
- Map styles in sb-home.scss: XX sites (XX%)
- Map styles in both: XX sites (XX%)
- Map styles in style.scss (incorrect): XX sites (XX%)

## Outliers and Edge Cases
1. Site: X - Unusual pattern but successful because...
2. Site: Y - Required manual fix for...
3. Site: Z - Edge case where...

## Success Factors
1. Factor 1: ...
2. Factor 2: ...
3. Factor 3: ...

## Baseline Definition
A "standard successful Lexus migration" exhibits:
- [ ] CommonTheme import matching Lexus pattern
- [ ] Map styles placed in sb-inside.scss
- [ ] Keywords matched: [list]
- [ ] No manual intervention required
```

### Testing Requirements

**Analysis Validation:**
- Must analyze at least 50+ successful Lexus migrations (if available)
- Must identify at least 2 distinct success patterns
- Must provide statistical breakdown (percentages, frequencies)
- Must include evidence (PR numbers, file paths, selectors)

**Data Quality Checks:**
- Verify PR numbers are valid and exist
- Verify merged status via GitHub API
- Cross-reference Firebase data with GitHub data for accuracy
- Identify any data inconsistencies or missing information

### Previous Story Intelligence

**From Story 4.1:**
- MAP_KEYWORDS and Lexus patterns documented
- Map migration logic flow understood

**From Story 4.2:**
- SCSS processor pipeline documented
- Classification rules understood

**From Story 4.3:**
- Failed sites analyzed (lexusofatlanticcity, tustinlexus, lexusofalbuquerque)
- Specific failure patterns documented

**Questions to Answer in This Story:**
1. What do successful sites have that failed sites lack?
2. Are there successful sites with patterns similar to failed sites?
3. What is the "typical" Lexus migration pattern?
4. Are there multiple valid success patterns?

### Git Intelligence Summary

**Historical Context:**
- SBM tool has been running for multiple months (evidenced by 164 migrations in Epic 2)
- Lexus migrations are a subset of total migrations
- Need to identify when map migration logic was added/changed
- Check git log for `sbm/core/maps.py` and `sbm/oem/lexus.py` changes

**Git Commands for Context:**
```bash
# Find when map migration was introduced
git log --all --oneline --grep="map"

# Find commits affecting Lexus handler
git log --oneline -- sbm/oem/lexus.py

# Find all Lexus-related commits
git log --all --oneline --grep="lexus" -i
```

### Latest Tech Information

**Data Analysis Best Practices:**
- Use statistically significant sample size
- Look for correlation vs causation
- Identify confounding variables (timing, tool version, manual intervention)
- Document data limitations and caveats

**Pattern Recognition Techniques:**
- Frequency analysis for keywords and selectors
- Clustering similar sites by feature vectors
- Outlier detection for unusual but successful patterns
- Baseline establishment via median/mode analysis

### Project Context Reference

From PRD:
- **FR3: Comprehensive Comparison** - Analyze **every single successful Lexus migration**
- **NFR1: Thoroughness** - Analyze ALL successful Lexus migrations, not just a sample
- **NFR2: Accuracy** - Findings must be evidence-based from actual PR data

From Epic 4 Goal:
- "Identify the patterns that worked"
- "Create a baseline for comparison"

### Story Completion Status

**Status:** ready-for-dev

**Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created. This story establishes the baseline of "what works" to enable gap analysis in Story 4.5.

**Next Steps:**
1. Run `dev-story` workflow to execute this analysis story
2. Ensure `gh` CLI and Firebase access are configured
3. Output will be comprehensive historical analysis in `_bmad-output/planning-artifacts/lexus-map-migration-analysis/`
4. Story 4.5 will compare successful patterns (from this story) with failed patterns (from Story 4.3) to identify root causes

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
