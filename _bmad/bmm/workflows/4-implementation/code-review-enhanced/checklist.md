# Enhanced Code Review - Validation Checklist

## Gate 1: Discovery
- [ ] Story file loaded from `{{story_path}}`
- [ ] Story Status verified as reviewable
- [ ] Epic and Story IDs resolved ({{epic_num}}.{{story_num}})
- [ ] Git status/diff executed and cross-referenced with story File List
- [ ] Architecture/standards docs loaded (as available)
- [ ] Project context loaded for coding standards

## Gate 2: Attack Plan
- [ ] All Acceptance Criteria extracted
- [ ] All Tasks/Subtasks with completion status extracted
- [ ] Review plan created (AC validation, task audit, code quality, test quality)

## Gate 3: Adversarial Review
- [ ] Git vs story File List discrepancies documented
- [ ] Each AC validated: IMPLEMENTED, PARTIAL, or MISSING
- [ ] Each [x] task verified with file:line proof
- [ ] Full function/module context read before flagging issues (not just flagged line)
- [ ] Cross-file pattern check performed for each finding
- [ ] Code quality deep dive completed on all changed files
- [ ] Honest assessment — no padded findings, no fabricated issues

## Gate 4: Auto-Fix
- [ ] Bail-out threshold checked (>15 total or >5 CRITICAL+HIGH)
- [ ] Issues processed in severity order: CRITICAL -> HIGH -> MEDIUM -> LOW
- [ ] Each fix verified: issue absent, no new errors, no unintended changes
- [ ] Cascade check after each CRITICAL/HIGH fix
- [ ] Scope constraint enforced — no unrelated refactors
- [ ] All findings documented in-story under "Senior Developer Review (AI)"
- [ ] Story File List and Change Log updated

## Gate 5: Verification and Status
- [ ] Post-fix regression sweep on ALL modified files
- [ ] Test suite executed (tsc + test runner)
- [ ] Test failures addressed (or escalated after 2 attempts)
- [ ] Story status updated (done/in-progress)
- [ ] Sprint status synced (if tracking enabled)
- [ ] Story saved successfully

_Reviewer: {{user_name}} on {{date}}_
