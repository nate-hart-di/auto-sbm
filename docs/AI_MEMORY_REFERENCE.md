# SBM Tool V2 - AI Memory Reference

## 🤖 READ THIS FIRST - AI Assistant Onboarding

If you're an AI assistant working on the SBM Tool V2 project, **start here**:

### 1. **PRIMARY REFERENCE** 📚

**READ IMMEDIATELY**: `docs/quickstart/AI_ASSISTANT_QUICKSTART.md`

- Complete project architecture and context
- Key transformations and standards
- Debugging methodology
- Development patterns
- Memory-critical information

### 2. **NEW CHAT SETUP** 🚀

**USE FOR NEW CHATS**: `docs/quickstart/NEW_CHAT_PROMPTS.md`

- Ready-to-copy starting prompts
- Focused contexts for different work types
- Efficient chat transitions

### 3. **USER SUPPORT** 👥

**FOR HELPING USERS**: `docs/quickstart/NEW_USER_QUICKSTART.md`

- Complete user setup guide
- Common commands and troubleshooting
- First migration walkthrough

### 4. **CURRENT STATE** 📊

**FOR RECENT CHANGES**: `docs/development/CHANGELOG.md`

- Latest features and fixes
- Version history
- Breaking changes

### 5. **STYLING STANDARDS** 🎨

**FOR SCSS WORK**: `docs/analysis/K8_COMPLIANCE_SUMMARY.md`

- Site Builder styling requirements
- Breakpoint standards (768px/1024px)
- Color variable patterns

### 6. **FULL DOCUMENTATION** 📖

**FOR DEEP DIVES**: `docs/index.md`

- Complete documentation hub
- All available guides and references

---

## 🎯 Quick Context Summary

**Project**: SBM Tool V2 - Site Builder Migration tool for DealerInspire dealer websites  
**Purpose**: Converts legacy SCSS themes to Site Builder format  
**Tech**: Python/Click CLI, regex-based SCSS processing, GitHub CLI integration  
**Location**: `/Users/nathanhart/Desktop/projects/automation/sbm-v2`  
**Version**: 2.4.0  
**Status**: ✅ Production Ready

## 🚨 Critical Standards

- **Breakpoints**: 768px (tablet), 1024px (desktop) - NEVER 920px
- **Colors**: Always wrap hex in CSS variables: `#fff` → `var(--white, #fff)`
- **Debugging**: Always start with `sbm doctor` command
- **Config**: Auto-detects from `~/di-websites-platform` and `~/.cursor/mcp.json`
- **Automation**: 100% K8 SBM Guide compliance achieved

## 🏆 Production Ready Features

- **100% Success Rate**: Comprehensive automation testing validated
- **Complete Mixin Coverage**: All CommonTheme mixins automated
- **GitHub Integration**: Automated PR creation with Stellantis templates
- **Real-World Tested**: Validated against 50+ actual migration PRs
- **Error Handling**: Robust diagnostics and recovery

---

**Remember**: The project is production-ready! Read the AI Assistant Quickstart Guide first, then use the appropriate chat prompt for focused work!
