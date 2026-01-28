# PRD: Lexus Map Migration Analysis

## Overview
Conduct a deep-dive analysis of the Lexus OEM map style migration failure. Determine precisely why the current automation fails to migrate Lexus map styles to `sb-inside.scss` and identify the specific patterns associated with `lexusofatlanticcity`, `tustinlexus`, and `lexusofalbuquerque`. This is a **Discovery & Determination** effort, not an implementation effort.

## Problem Statement
- **Lexus Map Styles:** Currently failing to migrate automatically or staying in `style.scss` instead of `sb-inside.scss`.
- **Broken Components:** Incorrect migration leads to broken forms and dealer info boxes.
- **Root Cause Unknown:** The specific reason why current detection logic fails for these sites is not fully documented.

## Functional Requirements (FRs)
- **FR1:** Analyze the existing `sbm/core/maps.py` and `sbm/oem/lexus.py` logic to document exactly how it currently identifies and migrates map components.
- **FR2:** Deep-dive analysis of specific PRs (`21434`, `21462`, `21393`, `21391`) using `gh` CLI to extract file changes, commit messages, and specific code patterns.
- **FR3:** **Comprehensive Comparison:** Analyze **every single successful Lexus migration** in history (using `gh` or history data) to identify the patterns that worked.
- **FR4:** Document the gap analysis: explicitly state *why* the current logic fails for the problematic sites and *why* it succeeded for others.
- **FR5:** **Root Cause Identification:** Define the exact conditions that cause migration failure, covering all edge cases.
- **FR6:** **Bulletproof Solution Definition:** Define a robust solution strategy that handles all identified failure modes and potential unknown paths.
- **FR7:** Produce a "Determination Report" outlining the findings and the proposed solution.

## Non-Functional Requirements (NFRs)
- **NFR1:** **Thoroughness:** Analyze ALL successful Lexus migrations, not just a sample.
- **NFR2:** **Accuracy:** Findings must be evidence-based from actual PR data.
- **NFR3:** **Safety:** No code changes during this phase.
- **NFR4:** **Predictive:** Account for potential future failure paths/patterns.

## Specific Site Context
- **Target Analysis Slugs:** `lexusofatlanticcity`, `tustinlexus`, `lexusofalbuquerque`.
- **Reference PRs:** 21434, 21462, 21393, 21391.
- **Reference Branch:** `pcon-727-lexusofatlanticcity-sbm0126`.
