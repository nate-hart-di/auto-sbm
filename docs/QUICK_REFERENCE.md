# SBM Tool V2 - Quick Reference Card

## 🚀 Installation (One Command)

```bash
pip install sbm-v2
```

## 🎯 Basic Usage

```bash
# 1. Setup dealer (replace 'dealer-slug' with actual dealer name)
sbm setup dealer-slug --auto-start

# 2. Run migration
sbm migrate dealer-slug

# 3. Create PR
sbm create-pr
```

## 🔧 Common Commands

| Command                              | What it does                         |
| ------------------------------------ | ------------------------------------ |
| `sbm doctor`                         | Check if everything is working       |
| `sbm setup dealer-slug --auto-start` | Prepare dealer for migration         |
| `sbm migrate dealer-slug`            | Convert dealer theme to Site Builder |
| `sbm create-pr`                      | Create GitHub pull request           |
| `sbm migrate dealer-slug --dry-run`  | Preview changes without making them  |

## 🚨 If Something Goes Wrong

1. **Always try this first:** `sbm doctor`
2. **Command not found?**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```
3. **GitHub issues?** `gh auth login`
4. **Everything broken?** Reinstall:
   ```bash
   pip install sbm-v2 --force-reinstall
   ```

## 📋 Migration Checklist

- [ ] Find dealer slug: `ls ~/di-websites-platform/dealer-themes/`
- [ ] Run setup: `sbm setup dealer-slug --auto-start`
- [ ] Wait for Docker (1-2 minutes)
- [ ] Run migration: `sbm migrate dealer-slug`
- [ ] Create PR: `sbm create-pr`
- [ ] Check PR was created in browser

## 🔍 What Files Are Created

- `sb-vdp.scss` - Vehicle Detail Page styles
- `sb-vrp.scss` - Vehicle Results Page styles
- `sb-inside.scss` - Interior page styles
- `style.scss` - Updated to import new files

## 💡 Pro Tips

- Use `--dry-run` to preview changes first
- Use `--force` to skip validation if needed
- Always run `sbm doctor` when things don't work
- The setup script installs everything automatically

## 📞 Need Help?

- Run `sbm doctor` for diagnostics
- Check GitHub Issues: https://github.com/nate-hart-di/auto-sbm/issues
- Full documentation: https://github.com/nate-hart-di/auto-sbm
