---
title: 'Remove Success Rate displays, fix Slack PR link, and SCSS migration'
slug: 'remove-success-rate-fix-slack-pr-link-and-scss-migration'
created: '2026-01-22T16:48:42.000Z'
status: 'in-progress'
stepsCompleted: [1, 2]
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

- Remove “Success Rate” display from Slack Block Kit and CLI stats views.
- Update Slack “Open PRs” section to link to filtered Auto‑SBM open PRs query.
- Identify root cause of commented selector lines in SCSS migration; fix in SCSS processor/recovery path.
- Update tests covering Slack payload/metrics display changes.

### Acceptance Criteria

- CLI and Slack stats no longer display “Success Rate”.
- Slack PRs section links to a GitHub search that returns only open Auto‑SBM PRs (non‑draft, fe‑dev).
- SCSS migration no longer comments out valid selector lines (e.g., `.mapRow {}`) or leaves stray braces that break compilation.
- Tests updated/added to reflect new Slack payload structure.

## Additional Context

### Dependencies

- TBD in investigation

### Testing Strategy

- TBD in investigation

### Notes

- Slack PR link should use GitHub filters: `is:pr is:open -is:draft label:fe-dev PCON-727 SBM` (confirm exact query string with gh cli).
- SCSS migration error example: `.mapRow` block gets commented out, resulting in stray `}` and SCSS compile failure.
