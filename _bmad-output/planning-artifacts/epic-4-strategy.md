# Epic 4: Map Migration Investigation - Strategic Plan

**Date:** 2026-01-28
**Status:** Foundation Phase
**Decision Authority:** Nate + BMad Master (Claude)

## CRITICAL DISCOVERY: Story 4.1 Scope Failure

### Code Review Findings

- 6 HIGH severity issues found in Story 4.1
- Root cause: Analyzed Lexus-specific logic without understanding default
  system
- Impact: Stories 4.2-4.5 built on incomplete foundation

### Strategic Decision: Create Story 4.0 (Foundation Audit)

**Approved by:** Nate
**Rationale:** Must understand default map migration + autogroup1 structure
before fixing Lexus
**Scope:**
- Document CommonTheme dealer group structure (especially autogroup1)
- Analyze failed PRs (21434, 21462, 21393, 21391) to understand actual failures
- Document baseline default behavior before Lexus-specific analysis

## MULTI-AGENT COORDINATION PLAN

### Agent Roles & Responsibilities

1. **Gemini Flash** - Generate project-context.md (reference doc)
2. **Claude/BMad Master** - Strategic analysis, Story 4.0 execution, root
   cause investigation
3. **[Other agents TBD]** - Specific tasks as assigned

### Resource Allocation Strategy

- **Rationale:** Limited Claude tokens remaining
- **Decision:** Gemini handles documentation generation, Claude handles
  critical thinking

## KNOWLEDGE GAPS IDENTIFIED

- Autogroup1 structure and shared function files
- Template inheritance behavior post-Site Builder migration
- Complete inventory of map component naming conventions
- Actual root cause of Lexus migration failures
- External function file locations and scanning

## EXECUTION TIMELINE

1. Gemini: Generate project-context.md
2. Claude: Review and validate
3. Claude: Lightweight map subsystem scan
4. Claude: Create Story 4.0
5. [Agent TBD]: Execute Story 4.0
6. Proceed to Epic 4 stories

## CONTEXT ARTIFACTS TO CREATE

- [x] project-context.md (Gemini Flash)
- [ ] Map Migration Context Brief (Claude)
- [ ] Story 4.0: Foundation Audit (Claude)
- [x] This strategy document (Claude - NOW)

## CRITICAL RULES FOR ALL AGENTS

1. Read this document FIRST before working on Epic 4
2. Read project-context.md before writing code
3. Document all decisions in sprint artifacts
4. Cross-reference code review findings before claiming completion

---

## 1. Critical Discovery

- Story 4.1 code review found 6 HIGH, 3 MEDIUM, 2 LOW severity issues
- Root cause: Analysis performed without understanding default/baseline system
- Impact on Epic 4 stories 4.2-4.5

## 2. Code Review Findings Summary

List all 11 issues found:

1. Incomplete function documentation (dedupe_map_imports missing)
2. Test coverage unknown (tests exist but not analyzed)
3. Incorrect line number references
4. Missing SCSS processor analysis (marked optional but critical)
5. Incomplete OEM handler comparison (DefaultHandler never read)
6. Dead code claims not verified codebase-wide
7. Flowchart incompleteness (missing edge cases)
8. Missing regex pattern examples
9. File list mismatch with requirements
10. Inconsistent terminology
11. Missing architecture compliance validation

## 3. Strategic Decision - Investigation Foundation

**Approved Decision:** Create "Story 4.0: Map Migration Foundation Audit"
before addressing Story 4.1 issues

**Rationale:**

- Must understand CommonTheme dealer group structure (especially autogroup1)
- Must analyze failed PRs (21434, 21462, 21393, 21391) to understand actual
  failures
- Must document baseline default behavior before Lexus-specific analysis
- Current Epic 4 stories built on insufficient foundation

## 4. Knowledge Gaps Identified

Document the critical unknowns:

- Autogroup1 structure and shared function files
- Template inheritance behavior post-Site Builder migration
- Complete inventory of map component naming conventions
- Actual root cause of Lexus migration failures
- External function file locations and scanning

## 5. PRD Alignment Analysis

**Finding:** Epic 4 stories don't fully align with PRD requirements

| PRD Requirement                | Current Story    | Status                     |
| ------------------------------ | ---------------- | -------------------------- |
| FR10: Analyze maps.py/lexus.py | Story 4.1        | ✅ Done (with limitations) |
| FR11: Analyze specific PRs     | Story 4.3        | ✅ Planned                 |
| FR12: Historical analysis      | Story 4.4        | ✅ Planned                 |
| FR13: Gap analysis             | Story 4.5        | ✅ Planned                 |
| FR14: Root cause               | Story 4.5        | ✅ Planned                 |
| FR15: Solution strategy        | Epic 5 Story 5.1 | ✅ Planned                 |
| FR16: Determination report     | Epic 5 Story 5.2 | ✅ Planned                 |

**Issue:** Story 4.2 (SCSS processing) not in PRD - needs justification or
removal

## 6. Multi-Agent Coordination Plan

**Agent Roles:**

- Gemini Flash: Documentation generation, reference artifact creation
- Claude/BMad Master: Strategic analysis, root cause investigation, Story 4.0
  execution
- [TBD]: Story 4.2-4.5 execution after foundation complete

**Resource Allocation:**

- Claude tokens limited - reserved for critical thinking
- Gemini for pattern extraction and summarization
- All agents MUST read this strategy doc before Epic 4 work

## 7. Execution Timeline

1. ✅ Gemini: Generate project-context.md
2. ✅ Claude: Create epic-4-strategy.md (this doc)
3. ⏳ Claude: Create epic-4-context-index.md
4. ⏳ Claude: Lightweight CommonTheme/autogroup1 scan
5. ⏳ Claude: Review failed PRs
6. ⏳ Claude: Create Story 4.0
7. ⏳ Execute Story 4.0
8. ⏳ Revisit Story 4.1 findings
9. ⏳ Execute Stories 4.2-4.5

## 8. Context Artifacts Status

- [x] Planning artifacts cleaned up (Gemini - 2026-01-28)
- [x] project-context.md (Gemini Flash - Complete)
- [x] epic-4-strategy.md (Claude - This document)
- [ ] epic-4-context-index.md (Claude - Next)
- [ ] CommonTheme structure scan (Claude - Pending)
- [ ] Failed PR analysis (Claude - Pending)

## 9. Critical Rules for All Agents

1. **READ THIS DOCUMENT FIRST** before any Epic 4 work
2. Read project-context.md before writing code
3. Document all decisions in sprint artifacts
4. Cross-reference code review findings
5. Never assume - verify against actual source code
6. Test claims don't become fact until verified

---

**Decision Authority:** Nate + BMad Master (Claude)
**Status:** Active Strategic Plan
**Last Updated:** Wednesday, January 28, 2026
