# Epic Blitz — Subagent-Orchestrated Epic Implementation

<critical>NO TIME ESTIMATES. NEVER mention hours, days, weeks, months.</critical>
<critical>Communicate in {communication_language}. Skill level: {user_skill_level}.</critical>

## Overview

This workflow implements entire epics via background Claude Code `Task` subagents, with **git commit gates** between each epic providing clean rewind points.

**Actors:**

- **Orchestrator** (you, the main agent): Pipeline management, context assembly, verification, fixes, commits
- **Subagent** (background Task agent): Implements one epic — all code, tests, and story documentation

**Gate flow per epic:**

```
SNAPSHOT → BUILD PROMPT → LAUNCH → VERIFY → [FIX] → COMMIT → ADVANCE
```

**Commit strategy:** One commit per epic. `git log --oneline` shows discrete rewind points. `git revert <hash>` undoes one epic cleanly.

---

## Phase 0: Pre-flight

### 0.1 Determine Scope

Parse `epic_range` from workflow arguments:

- Explicit range: `"2-5"` → Epics 2, 3, 4, 5
- Single epic: `"3"` → Epic 3 only
- Auto-detect: `""` → Find next undone epic(s) from sprint-status

### 0.2 Verify Clean State

Run these checks. **HALT if any fail:**

```bash
git status                      # Working tree clean (or user acknowledges)
npx tsc --noEmit                # Zero type errors
NODE_ENV=test npx vitest run    # All tests pass
```

Record baseline metrics:

- `BASELINE_TEST_COUNT` — number of passing tests
- `BASELINE_COMMIT` — current `git rev-parse HEAD`

### 0.3 Load Planning Context

Read these files ONCE (they don't change between epics):

- `{sprint_status}` — epic/story completion status
- `{epics_file}` — story definitions and acceptance criteria
- `{architecture_file}` — architecture decisions (D1–D9)
- `{gui_rules}` — naming conventions, architecture rules, test patterns
- `{project_context}` — CLI rules, platform knowledge

Verify **all dependency epics** for the range are `done` in sprint-status.

### 0.4 Build Epic Queue

Create ordered list of epics to implement. For each epic, extract from the epics file:

- Epic number and title
- Story definitions (number, title, acceptance criteria)
- Story count
- Dependencies on other epics

Initialize: `ACCUMULATED_LESSONS = ""`

---

## Phase 1: Epic Loop

For each epic `N` in the queue, execute ALL gates in order. **Never skip a gate.**

### Gate 1: CONTEXT SNAPSHOT

Read the **CURRENT** content of ALL shared files listed in `workflow.yaml:shared_files`. These files change between epics as each subagent modifies them.

```
src/shared/types.ts              # THE integration contract
src/server/app.ts                # Route registration, middleware, startup
src/server/db/schema.ts          # Drizzle schema definitions
src/client/lib/api.ts            # Frontend API client functions
src/client/pages/DashboardPage.tsx
src/client/pages/SettingsPage.tsx
src/client/pages/SiteDetailPage.tsx
src/server/services/testService.ts
src/server/services/settingsService.ts
src/server/services/sshOrchestrator.ts
src/server/plugins/sse.ts
```

**CRITICAL:** Read ALL files fresh. NEVER reuse content from a previous epic — the files have changed.

Also record current test count: `NODE_ENV=test npx vitest run 2>&1 | grep "Tests"`.

### Gate 2: BUILD SUBAGENT PROMPT

Fill in the **Subagent Prompt Template** (Section 4) with:

| Placeholder | Source |
|---|---|
| `{{EPIC_NUMBER}}` | Current epic number |
| `{{EPIC_TITLE}}` | From epics file |
| `{{STORY_DEFINITIONS}}` | Full story text from epics file for this epic |
| `{{SHARED_FILE: filename}}` | Fresh content from Gate 1 |
| `{{ACCUMULATED_LESSONS}}` | Lessons from previous epics in this session |
| `{{CURRENT_TEST_COUNT}}` | Test count from Gate 1 |
| `{{DATE}}` | Today's date |

### Gate 3: LAUNCH SUBAGENT

Launch via Task tool:

```
Task:
  subagent_type: general-purpose
  model: {subagent_model}
  run_in_background: true
  description: "Implement Epic N: [title]"
  prompt: [filled template from Gate 2]
```

Monitor via `TaskOutput` with `block: false` periodically until completion.

When complete, read the full output to understand what was implemented.

### Gate 4: VERIFY

Run both commands:

```bash
npx tsc --noEmit
NODE_ENV=test npx vitest run
```

**Pass criteria:** Zero tsc errors AND all vitest tests pass.

- If **PASS** → proceed to Gate 6 (COMMIT)
- If **FAIL** → proceed to Gate 5 (FIX)

### Gate 5: FIX PASS

Fix failures **directly** (not via subagent — faster and more targeted for small issues).

**Fix budget:** 3 attempts per epic. After each fix, re-run Gate 4.

**Common fix patterns** (see Section 5 for details):

1. **ESM imports** — Replace `require()` with `await import()` in test files
2. **JSX in tests** — Rename `.test.ts` → `.test.tsx` for files containing JSX
3. **Mock types** — Use `as ReturnType<typeof hookName>` for TanStack Query mocks
4. **Infrastructure guards** — Add `NODE_ENV !== 'test'` for real service connections (pg-boss, Slack, etc.)
5. **Regex mismatches** — Update test assertions to match actual rendered output
6. **Missing mock properties** — Add `isInitialLoading`, `isEnabled` etc. to TanStack Query mocks

If all 3 attempts exhausted → **HALT**, report status and remaining errors to user.

### Gate 6: COMMIT

Stage and commit all files for this epic:

```bash
git add [all new and modified files]
git commit -m "feat(gui): implement Epic N — [title]

Stories: N.1–N.M (M stories)
Tests: X passing (was Y)

Co-Authored-By: Claude [model] <noreply@anthropic.com>"
```

Record commit hash for rewind reference.

**Important:** Use specific `git add` for files, not `git add -A`. Review what's being staged.

### Gate 7: ADVANCE

1. **Verify sprint-status** was updated by subagent. If not, update manually:
   - Mark each story as `done`
   - Mark the epic as `done`
   - Update phase status if all epics in the phase are complete

2. **Accumulate lessons** — append to `ACCUMULATED_LESSONS`:
   - What issues did the fix pass address?
   - What patterns should future subagents avoid?
   - Any surprising behavior or gotchas?

3. **Report epic completion:**
   - Epic number and title
   - Stories completed
   - Test count: before → after
   - Commit hash
   - Lessons learned
   - Epics remaining in queue

4. **Proceed** to next epic in queue (back to Gate 1).

---

## Phase 2: Post-flight

### Final Verification

```bash
npx tsc --noEmit
NODE_ENV=test npx vitest run
```

### Summary Report

```
EPIC BLITZ COMPLETE
═══════════════════════════════════════
Epics implemented: [list]
Total stories: N
Test progression: baseline → ... → final
Commit log:
  abc1234 feat(gui): implement Epic 2 — Fleet Health Dashboard
  def5678 feat(gui): implement Epic 3 — System Configuration
  ...

Rewind points:
  To undo Epic 5: git revert jkl3456
  To undo Epics 4-5: git revert jkl3456 ghi9012
  To return to baseline: git reset --hard {BASELINE_COMMIT}
═══════════════════════════════════════
```

---

## Section 4: Subagent Prompt Template

Everything between `---BEGIN PROMPT---` and `---END PROMPT---` is the template. Fill all `{{PLACEHOLDERS}}` before sending.

---BEGIN PROMPT---

You are implementing **Epic {{EPIC_NUMBER}}: {{EPIC_TITLE}}** for the DI Form Buddy GUI project.

## Your Mission

Implement ALL stories in this epic. For each story:

1. Create server-side code (services, routes, types)
2. Create client-side code (components, hooks, API functions)
3. Create comprehensive tests for ALL new code
4. Create story documentation file in `_bmad-output/implementation-artifacts/`
5. Update `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Project Conventions (MUST FOLLOW)

### Technology Stack

| Layer | Choice |
|---|---|
| Frontend | React 19 + Vite + TypeScript + Tailwind + shadcn/ui |
| Backend | Fastify 5 |
| Database | PostgreSQL 16 + Drizzle ORM |
| Testing | Vitest + React Testing Library |
| State | TanStack Query (NO useEffect+fetch) |
| Real-time | SSE (NOT WebSocket) |
| Job Queue | pg-boss 12.11.1 (PostgreSQL-backed, no Redis) |

### Architecture Rules (MANDATORY)

1. **ALL pod communication through `executePodCommand()`** — never direct SSH
2. **Database queries in service files ONLY** — no Drizzle imports in routes
3. **No `useEffect` + `fetch`** — TanStack Query ONLY for server state
4. **SSE via discriminated union** — no type casts, narrow via `event.type`
5. **API envelope**: `{ data: T }` success / `{ error: { code, message } }` error
6. **Errors**: throw `AppError` with `ErrorCode` from `shared/types.ts`
7. **snake_case→camelCase boundary** in `parsePhpOutput.ts` ONLY. No other code sees snake_case.

### Naming Conventions

| Layer | Convention | Example |
|---|---|---|
| DB tables/columns | `snake_case` | `test_results.site_id` |
| TypeScript vars/functions | `camelCase` | `siteId`, `getTestResults()` |
| TypeScript types/interfaces | `PascalCase` | `TestResult` |
| React components | `PascalCase.tsx` | `StatusIcon.tsx` |
| API JSON | `camelCase` | `{ "formId": 5 }` |
| API URLs | `kebab-case` | `/api/test-runs/:id` |
| Constants | `SCREAMING_SNAKE` | `DEFAULT_POD_CONCURRENCY` |
| Hooks | `use` prefix | `useTestResults.ts` |
| Tests | `.test.ts` / `.test.tsx` | `sshOrchestrator.test.ts` |
| TS modules | `camelCase.ts` | `sshOrchestrator.ts` |

### Test Patterns (CRITICAL — read carefully)

- Use **`.test.tsx`** (not `.test.ts`) for ANY test file containing JSX (React component tests, hook tests with renderHook)
- Use **`await import()`** instead of `require()` — this is an ESM project
- Use **`as ReturnType<typeof hookName>`** for TanStack Query mock type completeness (avoids exhaustive property listing)
- Add **`NODE_ENV !== 'test'`** guard for ANY infrastructure that connects to real services (pg-boss, Slack bolt, database pools, etc.) in `app.ts`
- Tests mirror `src/` structure under `tests/` directory
- Mock external services, never call real APIs/databases in tests
- Use `vi.mock()` at top of test file for module mocking

### File Locations

```
src/client/components/custom/    # Custom React components
src/client/components/ui/        # shadcn/ui primitives
src/client/hooks/                # Custom TanStack Query hooks
src/client/pages/                # Page components
src/client/lib/                  # API client, utilities
src/server/routes/               # Fastify route handlers
src/server/services/             # Business logic + DB queries
src/server/lib/                  # Utilities (errors, encryption, parsing)
src/server/db/                   # Drizzle schema
src/server/plugins/              # Fastify plugins (SSE)
src/shared/                      # Integration contract (types.ts)
tests/                           # Mirrors src/ structure
_bmad-output/implementation-artifacts/  # Story docs + sprint-status
```

## Current Codebase State

Read these files to understand the current state before modifying them. **Add to them, don't overwrite:**

### src/shared/types.ts (THE integration contract)

```typescript
{{SHARED_FILE: src/shared/types.ts}}
```

### src/server/app.ts (register new routes and plugins here)

```typescript
{{SHARED_FILE: src/server/app.ts}}
```

### src/server/db/schema.ts (add new tables/columns here)

```typescript
{{SHARED_FILE: src/server/db/schema.ts}}
```

### src/client/lib/api.ts (add new API functions here)

```typescript
{{SHARED_FILE: src/client/lib/api.ts}}
```

### src/client/pages/DashboardPage.tsx

```typescript
{{SHARED_FILE: src/client/pages/DashboardPage.tsx}}
```

### src/client/pages/SettingsPage.tsx

```typescript
{{SHARED_FILE: src/client/pages/SettingsPage.tsx}}
```

### src/client/pages/SiteDetailPage.tsx

```typescript
{{SHARED_FILE: src/client/pages/SiteDetailPage.tsx}}
```

### src/server/services/testService.ts

```typescript
{{SHARED_FILE: src/server/services/testService.ts}}
```

### src/server/services/settingsService.ts

```typescript
{{SHARED_FILE: src/server/services/settingsService.ts}}
```

### src/server/services/sshOrchestrator.ts

```typescript
{{SHARED_FILE: src/server/services/sshOrchestrator.ts}}
```

### src/server/plugins/sse.ts

```typescript
{{SHARED_FILE: src/server/plugins/sse.ts}}
```

## Stories to Implement

{{STORY_DEFINITIONS}}

## Story Documentation

For each story, create a file at:
`_bmad-output/implementation-artifacts/gui-{{EPIC_NUMBER}}-{story_num}-{slug}.md`

Use this structure:

```markdown
# Story gui-{epic}-{story}: {Title}

**Priority:** P1
**Status:** done
**Created:** {date}
**Epic:** {epic_number} — {epic_title}

## Problem
[One paragraph]

## Acceptance Criteria
[From epics file]

## Implementation Summary
[What was built, key decisions]

## Files Changed

### NEW
- [list new files with brief description]

### MODIFIED
- [list modified files with what changed]

## Dev Agent Record
- Agent: Claude {model}
- Date: {date}
- Tests: {count} passing
```

## Sprint Status Update

After implementing ALL stories, update `_bmad-output/implementation-artifacts/sprint-status.yaml`:

- Mark each story key as `done` (e.g., `gui-2-1-dashboard-metrics: done`)
- Mark the epic as `done` (e.g., `epic-2-gui: done`)
- Update phase status if all epics in the phase are now complete
- Preserve ALL existing comments and structure in the file

## Lessons from Previous Epics

{{ACCUMULATED_LESSONS}}

## Verification (MANDATORY)

Before reporting completion, run BOTH:

```bash
npx tsc --noEmit
NODE_ENV=test npx vitest run
```

**Both must pass with ZERO errors.** Fix any failures before declaring done.

Report your final test count. Current baseline: **{{CURRENT_TEST_COUNT}}** tests passing.

---END PROMPT---

---

## Section 5: Known Gotchas & Baked-In Lessons

These patterns were discovered during the initial Epic 2-5 implementation run and are now encoded into the subagent prompt. Document new patterns here as they're discovered.

### 5.1 pg-boss Test Isolation

**Problem:** pg-boss tries to connect to real PostgreSQL during test runs, causing `Queue does not exist` errors across all test files.

**Fix:** Guard pg-boss initialization in `app.ts`:

```typescript
if (process.env.DATABASE_URL && process.env.NODE_ENV !== 'test') {
  const boss = new PgBoss(process.env.DATABASE_URL);
  await boss.start();
  // ...
}
```

**Applies to:** Any infrastructure that connects to external services (Slack bolt, database pools, etc.)

### 5.2 ESM Import Pattern in Tests

**Problem:** `require()` doesn't work in ESM projects. Tests using `require()` fail with `Cannot use require in ESM`.

**Fix:** Replace with dynamic import:

```typescript
// BAD
const { useSchedulerStatus } = require('../../../src/client/hooks/useScheduler');

// GOOD
const { useSchedulerStatus } = await import('../../../src/client/hooks/useScheduler');
```

### 5.3 JSX in Test Files

**Problem:** Test files with `.test.ts` extension that contain JSX (component renders, `renderHook`) fail with TypeScript parse errors.

**Fix:** Use `.test.tsx` extension for any test containing JSX.

### 5.4 TanStack Query Mock Completeness

**Problem:** `useQuery` return type has many properties (`isInitialLoading`, `isEnabled`, `dataUpdatedAt`, etc.). Listing them all manually is fragile.

**Fix:** Use type assertion:

```typescript
vi.mocked(useMyHook).mockReturnValue({
  data: mockData,
  isPending: false,
} as ReturnType<typeof useMyHook>);
```

### 5.5 AppError Handler Type Safety

**Problem:** Fastify error handler receives `unknown` error type. Duck-typing `error.statusCode` doesn't work.

**Fix:** Use `instanceof AppError` check:

```typescript
import { AppError } from './lib/errors.js';

app.setErrorHandler((error: Error, _request, reply) => {
  if (error instanceof AppError) {
    return reply.status(error.statusCode).send({
      error: { code: error.code, message: error.message },
    });
  }
  const statusCode = 'statusCode' in error ? (error as { statusCode: number }).statusCode : 500;
  return reply.status(statusCode).send({ error: { message: error.message } });
});
```

### 5.6 Shared File Conflicts

**Problem:** Multiple epics modify the same files (types.ts, app.ts, api.ts, SettingsPage.tsx). If subagents run in parallel, they'll conflict.

**Fix:** Always run epics **sequentially**. Read shared files **fresh** before each epic. The gate pattern enforces this.

### 5.7 Settings Service Async

**Problem:** `getSettings()` became async when the settings service was upgraded to DB+encryption. All callers must `await` it.

**Fix:** When upgrading from env-only to DB, update ALL callers and ALL test mocks to return Promises.

### 5.8 Regex vs Rendered Text

**Problem:** React Testing Library renders components differently than raw HTML. Text split across elements (e.g., `<span>0</span> site(s)`) doesn't match a regex expecting `0 site(s)`.

**Fix:** Use partial text matchers or adjust regex to skip the dynamic prefix.
