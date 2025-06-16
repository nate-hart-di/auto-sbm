# SBM Tool V2 - Troubleshooting Guide

## 🔧 Quick Fixes

### Step 1: Always Run This First

```bash
sbm doctor
```

This tells you exactly what's wrong.

### Step 2: Most Common Issues

**❌ "command not found: sbm"**

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**❌ "GitHub PR creation fails"**

```bash
gh auth login
```

**❌ "Python 3.8+ required"**

```bash
brew install python3
```

**❌ "Migration fails"**

```bash
# Check if dealer exists
ls ~/di-websites-platform/dealer-themes/your-slug

# Force migration if needed
sbm migrate your-slug --force
```

**❌ "Docker not ready"**

```bash
# Just wait 1-2 minutes for Docker to start
# Look for "Server is ready" message
```

## 🆘 Emergency Reset

If nothing works:

```bash
pip uninstall sbm-v2 -y
pip install sbm-v2
sbm doctor
```

## 📞 Still Need Help?

1. Run `sbm doctor` and share the output
2. Report at [GitHub Issues](https://github.com/nate-hart-di/auto-sbm/issues)
3. Include your operating system and Python version
