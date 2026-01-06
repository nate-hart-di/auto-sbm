# Story 1.1: Fix SCSS Comment Cleanup Bug

Status: completed

## Story

As a Developer,
I want the SCSS processor to correctly handle complex comment patterns,
so that valid code is not accidentally removed or corrupted during migration.

## Acceptance Criteria

1.  **Safe Comment Removal**: The regex or logic for removing comments MUST NOT unintentionally remove valid code that follows comment-like patterns (e.g., `//` followed by `/*`).
2.  **Handle Nested/Double Comments**: Patterns like `// // .class { ... }` must be handled safely.
    -   If these are intended to be commented out, they should remain commented out or be removed cleanly.
    -   They must NOT result in partial uncommenting that leaves orphaned code (e.g., `fill: var(--primary) !important;` becoming active outside a selector).
3.  **Preserve Structure**: The file structure (opening/closing braces) must remain valid after comment processing.

## Tasks / Subtasks

- [x] Task 1: Reproduce failure case (AC: 1, 2)
  - [x] Add unit test with the specific failing snippet:
    ```scss
    // All styles added with di-group-holman-automotive plugin
    // // .results-featured-facets .quick-facets-container .facet-link .feature-icon svg {
    fill: var(--primary) !important;
    }
    ```
- [x] Task 2: Fix Regex Logic (AC: 1, 2, 3)
  - [x] Update `sbm/scss/processor.py` to use safer parsing or corrected regex.
  - [x] Verify against the new test case.

## Dev Notes

- The previous regex `re.sub(r"//\s*(?://\s*)*\s*\/\*[\s\S]*?\*/", "", content)` was too aggressive.
- Consider parsing line-by-line or using a more constrained regex that ensures `/*` is part of the comment line, not a subsequent block start.

### References

- User reported failure in `sbm` tool during migration.
