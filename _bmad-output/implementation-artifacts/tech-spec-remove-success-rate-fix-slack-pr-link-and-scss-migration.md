---
title: 'Remove Success Rate displays, fix Slack PR link, and SCSS migration'
slug: 'remove-success-rate-fix-slack-pr-link-and-scss-migration'
created: '2026-01-22T16:48:42.000Z'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Python
  - Click
  - Rich
  - Slack Block Kit (JSON)
  - GitHub Search (PR query)
  - SCSS processing pipeline
files_to_modify:
  - scripts/stats/report_slack.py
  - tests/archive/test_slack_report.py
  - sbm/cli.py
  - sbm/core/migration.py
  - sbm/scss/processor.py
  - sbm/scss/classifiers.py
  - sbm/core/maps.py
code_patterns:
  - Slack payloads built as Block Kit sections/fields in `format_slack_payload`
  - CLI stats display uses Rich Panels/Columns in `sbm/cli.py`
  - SCSS processing via `SCSSProcessor.transform_scss_content` and `reprocess_scss_content`
  - Compilation error recovery modifies test-* SCSS in css/ during verification
test_patterns:
  - unittest-based tests in `tests/archive/test_slack_report.py`
---

# Tech-Spec: Remove Success Rate displays, fix Slack PR link, and SCSS migration

**Created:** 2026-01-22T16:48:42.000Z

## Overview

### Problem Statement

Front-end stats UIs show “Success Rate” (should be removed), Slack app links to an unfiltered PR list instead of Auto-SBM open PRs, and the SCSS migration process is corrupting a `.mapRow` block by commenting out the selector and leaving a stray brace, breaking compilation.

### Solution

Remove “Success Rate” from CLI and Slack display output (display-only), update Slack to link to an Auto-SBM open PRs filtered view, and fix the SCSS migration logic so `.mapRow` blocks are not commented out or duplicated; add tests/validation as appropriate.

### Scope

**In Scope:**
- CLI stats display
- Slack stats display and link
- SCSS migration pipeline that produces `sb-inside.scss`

**Out of Scope:**
- Changing metrics computation/storage
- Non-SBM dashboards
- Modifying source SCSS in the repo itself

## Context for Development

### Codebase Patterns

- Slack stats rendering is centralized in `scripts/stats/report_slack.py` (metrics calculation + Block Kit layout).
- CLI stats display is assembled in `sbm/cli.py` with Rich Panels/Columns for metrics.
- SCSS migrations are processed through `sbm/scss/processor.py` and error recovery in `sbm/core/migration.py`.
- Map SCSS migration uses `sbm/core/maps.py` with `SCSSProcessor.transform_scss_content`.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| scripts/stats/report_slack.py | Slack stats aggregation + Block Kit payload |
| tests/archive/test_slack_report.py | Tests for Slack report metrics/payload |
| sbm/cli.py | CLI stats display (Rich panels/tables) |
| sbm/core/migration.py | SCSS compilation error recovery + reprocess flow |
| sbm/scss/processor.py | SCSS transformation + cleanup logic |
| sbm/scss/classifiers.py | Rule parsing/exclusion logic |
| sbm/core/maps.py | Map SCSS migration, map import handling |

### Technical Decisions

- Remove “Success Rate” from display only; keep metric calculation unless needed for other logic/tests.
- Replace “Open PRs (In Review)” link list with a single GitHub search link filtered to open Auto‑SBM PRs.
- Align PR filter with existing SBM PR detection patterns (branch/title in `scripts/backfill_firebase_runs.py`), and confirm the encoded GitHub search URL via `gh` if available.
- Fix SCSS mis‑migration by preventing selector lines from being commented out without matching closing brace handling; update processor/recovery logic as needed.

## Implementation Plan

### Tasks

- [x] Task 1: Remove “Success Rate” from Slack stats display only
  - File: `scripts/stats/report_slack.py`
  - Action: Remove the “Success Rate” field from the Block Kit metrics grid and any summary text that references it.
  - Notes: Keep underlying calculation unless unused by other logic/tests.
- [x] Task 2: Remove “Success Rate” from CLI stats display
  - File: `sbm/cli.py`
  - Action: Locate any “Success Rate” label in stats panels/tables and remove it from rendered output.
  - Notes: If not present, confirm no-op and avoid changes.
- [x] Task 3: Update Slack “Open PRs” section to a filtered Auto‑SBM PRs link
  - File: `scripts/stats/report_slack.py`
  - Action: Replace the list of raw PR links with a single GitHub search link using query `is:pr is:open -is:draft label:fe-dev PCON-727 SBM`.
  - Notes: URL‑encode the query; confirm the final URL via `gh` (if available) and keep label text as “Open PRs (Auto‑SBM)”.
- [x] Task 4: Fix SCSS processor to restore fully commented selector lines
  - File: `sbm/scss/processor.py`
  - Action: Update `_fix_commented_selector_blocks` to strip *all* leading `//` markers (e.g., `// // // .mapRow {`) so selectors are restored before live declarations.
  - Notes: This prevents orphaned declarations and stray braces.
- [x] Task 5: Fix compilation recovery selector‑uncomment logic
  - File: `sbm/core/migration.py`
  - Action: Update `_fix_commented_selector_block` to remove multiple leading comment markers, not just the first.
  - Notes: Ensure it uncomments the selector line that contains `{` and preserves indentation.
- [x] Task 6: Update tests for Slack display changes and add SCSS regression test
  - File: `tests/archive/test_slack_report.py`
  - Action: Remove/adjust any assertions on `success_rate` display and update expectations for the “Open PRs” section.
  - Notes: Add a new unit test (new file if needed) for `_fix_commented_selector_blocks` to ensure `// // .mapRow {` is restored.

### Acceptance Criteria

- [ ] AC 1: Given stats are displayed in CLI or Slack, when the stats view renders, then “Success Rate” is not shown anywhere.
- [ ] AC 2: Given the Slack stats payload is rendered, when the “Open PRs” section appears, then it links to the GitHub search for open Auto‑SBM PRs using `is:pr is:open -is:draft label:fe-dev PCON-727 SBM`.
- [ ] AC 3: Given SCSS migration processes style.scss content, when a selector line is accidentally commented (e.g., `// // // .mapRow {`), then the selector is restored and the block compiles without orphaned braces.
- [ ] AC 4: Given test updates are run, when the Slack payload tests execute, then they pass with updated expectations and the new SCSS regression test passes.

## Additional Context

### Dependencies

- GitHub search URL encoding (can be derived manually; optionally verified via `gh`).

### Testing Strategy

- Unit: update `tests/archive/test_slack_report.py` for Slack payload expectations.
- Unit: add SCSS processor regression test for multiple leading `//` in selector lines.
- Manual: run `python scripts/stats/report_slack.py --period all --dry-run` and verify “Success Rate” removed and PR link points to filtered search.

### Notes

- Slack PR link should use GitHub filters: `is:pr is:open -is:draft label:fe-dev PCON-727 SBM` (confirm exact query string with gh cli).
- SCSS migration error example: `.mapRow` block gets commented out, resulting in stray `}` and SCSS compile failure.

## Review Notes
- Adversarial review completed
- Findings: 10 total, 7 fixed, 3 skipped
- Resolution approach: auto-fix
