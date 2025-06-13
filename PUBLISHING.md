# PyPI Publishing Guide

## Prerequisites

1. **Create PyPI accounts**:

   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

2. **Install publishing tools**:
   ```bash
   pip3 install build twine
   ```

## Publishing Process

### Step 1: Build the Package

```bash
# Ensure you're on the master branch
git checkout master

# Build the distribution files
python3 -m build
```

### Step 2: Check Package Quality

```bash
# Verify the package meets PyPI standards
python3 -m twine check dist/*
```

### Step 3: Test on TestPyPI

```bash
# Upload to TestPyPI first for testing
python3 -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip3 install --index-url https://test.pypi.org/simple/ sbm-v2
```

### Step 4: Publish to PyPI

```bash
# Upload to production PyPI
python3 -m twine upload dist/*
```

### Step 5: Verify Installation

```bash
# Test final installation
pip3 install sbm-v2
sbm doctor
```

## Authentication

### Option 1: API Tokens (Recommended)

1. Generate API tokens in PyPI/TestPyPI account settings
2. Create `~/.pypirc`:

```ini
[distutils]
index-servers =
  pypi
  testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-your-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-testpypi-token-here
```

### Option 2: Interactive Login

- Twine will prompt for credentials if not configured

## Version Management

1. **Update version** in `pyproject.toml`
2. **Commit changes** to master branch
3. **Create git tag**: `git tag v2.4.0 && git push origin v2.4.0`
4. **Build and publish** following steps above

## Current Status

✅ **Package built successfully**: `dist/sbm_v2-2.4.0.tar.gz` and `.whl`  
✅ **Package passes PyPI checks**: Ready for publishing  
🔲 **TestPyPI upload**: Requires authentication setup  
🔲 **PyPI publishing**: Ready once TestPyPI testing is complete

## Next Release Process

1. Develop in `dev` branch
2. Merge to `master` when ready
3. Update version number
4. Follow publishing steps above

This ensures users get: `pip install sbm-v2` → Clean, working package!
