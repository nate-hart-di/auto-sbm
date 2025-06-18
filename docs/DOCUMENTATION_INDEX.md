# Auto-SBM Documentation Index

## Overview

This documentation suite provides comprehensive coverage of the Auto-SBM (Site Builder Migration Tool V2) project. The documentation has been generated based on thorough analysis of the codebase, project structure, and existing documentation.

## Documentation Files

### 📚 Primary Documentation

#### 1. [COMPREHENSIVE_PROJECT_DOCUMENTATION.md](./COMPREHENSIVE_PROJECT_DOCUMENTATION.md)

**Complete project overview and technical specification**

- Project architecture and component analysis
- Technology stack and dependencies
- Detailed workflow explanations
- Performance metrics and optimization strategies
- Security considerations and deployment guidelines
- Future enhancement roadmap

#### 2. [API_REFERENCE.md](./API_REFERENCE.md)

**Complete API reference for developers**

- Core module documentation
- Class and method signatures with descriptions
- Error handling and exception classes
- Configuration management
- Utility functions and constants
- Usage examples and integration patterns

#### 3. [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)

**Developer setup and contribution guidelines**

- Development environment setup
- Code standards and formatting rules
- Testing strategies and best practices
- Performance optimization techniques
- Release process and version management
- Contributing guidelines and community standards

### 📋 Existing Documentation

#### 4. [README.md](../README.md)

**Quick start guide and usage examples**

- One-command migration workflow
- Installation instructions
- Command reference and options
- Success metrics and troubleshooting

#### 5. [AI_MEMORY_REFERENCE.md](./AI_MEMORY_REFERENCE.md)

**AI assistant orientation document**

- Project identity and purpose
- Core architecture principles
- Required reading for AI assistants

#### 6. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

**Quick command reference**

- Essential commands and options
- Common workflow patterns

## Documentation Structure

### By Audience

**End Users**:

- [README.md](../README.md) - Start here for basic usage
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Common commands

**Developers**:

- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Setup and contribution
- [API_REFERENCE.md](./API_REFERENCE.md) - Technical implementation details

**Project Managers/Stakeholders**:

- [COMPREHENSIVE_PROJECT_DOCUMENTATION.md](./COMPREHENSIVE_PROJECT_DOCUMENTATION.md) - Complete overview

**AI Assistants**:

- [AI_MEMORY_REFERENCE.md](./AI_MEMORY_REFERENCE.md) - Project orientation
- [quickstart/AI_ASSISTANT_QUICKSTART.md](./quickstart/AI_ASSISTANT_QUICKSTART.md) - Complete architecture guide

### By Topic

**Getting Started**:

1. [README.md](../README.md) - Basic usage
2. [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Development setup
3. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Command reference

**Technical Details**:

1. [COMPREHENSIVE_PROJECT_DOCUMENTATION.md](./COMPREHENSIVE_PROJECT_DOCUMENTATION.md) - Architecture
2. [API_REFERENCE.md](./API_REFERENCE.md) - Implementation details
3. [development/CHANGELOG.md](./development/CHANGELOG.md) - Recent changes

**Advanced Topics**:

1. Performance optimization strategies
2. OEM-specific implementations
3. SCSS transformation algorithms
4. Git workflow automation
5. Docker integration patterns

## Key Features Documented

### ✅ Automated Workflow

- Complete one-command migration (`sbm auto [dealer-slug]`)
- Git workflow automation (branch creation, PR generation)
- Docker container management and monitoring
- Real-time Gulp compilation tracking

### ✅ SCSS Processing

- Advanced mixin conversion (50+ supported mixins)
- Variable transformation to CSS custom properties
- Breakpoint standardization
- File mapping (lvdp.scss → sb-vdp.scss, etc.)

### ✅ Validation Framework

- Multi-tier validation system
- System environment checks
- SCSS syntax validation
- File integrity verification
- Force override capabilities

### ✅ OEM Integration

- Stellantis brand detection and specialized handling
- Custom PR templates and reviewer assignment
- FCA-specific migration patterns
- Extensible OEM handler architecture

### ✅ Error Handling

- Smart retry logic with exponential backoff
- Graceful degradation for service failures
- Comprehensive error classification and recovery
- Detailed error reporting with actionable suggestions

### ✅ Performance

- 5-10 minute average migration time
- 99% success rate on first run
- Parallel SCSS processing capabilities
- Intelligent caching strategies

## Usage Patterns

### Basic Migration

```bash
# Complete automated migration
sbm auto dealer-slug

# Force migration past warnings
sbm auto dealer-slug --force

# Preview changes without executing
sbm auto dealer-slug --dry-run
```

### Development Commands

```bash
# System diagnostics
sbm doctor

# Individual workflow steps
sbm setup dealer-slug    # Git setup only
sbm migrate dealer-slug  # Migration only
sbm validate dealer-slug # Validation only
sbm pr                   # Create PR only
```

### Advanced Options

```bash
# Skip Docker monitoring
sbm auto dealer-slug --skip-docker

# Enable verbose logging
sbm auto dealer-slug --verbose

# Use custom configuration
sbm auto dealer-slug --config custom.yml
```

## Quality Metrics

### Code Quality

- **Test Coverage**: 80% minimum, 95% for critical paths
- **Code Style**: Black formatting, flake8 linting, mypy type checking
- **Documentation**: 100% docstring coverage for public APIs

### Performance Benchmarks

- **Migration Speed**: 5-10 minutes end-to-end
- **SCSS Processing**: <30 seconds for typical themes
- **Git Operations**: <60 seconds including PR creation
- **Docker Startup**: <180 seconds with monitoring

### Success Metrics

- **99% Success Rate** on first migration attempt
- **Zero Manual Intervention** required for standard workflows
- **Automatic Error Recovery** for common failure scenarios
- **Comprehensive Logging** for debugging and audit trails

## Integration Points

### External Services

- **GitHub API**: Automated PR creation and management
- **Docker**: Container lifecycle management
- **Gulp**: Real-time compilation monitoring
- **Context7 API**: Enhanced documentation and error handling
- **MCP (Model Context Protocol)**: AI assistant integration

### File System Integration

- **DI Platform**: Auto-detection of `~/di-websites-platform`
- **Git Repository**: Automatic repository state management
- **SCSS Files**: Intelligent file mapping and transformation
- **Output Generation**: Atomic file operations with backup

## Maintenance

### Documentation Updates

- **Version Alignment**: Keep docs in sync with code changes
- **Example Updates**: Ensure examples reflect current API
- **Link Validation**: Regular check of internal and external links
- **Screenshot Updates**: Update UI screenshots as needed

### Code Examples

- **Functionality Coverage**: Examples for all major features
- **Error Scenarios**: Document common error cases and solutions
- **Integration Examples**: Real-world usage patterns
- **Performance Examples**: Optimization techniques and benchmarks

---

## Quick Navigation

**Start Here**: [README.md](../README.md) → [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

**For Developers**: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) → [API_REFERENCE.md](./API_REFERENCE.md)

**For Deep Dive**: [COMPREHENSIVE_PROJECT_DOCUMENTATION.md](./COMPREHENSIVE_PROJECT_DOCUMENTATION.md)

**For AI Assistants**: [AI_MEMORY_REFERENCE.md](./AI_MEMORY_REFERENCE.md) → [quickstart/AI_ASSISTANT_QUICKSTART.md](./quickstart/AI_ASSISTANT_QUICKSTART.md)

---

_This documentation index was generated as part of the comprehensive documentation effort for the auto-sbm project. For questions or updates, please refer to the project repository at https://github.com/nate-hart-di/auto-sbm_
