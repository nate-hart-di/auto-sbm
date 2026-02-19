---
title: 'Auto-Heal Broken Map Shortcodes'
slug: 'auto-heal-broken-map-shortcodes'
created: '2026-02-19'
status: 'done'
stepsCompleted: [1, 2]
tech_stack: ['Python', 'auto-sbm']
files_to_modify: ['sbm/core/maps.py', 'tests/test_maps.py']
code_patterns: ['pathlib-manipulation', 'file-copying', 'dict-construction']
test_patterns: ['pytest-fixtures', 'unittest-mock', 'tmp_path']
---

# Tech-Spec: Auto-Heal Broken Map Shortcodes

**Created:** 2026-02-19
**Last Reviewed:** 2026-02-19 (Adversarial Review — follow-up fixes applied and verified)

## Overview

### Problem Statement

Dealerships (e.g., `sewelllexusoffortworth`) have a legacy `[full-map]` shortcode registered in their `functions.php`, which points to a template part `partials/map/full-map`. This file **does not exist** anywhere in the CommonTheme repository. When content editors use the shortcode on internal pages in Site Builder, it outputs nothing. During migration, auto-sbm correctly detects the missing file and skips it (`skipped_missing`), leaving the shortcode permanently broken in the new environment.

### Solution

Implement an "Auto-Healing" proxy approach inside `migrate_map_partials`. When auto-sbm processes shortcode partials and `copy_partial_to_dealer_theme` returns `"skipped_missing"`, the auto-heal logic intercepts the status. It searches the `extra_partials` list (containing valid template-discovered map partials like `section-map`) for a real `.php` file that exists in CommonTheme. If one is found, auto-sbm constructs a new `partial_info` dict pointing from the template partial's source to the shortcode partial's expected destination, then re-invokes `copy_partial_to_dealer_theme` to perform the copy with full infrastructure (directory creation, logging, deduplication). This provides a physical proxy file to the shortcode without bypassing established copy machinery or modifying `functions.php`.

### Scope

**In Scope:**

- Modify `migrate_map_partials` in `sbm/core/maps.py` to intercept `skipped_missing` status on shortcode-sourced partials.
- Cross-reference missing shortcode partials with successfully detected template map partials from `extra_partials`.
- Resolve the actual CommonTheme source file for the template partial.
- Re-invoke `copy_partial_to_dealer_theme` with a synthesized `partial_info` dict to copy the template partial to the destination the shortcode expects.
- Log the auto-healing process clearly for the user.

**Out of Scope:**

- Modifying the AST of `functions.php` to rewrite the shortcode registration path itself.
- Auto-healing templates other than maps.
- Fixing the `partials/` prefix stripping issue (Bug 1) — treated as a separate prerequisite. See [Notes](#notes).

## Context for Development

### Codebase Patterns

**Python (sbm/core/maps.py):**

- **Orchestrator:** `migrate_map_components` (L158) handles the high-level workflow. It calls `find_map_shortcodes_in_functions`, `find_map_partials_in_templates`, and `migrate_map_partials`.
- **Detector:** `find_map_shortcodes_in_functions` (L455) parses `functions.php` to find shortcode registrations and their backing partial paths.
- **Detector:** `find_map_partials_in_templates` (L327) scans `front-page.php`, `index.php`, `page.php`, `home.php`, `functions.php`, and the entire `partials/` directory for `get_template_part` calls.
- **Migrator:** `migrate_map_partials` (L897) iterates over discovered partial paths and calls `copy_partial_to_dealer_theme` for each.
- **Copier:** `copy_partial_to_dealer_theme` (L1151) handles CommonTheme → DealerTheme copy with directory creation, fuzzy matching, and returns status strings: `"copied"`, `"already_exists"`, `"skipped_missing"`, `"skipped_inheritance"`, or `False` (on exception).

**Key data structure — `partial_info` dict:**

```python
{
    "template_file": "front-page.php",          # Source file where partial was detected
    "partial_path": "map/section-map",           # CommonTheme-relative path (no extension)
    "source": "found_in_template",               # Detection method
    "shortcode": "full-map",                     # Only present for shortcode-sourced partials
    "handler": "fullmap_shortcode_handler",       # Only present for shortcode-sourced partials
}
```

### Files to Reference

| File                 | Purpose                   | Changes Needed                                                                                                                                                       |
| -------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sbm/core/maps.py`   | Core map migration logic  | MODIFY: `migrate_map_partials` (L959-976) to add auto-heal fallback when `copy_partial_to_dealer_theme` returns `"skipped_missing"` for a shortcode-sourced partial. |
| `tests/test_maps.py` | Unit tests for maps logic | ADD: Test cases for auto-heal success and auto-heal skip (no valid template partial).                                                                                |

### Technical Decisions

**Architecture:**

- **Proxy File via `copy_partial_to_dealer_theme` (not raw `shutil.copy2`):** We re-use the existing copy infrastructure to maintain consistency — directory creation, logging, fuzzy matching, and status tracking all remain intact. Direct `shutil.copy2()` would bypass these safeguards.
- **Fallback Resolution:** The auto-heal loop iterates `extra_partials` (the template-discovered map partials) to find a dict whose `partial_path` resolves to an existing `.php` file in CommonTheme. It then constructs a synthetic `partial_info` where `partial_path` is set to the **shortcode's expected destination** and the CommonTheme source is the **template partial's resolved file**.
- **Graceful degradation:** If no valid template partial can be found, the original `skipped_missing` result is preserved and logged — no crash, no false positives.

### Prerequisite: Bug 1 — `partials/` Prefix Stripping

> [!IMPORTANT]
> This spec depends on the `partials/` prefix stripping fix (Bug 1) being applied first. Without it, `template_partials` entries from `find_template_parts_in_file` may retain a `partials/` prefix that prevents CommonTheme lookup from succeeding.
>
> Specifically: `find_template_parts_in_file` (L1020) strips `partials/` via regex `(?:/)?(?:partials/)?`, but `copy_partial_to_dealer_theme` (L1168) only does `lstrip("/")` without stripping `partials/`. Verify Bug 1 is resolved before implementing this spec.

## Implementation Plan

### Tasks

#### Phase 1: Implement Auto-Healing Logic

- [x] Task 1: Update `sbm/core/maps.py` → `migrate_map_partials` (L959-976)

  **Location:** Inside the `for partial_info in partial_paths:` loop, after the `copy_partial_to_dealer_theme` call (L965) and BEFORE the status branch at L966.

  **Logic:**

  ```python
  status = copy_partial_to_dealer_theme(slug, partial_info, interactive=interactive)

  # --- AUTO-HEAL: Intercept skipped_missing for shortcode-sourced partials ---
  if status == "skipped_missing" and partial_info.get("source") == "found_in_shortcode_handler":
      healed = False
      shortcode_dest = partial_info.get("partial_path", "")

      # Search extra_partials for a valid template partial to use as proxy source
      if extra_partials:
          for candidate in extra_partials:
              candidate_path = candidate.get("partial_path", "")
              if not candidate_path or candidate_path.startswith("shortcode:"):
                  continue  # Skip shortcode-derived entries

              # Resolve the candidate's CommonTheme source file
              candidate_source = Path(COMMON_THEME_DIR) / f"{candidate_path.lstrip('/')}.php"
              if not candidate_source.exists():
                  # Try with partials/ prefix
                  candidate_source = Path(COMMON_THEME_DIR) / f"partials/{candidate_path.lstrip('/')}.php"

              if candidate_source.exists():
                  # Directly copy the resolved template partial to the shortcode's expected destination.
                  # We use shutil.copy2() here because copy_partial_to_dealer_theme resolves source
                  # from CommonTheme using partial_path — but in auto-heal, source and destination
                  # are completely different paths that can't be expressed through a single partial_info dict.
                  theme_dir = Path(get_dealer_theme_dir(slug))
                  dest_file = theme_dir / f"{shortcode_dest.lstrip('/')}.php"
                  dest_file.parent.mkdir(parents=True, exist_ok=True)

                  if not dest_file.exists():
                      shutil.copy2(candidate_source, dest_file)
                      logger.info(
                          f"🩹 Auto-healed broken shortcode partial: {shortcode_dest}.php "
                          f"← {candidate_source.name}"
                      )
                      status = "copied"
                      actually_copied.append(shortcode_dest)
                      healed = True
                      break
                  else:
                      logger.info(f"Auto-heal target already exists: {dest_file}")
                      status = "already_exists"
                      healed = True
                      break

      if not healed:
          logger.info(
              f"⚠️ Auto-heal skipped for {shortcode_dest}: "
              f"no valid template partial found in extra_partials"
          )
  # --- END AUTO-HEAL ---
  ```

#### Phase 2: Testing & Verification

- [x] Task 2: Add Unit Tests in `tests/test_maps.py`

  **Test 1: `test_auto_heal_copies_template_partial_for_broken_shortcode`**
  - Setup: Create a `tmp_path` structure with:
    - A shortcode `partial_info` with `source: "found_in_shortcode_handler"` and `partial_path: "map/full-map"`
    - An `extra_partials` list containing a template partial with `partial_path: "map/section-map"`
  - Mock `COMMON_THEME_DIR` to a temp directory containing `map/section-map.php`
  - Mock `get_dealer_theme_dir` to return a temp dealer theme path
  - Call `migrate_map_partials` with the above inputs
  - Assert: `dealer_theme/map/full-map.php` exists and contains the content from `section-map.php`
  - Assert: return value includes `"map/full-map"` in the copied list

  **Test 2: `test_auto_heal_skips_when_no_template_partial_available`**
  - Setup: Same as Test 1 but `extra_partials` is empty or all entries are `shortcode:*` prefixed
  - Assert: No files are created; function returns successfully with empty copied list
  - Assert: logger output contains the skip warning

  **Test 3: `test_auto_heal_skips_for_non_shortcode_partials`**
  - Setup: A partial with `source: "found_in_template"` that returns `skipped_missing`
  - Assert: Auto-heal logic is NOT triggered (only shortcode-sourced partials are healed)

### Acceptance Criteria

**Validation:**

- [x] AC1: Given a dealer with a `full-map` shortcode pointing to non-existent `partials/map/full-map`, AND a valid template partial `map/section-map.php` exists in CommonTheme, when auto-sbm runs map migration, then `section-map.php` is copied into the dealer theme at `map/full-map.php`.
- [x] AC2: Given a dealer where no valid map template partials are found across ANY template source (`front-page.php`, `index.php`, `page.php`, `home.php`, `functions.php`, `partials/` directory), when the shortcode partial is missing, then auto-healing is skipped and the original `skipped_missing` status is preserved with a warning log.
- [x] AC3: Given a dealer where the shortcode partial already exists in the dealer theme, auto-heal is NOT triggered (existing `already_exists` check in `copy_partial_to_dealer_theme` handles this).

## Additional Context

### Migration Decision Paths (If/Then)

This section documents the logical migration conditions implemented in `sbm/core/maps.py` so future agents can reason about every migrate vs do-not-migrate branch.

#### 1) Top-Level Orchestration (`migrate_map_components`)

- If `css/style.scss` does not exist, then map migration is skipped and returns success (`True`).
- If `style.scss` exists, then the system discovers:
  - explicit CommonTheme map imports,
  - shortcode-derived partials,
  - template-derived partials,
  - SCSS imports derived from discovered partials.
- If no imports and no partials are discovered, then migration is skipped (`skipped_reason: none_found`) and returns success.
- If at least one signal exists, then:
  - imports are filtered through `should_migrate_map_import`,
  - SCSS migration runs on filtered imports,
  - partial migration runs on discovered partials.
- If SCSS and partial migration both report success, then overall result is success.
- If one path reports issues, the workflow still returns success (soft-fail behavior with warnings).
- If an unhandled exception occurs in orchestration, then it returns failure (`False`).

#### 2) Import-Level Decision (`should_migrate_map_import`)

- If import resolves to an existing file inside the dealer theme, then **do not migrate** that import.
- Else if import resolves to an existing file in CommonTheme (including underscore/extension variants), then **migrate** that import.
- Else import is unresolved/missing, so **do not migrate** it.

#### 3) SCSS Content Migration (`migrate_map_scss_content`)

- If no valid imports are provided, then no SCSS is migrated.
- Imports are deduplicated by CommonTheme absolute path.
- If an import basename is already imported in local SCSS files, then that import is skipped.
- If all imports are already present, then no SCSS write occurs.
- If SCSS content cannot be read from any source import, then no SCSS write occurs.
- If content exists:
  - append to `sb-inside.scss` only when file exists and map marker is absent,
  - append to `sb-home.scss` only when file exists and map marker is absent.
- If marker already exists in a target file, no additional map block is appended there.

#### 4) Partial Migration (`migrate_map_partials` + `copy_partial_to_dealer_theme`)

- If no imports, no extra partials, and template scanning is disabled, then partial migration is a no-op success.
- For each unique partial path:
  - attempt normal copy via `copy_partial_to_dealer_theme`.
  - If destination already exists, status is `already_exists` (counted as successful handling).
  - If source exists in CommonTheme (exact or fuzzy), status is `copied`.
  - If source is missing, status is usually `skipped_missing` (non-blocking).
- Auto-heal branch:
  - triggers only when status is `skipped_missing` and source is `found_in_shortcode_handler`.
  - searches `extra_partials` for a valid template proxy source (excludes shortcode paths and shortcode-handler sources).
  - if proxy exists and destination missing, copies proxy to shortcode destination and upgrades status to `copied`.
  - if proxy exists but destination already exists, status becomes `already_exists`.
  - if no proxy exists (or filesystem error occurs), auto-heal is skipped and status remains non-blocking.
- Overall partial migration returns success when at least one path is successfully handled or when there are no partials to process.

### Notes

- This spec depends on Bug 1 (the `partials/` prefix stripping fix) being applied first. See [Prerequisite section](#prerequisite-bug-1--partials-prefix-stripping).
- Historical note: the duplicate `scss_relative` assignment block in `derive_map_imports_from_partials` was removed during follow-up review fixes.

---

## Dev Agent Record

### File List

- sbm/core/maps.py
- tests/test_maps.py
- _bmad-output/implementation-artifacts/tech-spec-wip-map-migration-fixes.md

### Tests

- `pytest tests/test_maps.py -k "auto_heal"`

### Change Log

| Date       | Action                       | Details                                                                                                                     |
| ---------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 2026-02-19 | Created                      | Initial tech-spec draft                                                                                                     |
| 2026-02-19 | Adversarial Review           | 10 issues found (2C, 3H, 3M, 2L). All CRITICAL, HIGH, and MEDIUM issues fixed in-spec. 2 LOW items deferred with rationale. |
| 2026-02-19 | Implemented                  | Both tasks completed. Auto-heal logic added to `migrate_map_partials`. 3 unit tests added and passing. All ACs verified.    |
| 2026-02-19 | Code Review (Implementation) | Post-implementation adversarial review. 5 issues found (1H, 2M, 2L). All HIGH and MEDIUM issues fixed. 1 LOW deferred.      |
| 2026-02-19 | Code Review (Implementation) | Follow-up adversarial review. 4 issues found (1H, 2M, 1L). All issues fixed and regression-tested (`pytest tests/test_maps.py`). |

### Review Findings Applied

**CRITICAL fixes:**

- C1: Fixed `copy_partial_to_dealer_theme` signature from `(slug, commontheme_partial_path)` to `(slug, partial_info, interactive=False)`. Documented `partial_info` dict structure.
- C2: Replaced naive `shutil.copy2()` proposal with re-invocation of `copy_partial_to_dealer_theme`. Then identified that re-invocation won't work for cross-path proxying, so documented the correct direct-copy approach with inline `mkdir` and logging.

**HIGH fixes:**

- H1: Fixed `template_partials` → `extra_partials` naming. Documented dict key structure.
- H2: Explicitly scoped Bug 1 as a prerequisite with an IMPORTANT callout, including line references.
- H3: Rewrote AC2 to reference all template sources, not just `front-page.php`.

**MEDIUM fixes:**

- M1: Added graceful degradation when no valid template partial is found (warning log, preserve `skipped_missing`).
- M2: Rewrote test strategy with `tmp_path` fixtures, proper mocking targets, and 3 distinct test cases.
- M3: Updated files table with correct line references and change descriptions.

**LOW deferred:**

- L1: Duplicate code in `derive_map_imports_from_partials` (L705-711) — pre-existing, out of scope. Document for future cleanup.
- L2: Stale "Context for Development" section — now fully rewritten with correct function names, line numbers, and data structures.

**Post-Implementation Adversarial Code Review:**

**HIGH fixes:**

- H1 (Code): Unhandled filesystem exceptions (`OSError`) in auto-heal could crash the entire migration loop. Added `try/except` block to ensure graceful degradation.

**MEDIUM fixes:**

- M1 (Tests): Missing validation for filesystem error paths. Added `test_auto_heal_handles_filesystem_error_gracefully` test case.
- M2 (Code): Fragile state mutation logic for `actually_copied` list by appending in two places. Removed duplicate append and relied on natural loop fall-through.

**LOW fixes/deferrals:**

- L3 (Fixed): O(N\*M) redundant disk I/O when evaluating candidates across multiple shortcodes. Cached valid template proxy outside the auto-heal loop to fast-path resolution.
- L4 (Deferred): Auto-heal logging output uses full destination path instead of `basename`, which is mildly inconsistent with other logs. Deferred as cosmetic.

**Follow-up Adversarial Review (2026-02-19):**

**HIGH fixes:**

- H2 (Code): `find_template_parts_in_file` extracted the shortcode function body instead of the `get_template_part` path due to incorrect regex capture grouping. Fixed pattern grouping to correctly capture only the partial path.

**MEDIUM fixes:**

- M3 (Code): Auto-heal candidate selection could choose shortcode-handler-discovered entries as proxy sources. Restricted proxy-source candidates to avoid `found_in_shortcode_handler` entries.
- M4 (Tests): AC2 required warning-log verification when auto-heal is skipped, but test coverage did not assert this. Added `caplog` assertion in `test_auto_heal_skips_when_no_template_partial_available`.

**LOW fixes/deferrals:**

- L5 (Code): Removed duplicated `scss_relative` normalization block in `derive_map_imports_from_partials`.
- L6 (Tests): Strengthened `test_auto_heal_skips_for_non_shortcode_partials` with explicit return-value assertions.
- L7 (Tests): Added `test_find_template_parts_in_file_extracts_shortcode_function_partial_path` to guard regex capture correctness going forward.

### Status Changes

- `status: implemented` → `status: done`
- `stepsCompleted: [1, 2]` (Implementation complete and verified by adversarial review)
