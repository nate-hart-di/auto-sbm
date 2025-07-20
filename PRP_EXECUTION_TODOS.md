# Code Quality Critical Fixes - Execution TODO List

## Assessment of Current State
Based on ruff check: 1326 violations (down from 1646+)
Key remaining issues:
- 347 missing type function arguments (ANN001)  
- 94 missing return type private functions (ANN202)
- 89 missing return type public functions (ANN201)
- 12 print statements in CLI (T201)
- MyPy error in config.py: Missing github_token for GitSettings

## Remaining Tasks to Complete

### ✅ COMPLETED 
- [x] Partial progress tracking fixes in sbm/ui/progress.py
- [x] Configuration migration to Pydantic v2 in sbm/config.py
- [x] Fixed GitSettings missing github_token requirement - made optional
- [x] Added comprehensive type hints to CLI functions (auto, cli, migrate, reprocess, validate)
- [x] Fixed CustomCliGroup class with proper type annotations
- [x] Replaced ALL 7 print statements with secure logging (T201: 12 → 0)
- [x] Fixed duplicate exception handlers in CLI  
- [x] Created test files (test_progress_fixes.py, test_config_migration.py, test_type_safety_compliance.py)
- [x] Added proper typing imports to CLI
- [x] Configuration passes mypy validation
- [x] Security validation: No dangerous print statements in error paths

### 🔧 REMAINING WORK

#### Task 1: Complete Type Hint Coverage (Primary Remaining Issue)
- [ ] Add remaining 340 function argument type hints (ANN001) - down from 347
- [ ] Add 93 missing return type annotations for private functions (ANN202) - down from 94
- [ ] Add 84 missing return type annotations for public functions (ANN201) - down from 89
- [ ] Focus on core/migration.py, scss/processor.py, utils/ files

#### Task 2: Fix Progress Tracking Test Issues  
- [ ] Fix test failures in test_progress_fixes.py (step_tasks cleanup issue)
- [ ] Verify progress bars show 0% → 100% correctly in integration test
- [ ] Fix Rich Progress API usage edge cases

#### Task 3: Comprehensive Validation
- [ ] Run Level 1 validation: mypy --strict on full codebase
- [ ] Run Level 2 validation: fix and run unit tests with 80%+ coverage  
- [ ] Run Level 3 validation: integration test
- [ ] Run Level 4 validation: final security checks

## Current Priority Order
1. Fix config.py GitSettings issue (blocking mypy)
2. Complete type hints for high-impact files (cli.py, core/migration.py)
3. Replace remaining print statements with logging
4. Fix and validate all tests
5. Run comprehensive validation suite

## Success Criteria Checklist
- [ ] Zero mypy violations: `mypy sbm/ --strict` 
- [ ] Progress bars display 0% → 100%: integration test
- [ ] No hanging processes: thread cleanup tests pass
- [ ] No print statements in error paths: `rg "print\(" sbm/cli.py` returns 0
- [ ] All tests pass with 80%+ coverage
- [ ] Integration test completes successfully