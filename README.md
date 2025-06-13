# SBM Tool V2 - Development Branch

**Complete development environment** for the Site Builder Migration Tool V2.

## 🎯 Branch Structure

- **`main` branch**: Clean, user-focused repository for end users
- **`dev` branch**: Complete development environment (you are here)

## 🚀 Quick Development Setup

```bash
# Clone and switch to dev branch
git clone git@github.com:nate-hart-di/auto-sbm.git
cd auto-sbm
git checkout dev

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e .[dev]

# Run tests
pytest

# Run full validation suite
pytest tests/pr_validation_data/
```

## 📋 What's Here (Dev Branch)

- 🧪 **Complete test suites** - All test scenarios and validation
- 📊 **Test validation data** - Real PR validation cases (10+ dealer scenarios)
- 📚 **Development documentation** - Architecture, analysis, guides
- 🔧 **Development tools** - Scripts, workflows, templates
- 📈 **Analysis reports** - Compliance, standards, metrics

## 🧪 Testing

### Test Structure

```
tests/
├── pr_validation_data/     # Real PR test cases
│   ├── case_11699_*/      # Spitzer Motors validation
│   ├── case_12755_*/      # Maserati examples
│   └── ...                # 10+ real dealer scenarios
├── test_*.py              # Unit and integration tests
└── conftest.py            # Test configuration
```

### Running Tests

```bash
# All tests
pytest

# Specific test categories
pytest tests/test_workflow.py
pytest tests/pr_validation_data/

# With coverage
pytest --cov=sbm --cov-report=html
```

## 📚 Documentation Structure

```
docs/
├── development/           # Development guides and changelog
├── analysis/             # Technical analysis and compliance
├── guides/               # Migration rules and K8 guides
├── quickstart/           # New user and AI assistant onboarding
├── templates/            # PR templates and boilerplates
└── test-logs/           # Test execution logs
```

## 🔧 Development Workflow

1. **Work in dev branch**: Make all changes here
2. **Run tests**: Validate changes with full test suite
3. **Update docs**: Document changes in relevant docs
4. **Merge to main**: When ready for release, merge clean changes to main
5. **Main branch**: Stays clean and user-focused

## 📊 Validation Coverage

- ✅ **10+ Real PR Test Cases** - Validated against actual migrations
- ✅ **50+ Dealer Patterns** - Comprehensive pattern coverage
- ✅ **100% Core Functionality** - All features tested
- ✅ **Production Metrics** - Performance and reliability testing

## 🎯 Quick Commands

```bash
# Switch to user branch
git checkout main

# Switch to dev branch
git checkout dev

# Sync latest changes
git pull origin dev

# Run full validation
pytest tests/pr_validation_data/ -v
```

---

**User branch**: `git checkout main` for clean, user-focused repository
