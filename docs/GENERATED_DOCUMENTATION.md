# SBM Tool v2 - Generated Documentation

_Generated from indexed knowledge using crawl4ai-rag system_

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Components](#architecture--components)
3. [Migration Workflow](#migration-workflow)
4. [SCSS Processing](#scss-processing)
5. [OEM Detection System](#oem-detection-system)
6. [User Review System](#user-review-system)
7. [CLI Interface](#cli-interface)
8. [Version History](#version-history)
9. [Testing & Validation](#testing--validation)
10. [Technical Implementation](#technical-implementation)

## Project Overview

**SBM Tool v2** is a Site Builder Migration Tool for DealerInspire, designed to automate the conversion of legacy SCSS dealer themes to Site Builder format. The tool provides comprehensive automation for theme migration while maintaining production-ready standards.

### Purpose

- Automate conversion of legacy SCSS dealer themes to Site Builder format
- Generate production-ready files matching exact production patterns
- Reduce manual migration effort and ensure consistency

### Tech Stack

- Python 3.8+
- Click CLI framework
- GitHub CLI integration
- Regex-based SCSS processing (NOT AST - flexibility over perfect parsing)
- Docker support for DealerInspire platform

## Architecture & Components

### Core Modules

#### 1. CLI Interface (`cli.py`)

- **Simplified Interface**: Default help shows only 3 essential commands (auto, doctor, validate)
- **Advanced Commands**: Hidden commands available with `--advanced` flag
- **Commands Available**:
  - `sbm auto` - Full automated migration workflow
  - `sbm doctor` - System diagnostics
  - `sbm validate` - Dealer slug validation
  - Advanced: setup, migrate, status, config-info, create-pr, monitor

#### 2. Configuration System (`config.py`)

- Auto-detection of `~/di-websites-platform`
- Reads `~/.cursor/mcp.json` for platform configuration
- Flexible configuration with environment support
- Path resolution for absolute/relative paths

#### 3. Core Workflow (`core/full_workflow.py`)

Enhanced 8-step migration process:

1. System Diagnostics
2. Git Setup
3. Docker Startup
4. Theme Migration (Automated)
5. **User Review Session** (NEW in v2.9.0)
6. File Saving & Gulp
7. Validation
8. Pull Request (with confirmation)

#### 4. SCSS Processing (`scss/`)

- **Regex-Based Processing**: Flexible processing over perfect parsing
- **Legacy Style Extraction**: Processes existing SCSS files
- **Standard Templates**: Production-ready file templates
- **File Structure**: Creates identical 3-file structure (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)

#### 5. OEM Detection (`oem/`)

- **Brand Identification System**: Automatic OEM detection
- **Stellantis Support**: Special handling for Stellantis dealers
- **Handler Factory Pattern**: Dynamic OEM handler creation
- **Map Components**: Standard map components with directions box for Stellantis

#### 6. User Review System (`core/user_review.py`) - NEW v2.9.0

Interactive review session with comprehensive change tracking:

- File state capture (MD5 hashes, sizes, line counts)
- User prompts with help commands (done, help, status)
- Change analysis detecting manual modifications
- Detailed reporting of size/line differences

#### 7. Git Operations (`core/git_operations.py`)

Enhanced git operations with user review tracking:

- New `create_enhanced_pr()` method with user review tracking
- Enhanced PR descriptions separating automated vs manual work
- Smart commit messaging distinguishing automation from manual changes
- Improved Salesforce messages reflecting both contributions
- Absolute path handling for directory independence

## Migration Workflow

### Step-by-Step Process

#### 1. System Diagnostics

- Verify DealerInspire platform setup
- Check Docker availability
- Validate configuration paths
- Confirm GitHub CLI access

#### 2. Git Setup

- Create feature branch with naming convention
- Set up working directory
- Initialize git tracking

#### 3. Docker Startup

- Launch DealerInspire platform containers
- Verify container health
- Establish database connections

#### 4. Theme Migration (Automated)

- Process legacy SCSS files
- Extract existing styles
- Generate Site Builder compatible files
- Apply OEM-specific templates
- Create production headers

#### 5. User Review Session (NEW)

Interactive manual review phase:

- Present generated files to user
- Allow manual editing and refinement
- Track all changes with MD5 verification
- Capture size and line count differences
- User commands: `done`, `help`, `status`

#### 6. File Saving & Gulp

- Save final files to theme directory
- Run gulp compilation
- Verify CSS generation

#### 7. Validation

- Validate generated SCSS syntax
- Check file structure compliance
- Verify production standards

#### 8. Pull Request Creation

- GitHub action confirmation prompts
- Enhanced PR with automated vs manual sections
- Development insights for automation improvement

## SCSS Processing

### File Structure Creation

The tool creates a standard 3-file structure matching production patterns:

1. **sb-inside.scss** - Inside page styles
2. **sb-vdp.scss** - Vehicle Detail Page styles
3. **sb-vrp.scss** - Vehicle Results Page styles

### Processing Features

- **Production Headers**: File headers match exact production format
- **Legacy Extraction**: Processes existing inside.scss, vdp.scss, vrp.scss files
- **Standards Compliance**: Generated files follow Site Builder standards
- **Responsive Behavior**: Better responsive behavior across all devices

### Example Generated Headers

```scss
/*
	Loads on Site Builder VDP (Classic OR HotWheels if DT Override is toggled on)

	Documentation: https://dealerinspire.atlassian.net/wiki/spaces/WDT/pages/498572582/SCSS+Set+Up

	- After updating you'll need to generate the css in Site Builder settings
	- You can check if it compiled here:
		wp-content > uploads > sb-asset-cache > sb-vdp.css
*/
```

## OEM Detection System

### Brand Identification

- Automatic detection of dealer brand/OEM
- Support for Stellantis and non-Stellantis dealers
- Dynamic handler selection based on brand

### Stellantis Special Handling

- **Map Components**: Automatic map component generation
- **Directions Box**: Standard directions box implementation
- **Enhanced Templates**: Stellantis-specific production templates

## User Review System

### Interactive Review Features

- **File State Capture**: MD5 hashes, file sizes, line counts
- **Change Detection**: Identifies manual modifications post-automation
- **User Commands**:
  - `done` - Complete review session
  - `help` - Show available commands
  - `status` - Display current file states

### Change Tracking

- Size difference reporting (before/after manual edits)
- Line count changes
- Modification timestamps
- File integrity verification

### Integration with Workflow

- Seamless integration between automated migration and manual review
- Results feed into enhanced PR creation
- Development insights for improving automation

## CLI Interface

### Basic Commands

```bash
# Essential commands (shown by default)
sbm auto [dealer-name] # Full automated workflow
sbm doctor             # System diagnostics
sbm validate [dealer]  # Validate dealer slug

# Help commands
sbm --help     # Show basic commands
sbm -h         # Same as --help
sbm --advanced # Show all commands including hidden ones
```

### Advanced Commands (Hidden by default)

```bash
sbm setup [dealer]     # Setup only
sbm migrate [dealer]   # Migration only
sbm status             # Check status
sbm config-info        # Show configuration
sbm create-pr [dealer] # Create PR only
sbm monitor [dealer]   # Monitor progress
```

### Directory Independence

- SBM commands now work from any directory
- Proper absolute path resolution
- No dependency on specific working directories

## Version History

### Version 2.9.0 - Interactive User Review System (Latest)

**Major Features:**

- ✅ **Interactive User Review**: Manual review session with change tracking
- ✅ **Enhanced PR Creation**: Automated vs manual work separation
- ✅ **GitHub Action Confirmation**: Safety prompts before PR creation
- ✅ **Development Insights**: Tracking for automation improvement

**Bug Fixes:**

- Fixed OEMFactory method call hallucination
- Fixed SCSS file creation logic
- Fixed duplicate PR creation issues
- Enhanced git commit operations

### Version 0.2.0 - Real SBM Pattern Analysis (2024-12-18)

**Major Features:**

- ✅ **Real PR Analysis**: Analyzed 20+ production Stellantis SBM PRs
- ✅ **Pattern Matching**: Automation matches exact production patterns
- ✅ **File Structure**: Creates identical 3-file structure
- ✅ **Map Components**: Standard map components with directions box
- ✅ **Production Headers**: File headers match production format

**SCSS Processor:**

- ✅ **Stellantis Support**: Automatic map component generation
- ✅ **Legacy Style Extraction**: Processes existing SCSS files
- ✅ **Standard Templates**: Production-ready file templates

### Version 0.1.0 - Initial Release (2024-12-17)

**Core Features:**

- ✅ **CLI Interface**: Basic migration commands
- ✅ **OEM Detection**: Brand identification system
- ✅ **Configuration**: Flexible config system
- ✅ **Logging**: Comprehensive logging system

**Basic Functionality:**

- ✅ **Theme Processing**: Basic SCSS file handling
- ✅ **Validation**: Dealer slug validation
- ✅ **Error Handling**: Graceful error management

## Testing & Validation

### Real Pattern Tests

- Validates against actual production PR patterns
- File structure verification
- Content validation for map components and headers

### Production Validation Data

The tool has been tested against real production cases:

- case_11699_spitzermotorsofmansfieldcdjr
- case_12755_example_maserati_2
- case_12760_example_maserati_1
- case_12765_example_non_stellantis_2
- case_12770_example_non_stellantis_1
- case_12775_example_stellantis_5
- case_12780_example_stellantis_4
- case_12785_friendlycdjrofgeneva
- case_12790_larryroeschchryslerjeepdodgeram
- case_12797_perkinsmotors

### Testing Framework

- Comprehensive test suite with Pytest
- Real-world automation validation
- PR validation against production patterns

## Technical Implementation

### Core Principles

- **Modular Design**: Each component has single responsibility
- **Auto-Detection Over Configuration**: Minimal manual setup required
- **Regex-Based Processing**: Flexibility over perfect parsing
- **Error Handling**: Comprehensive try/catch with user-friendly messages
- **Type Hints**: Required for all functions and methods

### Key Bug Fixes Applied

1. **OEMFactory Method Call**: Fixed hallucinated method name

   ```python
   # Before (hallucinated):
   handler = OEMFactory.create_handler(dealer_slug)

   # After (correct):
   handler = OEMHandlerFactory(config).get_handler(dealer_slug)
   ```

2. **SCSS File Creation Logic**: Proper file existence checking
3. **Results Merging**: Fixed list concatenation vs .update() overwriting
4. **Git Operations**: Enhanced with absolute path handling

### Path Resolution

- Enhanced path resolution using `config.get_theme_path()` for absolute paths
- Fixed file existence checks to use proper absolute paths
- Git operations now use correct working directory parameters

### Integration Points

- GitHub CLI for repository operations
- Docker for DealerInspire platform integration
- Gulp for SCSS compilation
- Salesforce integration for change notifications

## Migration Impact

### For Existing Users

- No breaking changes to CLI interface
- Generated files now follow proper Site Builder standards
- Better responsive behavior across all devices

### For New Users

- Comprehensive styling guide with examples
- Clear best practices for Site Builder development
- Standards-compliant automation from day one

---

_This documentation was generated from indexed knowledge using the crawl4ai-rag system and represents the current state of the SBM Tool v2 project._
