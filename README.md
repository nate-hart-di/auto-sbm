# SBM Tool V2 - Site Builder Migration

**One-command automation** for converting DealerInspire dealer themes to Site Builder format.

## 🚀 Quick Install

```bash
pip install sbm-v2
```

## 🎯 Quick Start

```bash
# 1. Setup dealer migration
sbm setup your-dealer-slug --auto-start

# 2. Run migration
sbm migrate your-dealer-slug

# 3. Create pull request
sbm create-pr
```

## 📋 What It Does

- ✅ **Converts SCSS files** to Site Builder format
- ✅ **Updates mixins** to modern CSS
- ✅ **Handles Git workflow** automatically
- ✅ **Creates GitHub PR** with proper templates

## 🔧 Requirements

- Python 3.8+
- Access to `~/di-websites-platform` directory
- GitHub CLI (`gh`) authenticated

## 📚 Commands

| Command                         | Purpose                      |
| ------------------------------- | ---------------------------- |
| `sbm doctor`                    | Check system health          |
| `sbm setup <slug> --auto-start` | Prepare dealer for migration |
| `sbm migrate <slug>`            | Run the migration            |
| `sbm create-pr`                 | Create GitHub pull request   |

## 🚨 Getting Help

1. **Always try first:** `sbm doctor`
2. **Issues?** Check [troubleshooting guide](TROUBLESHOOTING.md)
3. **Bugs?** Report at [GitHub Issues](https://github.com/nate-hart-di/auto-sbm/issues)

---

**Need more details?** See [Complete Documentation](DOCS.md)
