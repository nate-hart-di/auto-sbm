# SBM Tool V2 - Project Specific Rules

## 🎯 **PROJECT IDENTITY & CONTEXT**

**Project**: SBM Tool V2 - Site Builder Migration Tool for DealerInspire
**Purpose**: Automate conversion of legacy SCSS dealer themes to Site Builder format
**Location**: `/Users/nathanhart/Desktop/projects/automation/sbm-v2`
**Tech Stack**: Python 3.8+, Click CLI, GitHub CLI, regex-based SCSS processing

### **ALWAYS READ FIRST**

- `docs/AI_MEMORY_REFERENCE.md` - Master orientation for AI assistants
- `docs/quickstart/AI_ASSISTANT_QUICKSTART.md` - Complete project architecture
- `docs/development/CHANGELOG.md` - Recent changes and current state

---

## 🏗️ **ARCHITECTURE & DESIGN PRINCIPLES**

### **CORE ARCHITECTURE RULES**

1. **Modular Design**: Each component has single responsibility

   - `sbm/cli.py` - CLI interface only
   - `sbm/scss/processor.py` - SCSS transformations only
   - `sbm/core/validation.py` - File structure validation only
   - `sbm/core/git_operations.py` - GitHub integration only

2. **Auto-Detection Over Configuration**

   - DI Platform: Auto-detect `~/di-websites-platform`
   - GitHub Token: Read from `~/.cursor/mcp.json`
   - Context7 API: Read from `~/.cursor/mcp.json`
   - Dealer Slug: Extract from current directory name

3. **Regex-Based Processing** (NOT AST)
   - Flexibility over perfect parsing
   - Handle edge cases in legacy SCSS
   - Maintain readability of transformations

### **DESIGN PATTERNS**

- **Error Handling**: Comprehensive try/catch with user-friendly messages
- **Logging**: Structured logging with different levels for debugging
- **Type Hints**: Required for all functions and methods
- **Testing**: Pytest-based with real-world dealer theme tests

---

## 🎨 **SCSS TRANSFORMATION STANDARDS**

### **CRITICAL BREAKPOINT RULES**

- **ALWAYS USE**: 768px (tablet), 1024px (desktop)
- **NEVER USE**: 920px, 1200px, or any non-standard breakpoints
- **AUTO-CONVERT**: Legacy breakpoints to standard ones during processing

### **MIXIN REPLACEMENT PATTERNS**

```scss
// Positioning
@include absolute(10px, 20px) → position: absolute;
top: 10px;
right: 20px;
@include relative() → position: relative;
@include centering() → position: absolute;
top: 50%;
left: 50%;
transform: translate(-50%, -50%);

// Flexbox
@include flexbox() → display: flex;
@include flex-direction(column) → flex-direction: column;
@include justify-content(center) → justify-content: center;

// Typography
@include responsive-font(16px, 20px) → font-size: clamp(16px, 4vw, 20px);
@include font_size(18px) → font-size: 18px;

// Utilities
@include border-radius(5px) → border-radius: 5px;
@include box-shadow(0 2px 4px rgba(0, 0, 0, 0.1)) → box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
```

### **COLOR VARIABLE CONVERSION**

```scss
// ALWAYS convert hex colors to CSS variables
#093382 → var(--primary, #093382)
#fff → var(--white, #fff)
#000 → var(--black, #000)
rgba(9, 51, 130, 0.5) → var(--primary-50, rgba(9, 51, 130, 0.5))
```

### **FILE MAPPING RULES**

- `lvdp.scss` → `sb-vdp.scss` (Vehicle Detail Page)
- `lvrp.scss` → `sb-vrp.scss` (Vehicle Results Page)
- `inside.scss` → `sb-inside.scss` (Interior pages)
- Update `style.scss` imports to reference new files

---

## 🔧 **CLI DEVELOPMENT STANDARDS**

### **COMMAND STRUCTURE**

```bash
sbm migrate [--force/-f] [--create-pr/-g] [--dry-run/-n]
sbm doctor [--export-log/-e FILE]
sbm validate [DEALER_SLUG]
sbm create-pr
sbm install-completion
```

### **FLAG REQUIREMENTS**

- **Short Aliases**: Every flag must have short version (-f, -g, -n, -e, -h)
- **Help Text**: Rich help with context and examples
- **Tab Completion**: Support for dealer slug completion
- **Validation**: Validate inputs before processing

### **ERROR HANDLING PATTERNS**

```python
try:
    # Operation
    pass
except SpecificError as e:
    logger.error(f"Specific issue: {e}")
    click.echo(f"❌ Error: {user_friendly_message}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    click.echo("❌ Unexpected error occurred. Run 'sbm doctor' for diagnostics.")
    sys.exit(1)
```

---

## 🐛 **DEBUGGING & VALIDATION PROTOCOLS**

### **DIAGNOSTIC WORKFLOW**

1. **ALWAYS START**: `sbm doctor` command for environment validation
2. **Check File Structure**: Validate required files exist
3. **Verify Configuration**: Confirm auto-detection worked
4. **Test SCSS Processing**: Use simple inputs first
5. **Review Git State**: Ensure clean working directory

### **VALIDATION REQUIREMENTS**

- **File Structure**: Check for `style.scss`, `style.css`, `di-acf-json/`
- **Environment**: Verify DI platform path, GitHub CLI auth
- **Dependencies**: Confirm all required packages installed
- **Git State**: Ensure repository is clean before operations

### **COMMON ISSUE PATTERNS**

```python
# Permission denied → Remove old aliases, reinstall
# Command not found → Add ~/.local/bin to PATH
# GitHub auth → Run gh auth login
# Missing files → Check dealer theme structure
# SCSS errors → Review processor logic for edge cases
```

---

## 📋 **GITHUB INTEGRATION STANDARDS**

### **PR CREATION RULES**

- **Template**: Always use Stellantis-specific template
- **Status**: Create as published (NOT draft)
- **Reviewers**: Default to `carsdotcom/fe-dev`
- **Labels**: Default to `fe-dev`
- **Browser**: Auto-open PR after creation

### **PR CONTENT REQUIREMENTS**

```markdown
## What

Dynamic content based on actual migrated files:

- Detected VRP/VDP/LVRP/LVDP files
- Stellantis brand-specific features
- File transformation summary

## Why

Site Builder migration for [DEALER_NAME]

## How

- Automated SCSS conversion
- Mixin replacement
- Color variable standardization
- Breakpoint normalization
```

### **COMMIT MESSAGE PATTERNS**

```
feat: Site Builder migration for [dealer-slug]
- Convert legacy SCSS to Site Builder format
- Replace mixins with CSS equivalents
- Standardize breakpoints to 768px/1024px
- Convert hex colors to CSS variables
```

---

## 🧪 **TESTING STANDARDS**

### **TESTING PHILOSOPHY**

- **Lightweight Testing**: Verify core functionality works, not comprehensive suites
- **Real-World Focus**: Test with actual dealer themes
- **Quick Validation**: Ensure things work before using them
- **No Over-Engineering**: Avoid extensive testing infrastructure

### **TEST STRUCTURE**

```python
def test_scss_processor_basic():
    """Test basic SCSS transformations work"""
    # Test mixin replacement
    # Test color conversion
    # Test breakpoint standardization

def test_real_world_dealer_theme():
    """Test with actual dealer theme"""
    # Use existing dealer theme
    # Run migration
    # Validate output files
```

### **TEST EXECUTION**

- Run tests before major releases
- Document test results in detailed summaries
- Include logs and generated files inspection
- Verify code formatting and completeness

---

## 📚 **DOCUMENTATION MAINTENANCE**

### **REQUIRED UPDATES**

- **CHANGELOG.md**: Document all changes with version increments
- **AI_MEMORY_REFERENCE.md**: Update for major architectural changes
- **K8_COMPLIANCE_SUMMARY.md**: Update styling standards
- **PROJECT_CONTEXT.md**: Update current state and milestones

### **VERSION MANAGEMENT**

- **Minor Fixes**: Increment by 0.0.1 (e.g., 2.0.0 → 2.0.1)
- **Major Features**: Increment by 0.1.0 (e.g., 2.0.0 → 2.1.0)
- **Breaking Changes**: Increment by 1.0.0 (e.g., 2.0.0 → 3.0.0)

### **DOCUMENTATION STANDARDS**

- Use emoji headers for visual organization
- Include code examples for all transformations
- Maintain cross-references between documents
- Keep troubleshooting sections updated

---

## 🚨 **PROJECT-SPECIFIC ANTI-PATTERNS**

### **NEVER DO**

- Use 920px breakpoints (use 768px instead)
- Edit parent theme files in DealerInspire
- Create draft PRs (always published)
- Skip `sbm doctor` when debugging
- Assume configuration without auto-detection
- Use AST parsing for SCSS (use regex)
- Create comprehensive test suites (keep lightweight)

### **ALWAYS DO**

- Start debugging with `sbm doctor`
- Reference existing SCSS patterns before creating new ones
- Use CSS variables for all hex colors
- Create PRs with Stellantis template
- Auto-detect configuration from standard locations
- Maintain file tracking for PR descriptions
- Update documentation with every change

---

## 🔄 **WORKFLOW INTEGRATION**

### **DEVELOPMENT CYCLE**

1. **Branch**: Create `sbm/{dealer-slug}` branch
2. **Migrate**: Run `sbm migrate --create-pr`
3. **Review**: Check generated SCSS files
4. **Test**: Validate with `sbm doctor`
5. **PR**: Auto-created with proper template
6. **Document**: Update CHANGELOG.md

### **RELEASE CYCLE**

1. **Test**: Run real-world tests
2. **Document**: Update all relevant docs
3. **Version**: Increment version number
4. **Tag**: Create git tag for release
5. **Deploy**: Update installation instructions

---

**Remember**: This tool automates critical production workflows. Consistency, reliability, and comprehensive documentation are more important than perfect code. When in doubt, reference existing patterns and ask for clarification.
