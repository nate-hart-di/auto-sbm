# SBM Tool V2 - Quick Reference Card

## 🚀 Installation (One Command)

```bash
pip install sbm-v2
```

## 🎯 FULLY AUTOMATED WORKFLOW (Recommended)

```bash
# Complete migration - just provide the dealer slug!
sbm [slug]
# OR explicitly use auto command
sbm auto [slug]

# That's it! The tool automatically handles:
# ✅ System diagnostics
# ✅ Git workflow (checkout main, pull, create branch)
# ✅ Docker container startup (just start)
# ✅ SCSS migration and conversion
# ✅ Validation and error checking
# ✅ GitHub PR creation
# ✅ Salesforce message generation
# ✅ Complete summary report
```

## 🔧 Automated Workflow Options

| Command                              | What it does                      |
| ------------------------------------ | --------------------------------- |
| `sbm dealer-slug`                    | **Complete automated migration**  |
| `sbm auto dealer-slug --force`       | Force past validation warnings    |
| `sbm auto dealer-slug --dry-run`     | Preview what would be done        |
| `sbm auto dealer-slug --skip-docker` | Skip Docker monitoring (advanced) |

## 🛠 Individual Commands (Advanced Users)

| Command                    | What it does                   |
| -------------------------- | ------------------------------ |
| `sbm doctor`               | Check if everything is working |
| `sbm setup dealer-slug`    | Git setup only                 |
| `sbm migrate dealer-slug`  | Migration only                 |
| `sbm validate dealer-slug` | Validation only                |
| `sbm pr`                   | Create GitHub PR only          |

## 🚨 If Something Goes Wrong

1. **Always try this first:** `sbm doctor`
2. **Command not found?**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```
3. **GitHub issues?** `gh auth login`
4. **Docker timeout?** Use `--skip-docker` flag
5. **Everything broken?** Reinstall:
   ```bash
   pip install sbm-v2 --force-reinstall
   ```

## 📋 Automated Migration Checklist

The tool automatically handles all these steps:

- [x] **Diagnostics**: Verify environment and dependencies
- [x] **Directory Switch**: Navigate to di-websites-platform
- [x] **Git Setup**: Checkout main, pull, create migration branch
- [x] **Docker Startup**: Run and monitor `just start [slug]`
- [x] **Migration**: Convert SCSS files to Site Builder format
- [x] **Validation**: Ensure migration meets standards
- [x] **PR Creation**: Generate GitHub PR with proper content
- [x] **Salesforce**: Copy message to clipboard
- [x] **Summary**: Display complete workflow results

## 🔍 What Files Are Created

- `sb-vdp.scss` - Vehicle Detail Page styles
- `sb-vrp.scss` - Vehicle Results Page styles
- `sb-inside.scss` - Interior page styles
- `style.scss` - Updated to import new files

## ⚡ Error Handling

The automated workflow includes smart error handling:

- **Docker Fails**: Prompts to retry `just start`
- **Validation Warnings**: Option to continue with `--force`
- **Git Issues**: Clear error messages and suggestions
- **Missing Dependencies**: Automatic detection and guidance

## 💡 Pro Tips

- **Start with dry run**: `sbm auto dealer-slug --dry-run` to preview
- **Use force for warnings**: `sbm auto dealer-slug --force` to skip validation
- **Check environment first**: `sbm doctor` when things don't work
- **Skip Docker if needed**: `--skip-docker` for manual Docker control

## 📊 Success Metrics

After migration, you'll see:

- ✅ Steps completed vs failed
- 📁 Number of files created
- ⏱️ Total workflow duration
- 🔗 GitHub PR URL
- 📋 Complete summary report

## 📞 Need Help?

- Run `sbm doctor` for diagnostics
- Use `sbm --help` for command reference
- Check [full documentation](docs/) for detailed guides

---

**Ready to migrate?** Just run `sbm [your-dealer-slug]` and let the automation handle everything! 🚀
