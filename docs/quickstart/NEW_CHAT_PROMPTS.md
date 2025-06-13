# SBM Tool V2 - New Chat Starting Prompts

## 🚀 Quick Context Prompt (Copy & Paste)

```
I'm working on the SBM Tool V2 project - a Site Builder Migration tool for DealerInspire dealer websites.

Key context:
- Project location: /Users/nathanhart/Desktop/projects/automation/sbm-v2
- Purpose: Converts legacy SCSS themes to Site Builder format
- Tech stack: Python/Click CLI, regex-based SCSS processing, GitHub CLI integration
- Key files: sbm/scss/processor.py (SCSS conversion), sbm/cli.py (CLI interface), sbm/core/git_operations.py (PR creation)

Please read the AI Assistant Quickstart Guide at docs/quickstart/AI_ASSISTANT_QUICKSTART.md to understand the project architecture and current state.

Current focus: [DESCRIBE WHAT YOU'RE WORKING ON]
```

## 🔧 Development-Focused Prompt

```
I'm working on SBM Tool V2 - a DealerInspire Site Builder migration tool. This is a mature Python CLI tool that automates SCSS theme conversions.

Project context:
- Location: /Users/nathanhart/Desktop/projects/automation/sbm-v2
- Main package: sbm/ with CLI, SCSS processor, validation, and git operations
- Key transformations: mixin replacement, color variables, breakpoint standardization
- Integration: GitHub CLI for PR creation with Stellantis templates

Please review docs/quickstart/AI_ASSISTANT_QUICKSTART.md for full architecture details.

I need help with: [SPECIFIC DEVELOPMENT TASK]
```

## 🐛 Debugging-Focused Prompt

```
I'm troubleshooting the SBM Tool V2 - a Site Builder migration tool for DealerInspire themes.

Quick context:
- Python CLI tool at /Users/nathanhart/Desktop/projects/automation/sbm-v2
- Main command: `sbm migrate` with flags --force, --create-pr, --dry-run
- Debugging: Always start with `sbm doctor` for environment diagnostics
- Config: Auto-detects ~/di-websites-platform, reads ~/.cursor/mcp.json

Current issue: [DESCRIBE THE PROBLEM]

Please check docs/quickstart/AI_ASSISTANT_QUICKSTART.md for debugging methodology and common issues.
```

## 🎨 SCSS/Styling-Focused Prompt

```
I'm working on SBM Tool V2's SCSS conversion engine for DealerInspire Site Builder migrations.

Key SCSS transformations:
- Mixins: @include flexbox() → display: flex
- Colors: #093382 → var(--primary, #093382)
- Breakpoints: 768px (tablet), 1024px (desktop) - NOT 920px
- Files: lvdp.scss → sb-vdp.scss, lvrp.scss → sb-vrp.scss

Main processor: sbm/scss/processor.py
Standards: docs/analysis/K8_COMPLIANCE_SUMMARY.md

Working on: [SCSS-SPECIFIC TASK]
```

## 📋 PR/Git-Focused Prompt

```
I'm working on SBM Tool V2's GitHub integration for automated PR creation during Site Builder migrations.

PR context:
- Creates Stellantis-specific PRs with dynamic content
- Default reviewers: carsdotcom/fe-dev, label: fe-dev
- Published PRs (not draft), auto-opens in browser
- Template: docs/templates/@sbm-pr-template-stellantis.md

Main file: sbm/core/git_operations.py
GitHub CLI integration, reads token from ~/.cursor/mcp.json

Working on: [PR/GIT-SPECIFIC TASK]
```

## 🧪 Testing-Focused Prompt

```
I'm working on testing for SBM Tool V2 - the DealerInspire Site Builder migration tool.

Testing context:
- Real-world tests with actual dealer themes
- Test location: tests/ and test_real_world.py
- Focus: Core functionality validation, not comprehensive test suites
- Approach: Lightweight testing to verify things work

Current testing need: [TESTING TASK]

Please reference docs/quickstart/AI_ASSISTANT_QUICKSTART.md for testing patterns.
```

## 📚 Documentation-Focused Prompt

```
I'm working on documentation for SBM Tool V2 - a Site Builder migration tool for DealerInspire.

Documentation structure:
- docs/quickstart/ - User and AI assistant guides
- docs/development/ - Development changelog and guides
- docs/analysis/ - K8 compliance and standards
- docs/templates/ - PR templates

Current documentation task: [DOC TASK]

Please review existing docs structure and maintain consistency with established patterns.
```

---

## 💡 Usage Tips

1. **Copy the relevant prompt** based on your focus area
2. **Fill in the bracketed sections** with your specific task
3. **Paste at the start of a new chat** to give context immediately
4. **Reference the AI Assistant Quickstart** for deeper understanding

## 🔄 Prompt Customization

Feel free to modify these prompts based on:

- **Specific features** you're working on
- **Current project phase** (development, testing, deployment)
- **Particular challenges** you're facing
- **Integration needs** with other tools

The key is giving the AI assistant enough context to understand the project architecture and current state without overwhelming the initial message.
