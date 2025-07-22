# PRP Base Creation Template v2.1
# Meta-Template for Generating Context-Rich PRPs with Validation

## Purpose

This template enables AI agents to generate high-quality PRPs (Product Requirement Prompts) that contain sufficient context, validation loops, and implementation guidance for successful feature development. Use this template to create specific PRPs for any feature or enhancement.

## Core Principles for PRP Generation

1. **Context Saturation**: Include ALL necessary context up front
2. **Validation Driven**: Every step must have executable validation
3. **Pattern Recognition**: Leverage existing codebase patterns
4. **Progressive Success**: Build incrementally with verification
5. **Implementation Ready**: Output should be actionable immediately

---

## Template Generation Workflow

### Phase 1: Requirements Gathering

Use this section to analyze the feature request and gather comprehensive requirements.

#### Initial Analysis
```yaml
feature_request: "[Original request from user/stakeholder]"
complexity_level: "[Simple/Medium/Complex]"
target_template: "[base/spec/task/planning]"
language_stack: "[Python/TypeScript/Mixed]"
```

#### Context Discovery Questions
```yaml
business_context:
  - why_needed: "[Business value and user impact]"
  - who_benefits: "[Target users and stakeholders]"
  - success_metrics: "[How will success be measured]"
  - integration_points: "[Where does this connect to existing features]"

technical_context:
  - existing_patterns: "[What patterns in codebase should be followed]"
  - dependencies: "[Required libraries, services, or components]"
  - constraints: "[Technical limitations or requirements]"
  - validation_strategy: "[How will implementation be tested]"

implementation_context:
  - file_locations: "[Where will new code be added]"
  - data_models: "[Required data structures and schemas]"
  - apis_needed: "[New or modified endpoints]"
  - ui_components: "[User-facing changes]"
```

### Phase 2: Codebase Analysis

Before generating the PRP, perform thorough codebase analysis to ensure accurate patterns and context.

#### Pattern Discovery
```bash
# Use these searches to understand existing patterns
grep -r "class.*Service" src/ --include="*.py"
grep -r "export.*Component" src/ --include="*.ts" --include="*.tsx"
find . -name "test_*.py" -o -name "*.test.ts" -o -name "*.test.tsx"
find . -name "*validator*" -o -name "*schema*"
```

#### Architecture Understanding
```yaml
current_structure:
  - data_layer: "[How data is currently managed]"
  - business_layer: "[Where business logic lives]"
  - presentation_layer: "[UI/API patterns]"
  - testing_patterns: "[How tests are structured]"
  - error_handling: "[Error management patterns]"
```

### Phase 3: PRP Template Selection and Customization

Choose the appropriate base template and customize it for the specific feature.

#### Template Selection Guide
```yaml
prp_base.md:
  - use_when: "Complex features requiring comprehensive context"
  - best_for: "New major features, integrations, refactoring"
  - includes: "Full validation loops, integration points, extensive context"

prp_spec.md:
  - use_when: "Well-defined specifications need implementation"
  - best_for: "Features with clear requirements, API implementations"
  - includes: "High/mid/low level objectives, ordered tasks"

prp_task.md:
  - use_when: "Small, focused changes or bug fixes"
  - best_for: "Single-file changes, quick enhancements"
  - includes: "Concise task descriptions, validation commands"

prp_planning.md:
  - use_when: "Requirements need clarification and planning"
  - best_for: "Ambiguous requests, research-heavy features"
  - includes: "Diagrams, research phases, stakeholder alignment"

prp_base_typescript.md:
  - use_when: "TypeScript/React/Next.js features"
  - best_for: "Frontend features, full-stack TypeScript"
  - includes: "TypeScript-specific patterns, React patterns"
```

### Phase 4: PRP Content Generation

Generate the PRP content using the selected template with feature-specific context.

#### Required Context Gathering
```yaml
# MUST INCLUDE in every PRP
documentation_context:
  - relevant_files: "[List files that show patterns to follow]"
  - api_documentation: "[External API docs if applicable]"
  - library_docs: "[Specific sections of library documentation]"
  - gotchas_document: "[Known issues and solutions]"

codebase_context:
  - current_tree: "[Run tree command to show current structure]"
  - desired_tree: "[Show where new files will be added]"
  - similar_features: "[Point to existing similar implementations]"
  - integration_points: "[Where new code connects to existing code]"

validation_context:
  - test_patterns: "[How existing tests are structured]"
  - linting_config: "[Current code quality tools and config]"
  - ci_cd_requirements: "[Build and deployment considerations]"
  - performance_requirements: "[Any performance constraints]"
```

#### Implementation Blueprint Generation
```yaml
# Structure the implementation with progressive complexity
data_models:
  - schemas: "[Pydantic/Zod schemas needed]"
  - interfaces: "[TypeScript interfaces or Python protocols]"
  - validators: "[Input validation logic]"

business_logic:
  - services: "[Core business logic components]"
  - utilities: "[Helper functions and utilities]"
  - integrations: "[External service integrations]"

presentation_layer:
  - apis: "[API endpoints or routes]"
  - ui_components: "[User interface components]"
  - cli_commands: "[Command-line interfaces]"

testing_strategy:
  - unit_tests: "[Individual component tests]"
  - integration_tests: "[Cross-component tests]"
  - end_to_end_tests: "[Full workflow tests]"
```

#### Validation Loop Design
```yaml
# Create comprehensive validation for each implementation phase
level_1_syntax:
  - linting: "[Language-specific linting commands]"
  - type_checking: "[Static type analysis]"
  - formatting: "[Code formatting validation]"

level_2_unit_tests:
  - test_patterns: "[How to structure tests]"
  - test_commands: "[Commands to run specific tests]"
  - coverage_requirements: "[Minimum test coverage expectations]"

level_3_integration:
  - startup_commands: "[How to start services for testing]"
  - api_testing: "[How to test endpoints]"
  - ui_testing: "[How to verify user interfaces]"

level_4_deployment:
  - build_validation: "[Production build verification]"
  - performance_testing: "[Performance benchmarking]"
  - security_scanning: "[Security validation steps]"
```

### Phase 5: PRP Quality Validation

Ensure the generated PRP meets quality standards before use.

#### Completeness Checklist
```yaml
context_completeness:
  - [ ] All relevant files and patterns identified
  - [ ] External dependencies documented
  - [ ] Integration points clearly defined
  - [ ] Known gotchas and constraints listed

implementation_clarity:
  - [ ] Clear step-by-step tasks defined
  - [ ] Pseudocode provided for complex logic
  - [ ] File structure changes documented
  - [ ] Data models and APIs specified

validation_robustness:
  - [ ] Each level of validation has specific commands
  - [ ] Failure scenarios and debugging steps included
  - [ ] Success criteria clearly defined
  - [ ] Anti-patterns explicitly documented

actionability:
  - [ ] PRP can be executed without additional context
  - [ ] All commands are runnable in the target environment
  - [ ] Dependencies and setup requirements clear
  - [ ] Expected outcomes explicitly stated
```

#### Quality Gates
```bash
# Validate the generated PRP meets standards
# Check for completeness markers
grep -c "TODO\|TBD\|FIXME" generated_prp.md
# Should return 0

# Validate all code blocks have language specified
grep -c "^```$" generated_prp.md
# Should return 0 (all code blocks should specify language)

# Check for validation commands in each section
grep -c "VALIDATE:\|RUN:\|TEST:" generated_prp.md
# Should be > 0 (validation steps included)

# Verify anti-patterns section exists
grep -c "Anti-Patterns" generated_prp.md
# Should be > 0
```

---

## PRP Template Generation Examples

### Example 1: Python Feature PRP Generation
```yaml
input:
  request: "Add authentication middleware to FastAPI app"
  complexity: "Medium"
  stack: "Python"

output_template: "prp_base.md"
customizations:
  - Add FastAPI-specific patterns
  - Include JWT token handling
  - Focus on middleware integration
  - Add security testing validation
```

### Example 2: TypeScript Component PRP Generation
```yaml
input:
  request: "Create reusable data table component for Next.js"
  complexity: "Complex"
  stack: "TypeScript"

output_template: "prp_base_typescript.md"
customizations:
  - Add React component patterns
  - Include TypeScript prop definitions
  - Focus on reusability and accessibility
  - Add Storybook documentation
```

### Example 3: Quick Fix PRP Generation
```yaml
input:
  request: "Fix bug in user validation function"
  complexity: "Simple"
  stack: "Python"

output_template: "prp_task.md"
customizations:
  - Single file modification
  - Specific function update
  - Minimal validation needed
  - Quick turnaround focus
```

---

## Generated PRP Usage Instructions

### For AI Agents
1. **Pre-Implementation**: Read entire PRP thoroughly
2. **Context Gathering**: Load all referenced files and documentation
3. **Pattern Recognition**: Study existing codebase patterns before coding
4. **Incremental Implementation**: Follow the task order exactly
5. **Continuous Validation**: Run validation commands after each step
6. **Error Recovery**: Use debugging hints when validation fails

### For Human Developers
1. **Planning Review**: Validate the implementation plan makes sense
2. **Context Verification**: Ensure all referenced patterns exist
3. **Resource Allocation**: Plan time based on complexity indicators
4. **Checkpoint Monitoring**: Use validation gates as progress markers
5. **Quality Assurance**: Run final validation before deployment

### Using the PRP Runner
```bash
# Interactive development
uv run PRPs/scripts/prp_runner.py --prp feature_name --interactive

# Headless execution
uv run PRPs/scripts/prp_runner.py --prp feature_name --output-format json

# Streaming progress monitoring
uv run PRPs/scripts/prp_runner.py --prp feature_name --output-format stream-json
```

---

## Meta-Validation for This Template

### Self-Validation Checklist
- [ ] Template covers all PRP types in the system
- [ ] Provides clear selection criteria for each template type
- [ ] Includes comprehensive context gathering methodology
- [ ] Defines quality gates for generated PRPs
- [ ] Provides usage instructions for both AI and human users
- [ ] Integrates with existing PRP runner system

### Template Evolution
- Version 2.1: Added comprehensive template selection guide
- Future: Consider adding template validation automation
- Future: Add metrics collection for PRP success rates
- Future: Create template customization wizard

---

## Anti-Patterns to Avoid When Creating PRPs

- ❌ **Vague Requirements**: Don't accept incomplete or ambiguous feature requests
- ❌ **Missing Context**: Don't skip codebase analysis and pattern discovery
- ❌ **Weak Validation**: Don't create PRPs without executable validation steps
- ❌ **Template Mismatching**: Don't use complex templates for simple tasks
- ❌ **Context Overload**: Don't include irrelevant documentation
- ❌ **Insufficient Granularity**: Don't create tasks that are too large to validate
- ❌ **Pattern Deviation**: Don't ignore existing codebase conventions
- ❌ **Success Ambiguity**: Don't leave success criteria undefined

## Success Indicators for Generated PRPs

- ✅ **Implementation Success**: AI agents can complete the PRP without additional context
- ✅ **Validation Reliability**: All validation commands execute successfully
- ✅ **Pattern Consistency**: Generated code follows existing codebase conventions
- ✅ **Quality Maintenance**: Code meets all linting and testing standards
- ✅ **Integration Seamless**: New features integrate cleanly with existing code
- ✅ **Documentation Completeness**: All changes are properly documented
- ✅ **Maintainability**: Generated code is readable and maintainable