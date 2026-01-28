---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
inputDocuments:
  - /Users/nathanhart/.claude/plans/enumerated-petting-puffin.md
  - /Users/nathanhart/auto-sbm/_bmad-output/architecture.md
  - /Users/nathanhart/auto-sbm/_bmad-output/planning-artifacts/PRD.md
  - /Users/nathanhart/auto-sbm/_bmad-output/planning-artifacts/architecture.md
---

# auto-sbm - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for auto-sbm, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Enhance `sbm stats --history` to display Duration, Lines Migrated, Time Saved, and Report Path.
FR2: Add CLI filtering options: `--limit`, `--since`, `--until`, `--user`.
FR3: Generate detailed markdown migration reports in `.sbm-reports/`.
FR4: **Mandatory Firebase Sync.** System MUST sync migration stats to Firebase Realtime Database for team-wide tracking.
FR5: **Background Sync:** Reliable background process to ensure sync completes without blocking CLI.
FR6: **Offline Queue:** Robust offline support that queues writes and strictly enforcing sync when connectivity is restored.
FR7: Provide data migration script for existing local stats.
FR8: Display aggregated team statistics from Firebase source.
FR9: **Bulk Duplicate Prevention:** Pre-flight check for bulk commands (`sbm @file`) that warns users if any input slugs have already been successfully migrated (checked against global history).

**Lexus Map Migration Analysis:**
FR10: Analyze the existing `sbm/core/maps.py` and `sbm/oem/lexus.py` logic to document exactly how it currently identifies and migrates map components.
FR11: Deep-dive analysis of specific PRs (21434, 21462, 21393, 21391) using gh CLI to extract file changes, commit messages, and specific code patterns.
FR12: Comprehensive Comparison - Analyze every single successful Lexus migration in history to identify the patterns that worked.
FR13: Document the gap analysis - explicitly state why the current logic fails for the problematic sites and why it succeeded for others.
FR14: Root Cause Identification - Define the exact conditions that cause migration failure, covering all edge cases.
FR15: Bulletproof Solution Definition - Define a robust solution strategy that handles all identified failure modes and potential unknown paths.
FR16: Produce a "Determination Report" outlining the findings and the proposed solution.

### NonFunctional Requirements

NFR1: **Local-First Reliability:** System functions offline but treats Sync as a guaranteed eventual consistency requirement.
NFR2: **Performance:** History queries < 2s.
NFR3: **Resilience:** Auto-retry logic for failed syncs.
NFR4: **Security:** Team-scoped access rules.
NFR5: **Tech Stack:** Python 3.9+, Click, Rich, `firebase-admin`.

**Lexus Map Migration Analysis:**
NFR6: **Thoroughness** - Analyze ALL successful Lexus migrations, not just a sample.
NFR7: **Accuracy** - Findings must be evidence-based from actual PR data.
NFR8: **Safety** - No code changes during this phase.
NFR9: **Predictive** - Account for potential future failure paths/patterns.

### Additional Requirements

- **Dependencies:** Add `firebase-admin`.
- **Configuration:** Update `.env` and `config.py` with Firebase credentials.
- **Structure:** New modules `sbm/utils/report_generator.py` and `sbm/utils/firebase_sync.py`.
- **Refactoring:** The implementation plan needs to integrate Firebase logic directly into the core `tracker.py` and `cli.py` workflow immediately, not as an afterthought.

### FR Coverage Map

FR1: Epic 1 - Enhanced CLI table
FR2: Epic 1 - CLI query options
FR3: Epic 1 - Report generator module
FR4: Epic 2 - Core sync logic
FR5: Epic 2 - Threading/Async implementation
FR6: Epic 2 - Queue manager
FR7: Epic 2 - Import script
FR8: Epic 2 - Aggregated read logic
FR9: Epic 2 - Bulk duplicate prevention
FR10: Epic 4 - Analyze current map migration logic
FR11: Epic 4 - Analyze specific problem PRs
FR12: Epic 4 - Comprehensive historical Lexus migration analysis
FR13: Epic 4 - Document gap analysis
FR14: Epic 4 - Root cause identification
FR15: Epic 5 - Design bulletproof solution strategy
FR16: Epic 5 - Create determination report

## Epic List

### Epic 1: Rich Migration Insights & Reporting
**Goal:** Provide users with comprehensive local visibility into migration performance and deep-dive artifacts, eliminating "blind spots" in the current CLI and establishing the full data schema.
**FRs covered:** FR1, FR2, FR3

### Epic 2: Robust Team-Wide Synchronization
**Goal:** Establish a reliable, real-time source of truth for the team stats, replacing the noisy git-based system with a resilient, offline-capable Firebase sync.
**FRs covered:** FR4, FR5, FR6, FR7, FR8, FR9

### Epic 3: Data Quality & Accuracy
**Goal:** Ensure stats calculations are accurate and reflect real data without artificial inflation or estimation fallbacks.
**FRs covered:** (Data quality requirements)

### Epic 4: Lexus Map Migration - Deep-Dive Investigation & Root Cause Analysis
**Goal:** Conduct comprehensive analysis of current Lexus map migration logic, gather all historical evidence from PRs, and identify the exact root causes of migration failures.
**FRs covered:** FR10, FR11, FR12, FR13, FR14

### Epic 5: Lexus Map Migration - Solution Strategy & Determination Report
**Goal:** Design a bulletproof solution strategy that handles all identified failure modes and produce a comprehensive determination report for implementation teams.
**FRs covered:** FR15, FR16

## Epic 1: Rich Migration Insights & Reporting

Provide users with comprehensive local visibility into migration performance and deep-dive artifacts, eliminating "blind spots" in the current CLI and establishing the full data schema.

### Story 1.1: Migration Data Schema & Tracking Logic

As a Developer,
I want to update the internal tracking logic to capture rich metrics like duration and lines migrated,
So that this data is available for reporting and historical analysis.

**Acceptance Criteria:**

**Given** a migration is currently running
**When** the migration completes (success or failure)
**Then** the `record_run` function captures: duration_seconds, lines_migrated, files_created_count, and scss_line_count
**And** the `MigrationRun` data class is updated to support these new fields
**And** the existing `~/.sbm_migrations.json` schema is updated non-destructively

### Story 1.2: Detailed Report Generation

As a User,
I want a detailed markdown report generated after every migration,
So that I can review exactly what changed, what files were created, and how much manual effort was saved.

**Acceptance Criteria:**

**Given** a successful migration run
**When** the process finishes
**Then** a new markdown file is created in `.sbm-reports/{slug}-{timestamp}.md`
**And** the report contains: Summary, File Breakdown, Component Details, and Time Savings analysis
**And** an `index.md` in `.sbm-reports/` is updated with a link to the new report
**And** the report path is returned to the tracker for storage

### Story 1.3: Enhanced CLI History Display

As a User,
I want `sbm stats --history` to show me duration, lines migrated, and report locations,
So that I have a complete picture of my migration activity without checking log files.

**Acceptance Criteria:**

**Given** I have migration history with the new rich data
**When** I run `sbm stats --history`
**Then** the table displays new columns: "Duration", "Lines", "Saved", and "Report"
**And** "Duration" is formatted nicely (e.g., "1m 30s")
**And** "Report" shows the relative path to the generated markdown file
**And** old migration records display "N/A" for missing data columns gracefully

### Story 1.4: History Filtering & Pagination

As a User,
I want to filter my migration history by date, user, or limit,
So that I can find specific runs easily without scrolling through hundreds of entries.

**Acceptance Criteria:**

**Given** I have a large history of migrations
**When** I run `sbm stats --history --limit 5`
**Then** only the 5 most recent runs are shown
**When** I run `sbm stats --history --since 2024-01-01`
**Then** only runs from that date onwards are shown
**When** I run `sbm stats --history --user nate-hart-di`
**Then** only runs by that specific user are shown

## Epic 2: Robust Team-Wide Synchronization

Establish a reliable, real-time source of truth for the team stats, replacing the noisy git-based system with a resilient, offline-capable Firebase sync.

### Story 2.1: Firebase Infrastructure Setup

As a Developer,
I want to set up the Firebase infrastructure and dependencies,
So that the application can connect to the remote database securely.

**Acceptance Criteria:**

**Given** the project codebase
**When** I install dependencies
**Then** `firebase-admin` is added to `pyproject.toml`
**And** `.env.example` is updated with `FIREBASE_CREDENTIALS_PATH` and `FIREBASE_DB_URL`
**And** `config.py` loads these new variables
**And** a service account JSON can be loaded successfully by the application

### Story 2.2: Core Realtime Sync

As a User,
I want my migration stats to be sent to the cloud immediately,
So that my team knows what I'm working on in real-time.

**Acceptance Criteria:**

**Given** a configured Firebase connection
**When** a migration finishes successfully
**Then** the `FirebaseSync` class pushes the run data to `/users/{user_id}/runs/{run_id}`
**And** the data includes local fields plus the new global fields (duration, report path)
**And** the write operation is confirmed by the server
**And** any connection errors are logged but do not crash the application

### Story 2.3: Resilience & Offline Queue

As a Mobile User,
I want my stats to be saved even when I'm offline,
So that I don't lose data or get blocked by connection errors.

**Acceptance Criteria:**

**Given** I am offline or Firebase is down
**When** I complete a migration
**Then** the CLI does NOT hang or crash
**And** the run is marked as "pending_sync" in the local JSON
**And** a background thread attempts to sync pending items when the application starts or finishes a run
**And** the system retries failed uploads automatically

### Story 2.4: Team Stats Aggregation

As a Team Lead,
I want to see the combined statistics of the entire team,
So that I can report on overall progress.

**Acceptance Criteria:**

**Given** multiple users are syncing data
**When** I run `sbm stats --team` (or default view)
**Then** the system queries the Firebase root (or specific indices) to aggregate totals
**And** it displays "Team Total Migrations" and "Team Total Time Saved"
**And** the fetching is fast (<2s) and fails gracefully to local-only stats if offline

### Story 2.5: Bulk Migration Duplicate Prevention (FR9)

As a User performing bulk operations,
I want to be warned if I'm about to run a migration that my teammate has already done,
So that I don't waste time or create duplicate PRs.

**Acceptance Criteria:**

**Given** I run `sbm @input_file.txt` containing list of slugs
**When** the CLI parses the list
**Then** it queries the global Firebase history for any successful migrations matching those slugs
**And** it displays a warning: "⚠️ The following 3 slugs have already been migrated by [User]: ..."
**And** it prompts me to "Skip duplicates? [Y/n]"
**And** if I say Yes, it removes them from the execution list
**And** if offline, it warns "Cannot check global history (Offline)" but proceeds with local checks

### Story 2.6: Legacy Data Import Utility

As a User,
I want to upload my old local history to the new system,
So that the team stats reflect all previous work, not just new runs.

**Acceptance Criteria:**

**Given** I have a `~/.sbm_migrations.json` full of history
**When** I run `scripts/stats/migrate_to_firebase.py`
**Then** it reads all local runs
**And** it uploads any runs missing from Firebase
**And** it handles duplicates (idempotency)
**And** it provides a progress bar and final summary of "Imported X runs"

### Story 2.7: Firebase-First Architecture & Security Evolution

As a Team Lead,
I want Firebase to be the single source of truth for all migration stats with proper security controls,
So that all users can read team data without admin credentials while maintaining centralized, always-synced statistics.

**Acceptance Criteria:**

**Given** the current dual-system architecture (Firebase + git-based stats)
**When** any user runs `sbm stats` or `sbm stats --team`
**Then** the command queries Firebase directly as the primary source
**And** local JSON files serve only as operational cache for offline queue
**And** git-based stats files (`stats/*.json`) are no longer written or committed
**And** no git commits are created for stats updates

**Given** a team member without Firebase admin credentials
**When** they run `sbm` commands on their machine
**Then** the CLI automatically authenticates with read-only Firebase access
**And** their migration runs are successfully written to Firebase
**And** they can query team stats without any credential configuration
**And** no Firebase credentials are required in their `.env` file

**Given** I am the primary developer with admin access
**When** I configure Firebase admin credentials
**Then** I have full read/write access to all Firebase data
**And** I can manage Firebase security rules
**And** my credentials are stored securely and never committed to git

**Given** any user runs stats commands
**When** they execute `sbm stats`, `sbm stats --history`, or `sbm stats --team`
**Then** all data is fetched from Firebase in real-time
**And** offline mode shows clear message: "Stats unavailable (offline mode)"
**And** no fallback to git-based stats occurs
**And** performance remains under 2 seconds for all queries

## Epic 3: Data Quality & Accuracy

Ensure stats calculations are accurate and reflect real data without artificial inflation or estimation fallbacks.

### Story 3.1: Fix Stats Calculation Inflation

As a User,
I want the CLI stats to accurately reflect my actual migration work without inflated estimates,
So that I can trust the numbers shown in `sbm stats` and they match the real data in Firebase.

**Acceptance Criteria:**

**Given** I have 164 unique migrations in Firebase with varying data completeness
**When** I run `sbm stats`
**Then** the displayed line count reflects ONLY actual merged PR data from Firebase
**And** migrations without PR data are NOT inflated with 500-line estimates
**And** duplicate runs for the same slug are handled correctly
**And** the "Sites Migrated" count shows unique migrations (164)
**And** the "Lines Migrated" count shows actual sum from `lines_migrated` field

**Given** I have MERGED PRs with `lines_migrated = 0` in Firebase
**When** the backfill script runs
**Then** it populates these runs with actual GitHub PR line counts
**And** duplicate runs for the same slug get deduplicated (LATEST run keeps lines, older runs set to 0)
**And** all MERGED PRs have accurate line counts after backfill

---

## Epic 4: Lexus Map Migration - Deep-Dive Investigation & Root Cause Analysis

**Goal:** Conduct comprehensive analysis of current Lexus map migration logic, gather all historical evidence from PRs, and identify the exact root causes of migration failures.

**User Outcome:** Developer has complete understanding of how the system works, evidence-based analysis of all historical Lexus migrations, and definitive explanation of why certain sites fail.

**Functional Requirements Covered:**
- FR10: Analyze the existing `sbm/core/maps.py` and `sbm/oem/lexus.py` logic to document exactly how it currently identifies and migrates map components
- FR11: Deep-dive analysis of specific PRs (21434, 21462, 21393, 21391) using gh CLI to extract file changes, commit messages, and specific code patterns
- FR12: Comprehensive Comparison - Analyze every single successful Lexus migration in history to identify the patterns that worked
- FR13: Document the gap analysis - explicitly state why the current logic fails for the problematic sites and why it succeeded for others
- FR14: Root Cause Identification - Define the exact conditions that cause migration failure, covering all edge cases

### Story 4.1: Analyze Current Map Migration Logic

As a Developer,
I want to thoroughly analyze the existing `sbm/core/maps.py` and `sbm/oem/lexus.py` code,
So that I understand exactly how map components are currently identified and migrated for Lexus sites.

**Acceptance Criteria:**

**Given** the codebase with map migration logic
**When** I read and analyze `sbm/core/maps.py` and `sbm/oem/lexus.py`
**Then** I can document the complete logic flow for map component detection
**And** I can explain the decision logic for placing styles in `sb-inside.scss` vs `style.scss`
**And** I can identify all conditionals, pattern matching, and OEM-specific handling
**And** I create a flowchart or detailed documentation of the current process

### Story 4.2: Trace SCSS Processing & Classification Logic

As a Developer,
I want to trace how SCSS styles flow through the processor and classifier,
So that I understand how style placement decisions are made and where Lexus map styles might be misclassified.

**Acceptance Criteria:**

**Given** the SCSS transformation pipeline
**When** I analyze `sbm/scss/processor.py` and `sbm/scss/classifiers.py`
**Then** I can document the data flow: Legacy theme → SCSS Processor → OEM Handler → Map Migrator → File placement
**And** I can identify all classification rules that determine style placement
**And** I can pinpoint where map-related styles are processed
**And** I document any Lexus-specific processing paths

### Story 4.3: Analyze Specific Problem PRs

As a Developer,
I want to extract and analyze the specific PRs for failed migrations (21434, 21462, 21393, 21391),
So that I can see exactly what patterns, file changes, and issues occurred in the problematic sites.

**Acceptance Criteria:**

**Given** the PR numbers for failed migrations
**When** I use `gh` CLI to fetch PR details, file diffs, and commit messages
**Then** I extract all SCSS changes for `lexusofatlanticcity`, `tustinlexus`, and `lexusofalbuquerque`
**And** I identify which styles ended up in wrong files
**And** I document the specific patterns present in these sites
**And** I note any error messages, manual fixes, or special handling applied

### Story 4.4: Comprehensive Historical Lexus Migration Analysis

As a Developer,
I want to analyze every single successful Lexus migration in the project history,
So that I can identify patterns that worked and create a baseline for comparison.

**Acceptance Criteria:**

**Given** access to GitHub PR history via `gh` CLI or Firebase migration data
**When** I query for all Lexus-related migration PRs with status "merged" or "success"
**Then** I create a comprehensive dataset with: site slug, PR number, files changed, SCSS patterns, outcome
**And** I identify common patterns in successful migrations
**And** I document any variations in successful approaches
**And** I categorize Lexus sites by migration success patterns

### Story 4.5: Gap Analysis & Root Cause Identification

As a Developer,
I want to compare successful vs failed migrations to pinpoint exact failure conditions,
So that I can definitively state why certain Lexus sites fail while others succeed.

**Acceptance Criteria:**

**Given** data from successful migrations and failed migrations
**When** I perform comparative analysis
**Then** I identify the exact differences in SCSS patterns between successful and failed sites
**And** I document edge cases and conditions that trigger failures
**And** I explain why the current logic fails for `lexusofatlanticcity`, `tustinlexus`, `lexusofalbuquerque`
**And** I explain why it succeeded for other Lexus sites
**And** I document all root causes with evidence from PR data

---

## Epic 5: Lexus Map Migration - Solution Strategy & Determination Report

**Goal:** Design a bulletproof solution strategy that handles all identified failure modes and produce a comprehensive determination report for implementation teams.

**User Outcome:** Developer has validated solution strategy and deliverable report that can guide immediate implementation.

**Functional Requirements Covered:**
- FR15: Bulletproof Solution Definition - Define a robust solution strategy that handles all identified failure modes and potential unknown paths
- FR16: Produce a "Determination Report" outlining the findings and the proposed solution

### Story 5.1: Design Bulletproof Solution Strategy

As a Developer,
I want to design a robust solution that handles all identified failure modes and edge cases,
So that future Lexus map migrations will succeed consistently without manual intervention.

**Acceptance Criteria:**

**Given** root causes identified in Epic 4
**When** I design the solution strategy
**Then** the solution addresses every identified failure condition
**And** the solution accounts for potential future failure paths not yet encountered
**And** the solution maintains backward compatibility with successful migrations
**And** I document the implementation approach with code examples or pseudocode
**And** I identify which files need modification (`sbm/core/maps.py`, `sbm/oem/lexus.py`, etc.)
**And** I consider predictive requirements by accounting for unknown edge cases

### Story 5.2: Create Comprehensive Determination Report

As a Developer,
I want to produce a final determination report documenting all findings and the proposed solution,
So that implementation teams have a clear, actionable document to guide their work.

**Acceptance Criteria:**

**Given** all analysis from Epic 4 and solution strategy from Story 5.1
**When** I create the determination report
**Then** the report includes an executive summary of the problem
**And** the report documents the current system behavior with evidence
**And** the report includes the historical analysis findings
**And** the report clearly states all root causes with supporting data
**And** the report presents the bulletproof solution strategy
**And** the report includes implementation guidance (files to modify, code examples, test scenarios)
**And** the report is saved as a markdown document in the appropriate location
**And** the report is evidence-based throughout (NFR: Accuracy)
