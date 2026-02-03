<template-output>
  <path>_bmad-output/implementation-artifacts/3-2-code-review-report.md</path>
  <content>
# Senior Developer Review (AI)

**Reviewer:** Gemini-2.0-Flash-Thinking-Exp-0121
**Date:** 2026-01-28
**Story:** 3-2-fix-map-migration-path-resolution
**Outcome:** Changes Requested

## 🚨 Critical Findings

### 1. Path Traversal in Local Existence Check
The function `should_migrate_map_import` contains a logic flaw that allows path traversal to escape the dealer theme directory.
```python
# sbm/core/maps.py
local_candidates = _resolve_scss_candidates(css_base, import_path)
if any(p.exists() for p in local_candidates):
    return False # Skipped!
```
If `import_path` is `../../DealerInspireCommonTheme/...` and this path resolves to a real file on the filesystem (e.g., in a development environment where themes are siblings), the function incorrectly identifies the file as "Local" and SKIPS the migration.
**Impact:** Migration fails to copy assets for valid WordPress paths, defeating the purpose of the migration tool which is to make the theme standalone.
**Fix:** Ensure `local_candidates` are strictly within `dealer_theme_dir` using `path.resolve().is_relative_to()`.

### 2. "Skipped Inheritance" Logic Disables Partial Migration
The function `copy_partial_to_dealer_theme` includes logic that strictly prevents copying any file found in CommonTheme:
```python
# sbm/core/maps.py
if commontheme_source.exists():
    return "skipped_inheritance"
```
This contradicts the requirement to "Migrate the SCSS content" and implied requirement to migrate components. By skipping all existing files, the "migration" becomes a no-op for PHP files, leaving the dealer theme dependent on CommonTheme.
**Impact:** Partial migration effectively disabled.
**Fix:** Remove the "skipped_inheritance" return or make it conditional. If we are migrating, we should copy.

## 🟡 Medium Findings

### 3. Brittle Regex for Template Parts
The regex used to find `get_template_part` inside functions is fragile:
```python
shortcode_function_pattern = r"function\s+...\{[^}]*get_template_part..."
```
The `[^}]*` pattern stops matching at the *first* closing brace `}`. If the function contains any nested blocks (if/foreach/while), the regex will fail to find `get_template_part` calls appearing after the nested block.
**Fix:** Simplify to scan for `get_template_part` calls globally in the file (context-free), or use a parser-based approach if precision is needed (though regex is standard here, `.*?` with `re.DOTALL` is safer than `[^}]*`).

### 4. Logic Discrepancy in `migrate_map_components`
The unified migration flow filters imports using `should_migrate_map_import`, but partials are migrated using `all_partials` (which includes raw findings) without a similar "should migrate" check (though `copy_partial` does its own check). Consistency would be better.

## 🟢 Low Findings

### 5. `_resolve_scss_candidates` Edge Case
The helper appends `_{filename}` even if `filename` already starts with `_` (e.g. `_foo` -> `__foo`). This is minor but messy.
**Fix:** Check `not filename.startswith("_")` before prepending.

## Action Plan
1.  **Fix `should_migrate_map_import`**: Add strict containment check.
2.  **Fix `copy_partial_to_dealer_theme`**: Remove inheritance skipping.
3.  **Fix Regex**: Replace brittle function-body regex with robust global search.
4.  **Refactor**: Cleanup `_resolve_scss_candidates`.
5.  **Verify**: Run the adversarial test again.

</content>
</template-output>
