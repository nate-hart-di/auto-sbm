# Repository Separation Plan

## 🎯 Problem

Current repo mixes user-facing tool with development artifacts, making it confusing and bloated for end users.

## 📁 Current Repository Analysis

**Size Breakdown:**

- `/tests/` - 540KB (development testing)
- `/docs/` - 148KB (development documentation)
- Core tool - ~50KB
- **Total development cruft: ~700KB**

## 🔄 Proposed Solution

### User-Facing Repository: `nate-hart-di/auto-sbm`

**What users actually need:**

```
auto-sbm/
├── sbm/                    # Core package
├── README.md              # Simple getting started
├── DOCS.md                # Complete documentation
├── TROUBLESHOOTING.md     # Common issues
├── QUICK_REFERENCE.md     # Quick commands
├── requirements.txt       # Dependencies
├── pyproject.toml         # Package config
└── LICENSE
```

### Development Repository: `nate-hart-di/auto-sbm-dev`

**What developers need:**

```
auto-sbm-dev/
├── sbm/                   # Core package (same as user repo)
├── tests/                 # All test suites
├── docs/                  # Development documentation
├── .github/               # GitHub workflows
├── scripts/               # Development scripts
├── validation/            # Test data and validation
└── development tools
```

## 🚀 Implementation Strategy

### Phase 1: Clean Current Repo for Users

1. ✅ Remove `setup.sh` (pip is simpler)
2. ❌ Remove `/tests/` directory
3. ❌ Remove `/docs/development/`
4. ❌ Remove test validation data
5. ✅ Simplify README (already done)
6. ✅ Create focused documentation (already done)

### Phase 2: Publish to PyPI

```bash
# Users can then just:
pip install sbm-v2
```

### Phase 3: Create Development Repository

1. Create `auto-sbm-dev` repository
2. Copy all development artifacts
3. Add development-specific documentation
4. Setup CI/CD for both repos

## 📊 Benefits

**For Users:**

- ✅ Simple `pip install`
- ✅ Clean, focused documentation
- ✅ No development noise
- ✅ Faster clone/download

**For Developers:**

- ✅ Full test suites
- ✅ Development documentation
- ✅ Validation data
- ✅ CI/CD workflows

## 🎯 Next Steps

1. **Immediate**: Remove development files from user repo
2. **Week 1**: Publish to PyPI
3. **Week 2**: Create separate dev repository
4. **Week 3**: Setup automated sync between repos

## 🔧 File Removal List

**Remove from user repo:**

```bash
rm -rf tests/
rm -rf docs/development/
rm -rf docs/analysis/
rm -rf docs/test-logs/
rm -rf .github/workflows/test*.yml
```

**Keep in user repo:**

```bash
sbm/               # Core package
README.md          # Simple guide
DOCS.md            # Complete docs
TROUBLESHOOTING.md # User help
QUICK_REFERENCE.md # Quick commands
requirements.txt   # Dependencies
pyproject.toml     # Package config
LICENSE            # Legal
```

This makes the user experience **10x simpler** while preserving all development capabilities.
