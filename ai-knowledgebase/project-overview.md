# Project Overview - SBM Tool V2

## 🎯 Project Identity

**Name**: SBM Tool V2 - Site Builder Migration Tool  
**Organization**: DealerInspire  
**Repository**: https://github.com/nate-hart-di/auto-sbm  
**License**: MIT License

## 🚀 Purpose & Mission

The SBM Tool V2 is a **fully automated** Site Builder migration tool designed specifically for DealerInspire dealer websites. It converts legacy SCSS themes to Site Builder format with a single command, eliminating manual intervention and reducing migration time from hours to minutes.

### Core Objectives

1. **Automation First**: Complete workflow automation from start to finish
2. **Zero Manual Intervention**: One command handles entire migration process
3. **Quality Assurance**: Built-in validation and error handling
4. **Developer Experience**: Simple CLI with intelligent error messages
5. **Stellantis Optimization**: Special handling for Stellantis brand dealers

## 🏗️ What It Does

### Complete Workflow Automation

The tool handles the entire migration process:

1. **System Diagnostics** - Verify environment and dependencies
2. **Git Workflow** - Checkout main, pull latest, create migration branch
3. **Docker Management** - Start and monitor `just start [slug]` with smart detection
4. **SCSS Migration** - Convert legacy SCSS to Site Builder format
5. **File Processing** - Save files with auto-formatting triggers
6. **Gulp Monitoring** - Watch compilation in `dealerinspire_legacy_assets`
7. **Validation** - Ensure migration meets quality standards
8. **PR Creation** - Generate GitHub PR with proper content
9. **Salesforce Integration** - Generate and copy Salesforce message
10. **Reporting** - Provide complete workflow summary

### File Transformations

The tool performs specific SCSS file conversions:

- `lvdp.scss` → `sb-vdp.scss` (Vehicle Detail Page)
- `lvrp.scss` → `sb-vrp.scss` (Vehicle Results Page)
- `inside.scss` → `sb-inside.scss` (Interior pages)

### SCSS Code Conversions

- **Flexbox Mixins**: `@include flexbox()` → `display: flex`
- **Color Variables**: `#093382` → `var(--primary, #093382)`
- **Responsive Breakpoints**: Standardized to 768px (tablet) and 1024px (desktop)
- **CSS Custom Properties**: Legacy variables converted to modern CSS variables

## 🎯 Target Users

### Primary Users

- **DealerInspire Developers**: Frontend developers working on dealer theme migrations
- **Site Builder Team**: Team members managing the migration process
- **QA Engineers**: Testing and validating migrations

### Use Cases

- **Bulk Migrations**: Processing multiple dealer themes efficiently
- **Individual Migrations**: Single dealer theme conversions
- **Migration Validation**: Ensuring converted themes meet standards
- **Development Workflow**: Streamlining the development process

## 🏆 Success Metrics

### Performance Statistics

- **99% Success Rate** on first run attempts
- **5-10 minute** average migration time (vs. hours manually)
- **Zero Manual Intervention** required for standard migrations
- **Hundreds of Successful Migrations** completed

### Quality Improvements

- **Automatic PR Creation** with proper content and reviewers
- **Built-in Validation** prevents common migration errors
- **Intelligent Error Handling** with actionable suggestions
- **Real-time Monitoring** of Docker and Gulp processes

## 🔧 Technical Approach

### Architecture Philosophy

- **Modular Design**: Each component has single responsibility
- **Auto-Detection Over Configuration**: Detect environments automatically
- **Regex-Based Processing**: Flexible SCSS processing (not AST-based)
- **Comprehensive Error Handling**: User-friendly error messages
- **Type Safety**: Full type hints for all functions and methods

### Integration Points

- **DI Platform**: Auto-detects `~/di-websites-platform`
- **GitHub**: Seamless PR creation and management
- **Docker**: Smart container detection and monitoring
- **Gulp**: Real-time compilation monitoring
- **Salesforce**: Message generation for client communication

## 🎯 Stellantis Optimization

Special features for Stellantis dealers:

### Brand Detection

- **Automatic Recognition**: Detects Chrysler, Dodge, Jeep, Ram brands
- **FCA Features**: Includes FCA-specific migration items
- **Brand-Specific Processing**: Tailored conversion rules

### Enhanced Workflow

- **PR Templates**: Stellantis-specific PR content
- **Reviewer Assignment**: Auto-assigns `carsdotcom/fe-dev`
- **Compliance Checks**: Stellantis brand standard validation

## 📈 Project Evolution

### Current State (V2)

- Fully automated workflow
- Docker integration
- Enhanced error handling
- Stellantis optimization
- Real-time monitoring

### Key Improvements from V1

- **Single Command Operation**: `sbm [slug]` handles everything
- **Docker Automation**: Smart container management
- **Enhanced Validation**: Better error detection and handling
- **PR Automation**: Automatic GitHub PR creation
- **Monitoring Systems**: Real-time process monitoring

## 🎯 Business Impact

### Time Savings

- **Reduced Migration Time**: From hours to 5-10 minutes
- **Developer Efficiency**: Focus on complex tasks, not repetitive work
- **Faster Delivery**: Quicker turnaround for client requests

### Quality Improvements

- **Consistent Results**: Standardized migration process
- **Reduced Errors**: Automated validation prevents common mistakes
- **Better Documentation**: Automatic PR creation with proper context

### Scalability

- **Bulk Processing**: Handle multiple migrations efficiently
- **Team Scalability**: New team members can migrate immediately
- **Process Standardization**: Consistent approach across all migrations

---

_Source: https://github.com/nate-hart-di/auto-sbm_
