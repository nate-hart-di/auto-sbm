# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-07-29

### Changed

- **Major Refactor of SCSS Migration Logic**: The core `SCSSProcessor` has been completely rebuilt to improve reliability and correctness during theme migrations.
  - **Removed Fragile Regex Processing**: The previous implementation relied on a series of complex and brittle regular expressions to parse and categorize SCSS rules. This approach frequently caused syntax errors, incorrect style categorization, and failures on complex themes.
  - **Introduced Mixin Inlining**: The new processor now intelligently discovers all mixin definitions within the `DealerInspireCommonTheme`, parses their structure (including arguments), and directly inlines them wherever an `@include` is found in the source theme.
  - **Self-Contained Output**: The processor removes all `@import` statements from the final output, creating clean, self-contained `sb-inside.scss`, `sb-vdp.scss`, and `sb-vrp.scss` files that are ready for use without any external dependencies.
  - **Improved Reliability**: This new compiler-first approach eliminates the entire class of errors related to regex parsing and ensures that the generated SCSS is always syntactically valid and correct.
