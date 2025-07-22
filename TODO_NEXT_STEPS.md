# 🎯 Auto-SBM Next Steps - Prioritized Action Plan

## 🚨 **HIGH PRIORITY (Critical for Production)**

### 1. **Fix Critical Test Failures** (Est: 2-3 hours)
- **18 failing tests** - mostly UI-related Rich object testing
- **Impact**: Prevents reliable CI/CD and deployment confidence
- **Actions**:
  - Fix Rich Panel/Progress object testing approach (use console capture instead of str())
  - Fix MockStat object issues in file tests
  - Update test assertions to work with Rich UI objects properly

### 2. **Remove Print Statements** (Est: 1 hour) 
- **121 `T201` errors** - print statements should use logger
- **Impact**: Poor logging practices, debugging statements in production
- **Actions**:
  - Replace `print()` with `logger.info()`, `logger.debug()`, etc.
  - Focus on CLI and setup files first
  - Keep prints only in tests and scripts where appropriate

### 3. **Fix Line Length Issues** (Est: 30 minutes)
- **104 `E501` errors** - lines too long (>100 chars)  
- **Impact**: Code readability and style consistency
- **Actions**:
  - Run `ruff check . --fix` for auto-fixable line breaks
  - Manually fix complex expressions and long strings

## 📋 **MEDIUM PRIORITY (Code Quality & Maintainability)**

### 4. **Add Missing Type Annotations** (Est: 3-4 hours)
- **305 `ANN001` + 76 `ANN201` + 88 `ANN202`** = 469 type annotation issues
- **Impact**: Type safety, IDE support, documentation
- **Actions**:
  - Start with public functions (`ANN201` - 76 issues)
  - Add function parameter types (`ANN001` - 305 issues) 
  - Add private function returns (`ANN202` - 88 issues)
  - Use mypy to verify correctness

### 5. **Remove Unused Code** (Est: 1-2 hours)
- **152 `ARG001` + 25 `F841`** = 177 unused code issues
- **Impact**: Code bloat, confusion, potential bugs
- **Actions**:
  - Remove unused variables (`F841` - 25 issues)
  - Remove unused function arguments (`ARG001` - 152 issues)
  - Consider if functionality should be implemented or removed

### 6. **Use Modern Path Operations** (Est: 2 hours)
- **75 `PTH118` + 49 `PTH110` + 48 `PTH123`** = 172 pathlib issues
- **Impact**: Modern Python practices, better cross-platform support
- **Actions**:
  - Replace `os.path.join()` with `Path` / operator
  - Replace `os.path.exists()` with `Path.exists()`
  - Replace `open()` with `Path.read_text()` / `Path.write_text()`

## ⚡ **QUICK WINS (Low Effort, High Impact)**

### 7. **Fix Whitespace Issues** (Est: 5 minutes)
- **61 `W293`** - blank lines with whitespace
- **Impact**: Clean git diffs, professional appearance
- **Actions**: Run `ruff check . --fix` (auto-fixable)

### 8. **Fix Import Organization** (Est: 15 minutes)
- **71 `PLC0415` + 35 `TID252`** = 106 import issues
- **Impact**: Code organization and readability
- **Actions**:
  - Move imports to top of file
  - Fix relative import patterns
  - Consider using absolute imports

### 9. **Fix Try/Except Patterns** (Est: 30 minutes)
- **32 `TRY300` + 13 `TRY003`** = 45 exception handling issues
- **Impact**: Better error handling patterns
- **Actions**:
  - Add `else` clauses to try blocks where appropriate
  - Use specific exception messages instead of vanilla args

## 🔧 **LOW PRIORITY (Polish & Optimization)**

### 10. **Fix Logging Patterns** (Est: 30 minutes)
- **33 `G004`** - f-string in logging
- **Impact**: Logging performance (lazy evaluation)
- **Actions**: Replace f-strings with % formatting in logger calls

### 11. **Update Type Annotations Style** (Est: 30 minutes)
- **9 `UP006` + 8 `UP045`** = 17 modern typing issues
- **Impact**: Modern Python typing practices
- **Actions**: Use `dict` instead of `Dict`, `list` instead of `List`, etc.

### 12. **Security & Code Smell Fixes** (Est: 1 hour)
- **4 `S602` + 2 `S105`** = 6 security issues
- **Impact**: Security best practices
- **Actions**: Review subprocess calls and hardcoded passwords

## 📊 **SUCCESS METRICS**

### Target Goals:
- **Tests**: 130 passing, 0 failing (currently 112/18)
- **Ruff errors**: <500 (currently 1517) - 67% reduction goal
- **Test coverage**: >50% (currently 27%)
- **Type coverage**: >80% (mypy --report)

### Phase 1 Goals (Next 8 hours):
- ✅ Fix all critical test failures
- ✅ Reduce ruff errors to <1000 (34% reduction)
- ✅ Add type annotations to all public functions
- ✅ Remove all print statements

### Phase 2 Goals (Next 16 hours):
- ✅ Achieve <500 ruff errors (67% reduction total)
- ✅ 95%+ test pass rate
- ✅ 50%+ test coverage
- ✅ Full type annotation coverage

## 🛠️ **Implementation Strategy**

### Immediate Actions (Next 2 hours):
```bash
# 1. Auto-fix what we can
ruff check . --fix

# 2. Focus on high-impact areas first
ruff check sbm/cli.py sbm/config.py sbm/core/ --statistics

# 3. Run tests frequently to ensure no regressions
python -m pytest tests/ -x --tb=short

# 4. Track progress
ruff check . --statistics > progress_$(date +%Y%m%d_%H%M).log
```

### Testing Strategy:
- Run tests after each major fix batch
- Focus on keeping existing passing tests working
- Fix test infrastructure before fixing code quality issues

### Quality Gates:
- No regressions in passing tests
- Gradual improvement in ruff error count
- Maintain or improve test coverage
- All changes must pass CI pipeline

---

**PRIORITY ORDER**: Tests → Print statements → Line length → Type annotations → Unused code → Path operations → Quick wins → Polish