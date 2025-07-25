# PRP: Replace Custom CSS Parser with Professional Library

## Problem Statement

The current `StyleClassifier.filter_scss_content()` uses a naive, hand-written CSS parser that fails to correctly identify and exclude header/footer/navigation styles. This causes critical compilation errors in production.

### Current Failures
- **Comma-separated selectors**: Misses first selector in multi-line rules
- **Complex SCSS nesting**: Doesn't handle `&` parent references
- **Media queries**: Fails with breakpoint conditions
- **Comments within rules**: Breaks brace counting logic

### Specific Error Pattern
```scss
.navbar .navbar-inner ul.nav li a,              ← Missed by parser
.navbar .navbar-inner ul.nav li a.dropdown-menu { ← Only this line checked
```

## Requirements

### Functional Requirements
1. **100% accurate CSS/SCSS rule parsing** - no missed patterns
2. **Complete rule exclusion** - entire rules excluded, not commented
3. **Handle complex patterns**:
   - Comma-separated selectors (single rule, multiple selectors)
   - SCSS nesting with `&` parent references
   - Media queries with complex conditions
   - Multi-line rules spanning 10+ lines
   - Comments mixed within rule declarations

### Technical Requirements
4. **Use established CSS parsing library** - no custom parsers
5. **Maintain existing exclusion patterns** - header/nav/footer detection
6. **Preserve logging** - show what was excluded and why
7. **Performance** - handle large SCSS files (1000+ lines)
8. **Error handling** - graceful fallback if parsing fails

## Research: Available Libraries

Based on 2024 research:

### Option A: `cssutils` (Recommended)
- **Status**: Actively maintained (v2.11.1, June 2024)
- **Supports**: CSS 2.1, CSS 3, MediaQueries
- **Python**: 3.8+ compatible
- **Pros**: Most recent updates, mature API
- **Cons**: CSS-focused, may need SCSS preprocessing

### Option B: `libsass-python`
- **Status**: Deprecated (LibSass deprecated for Dart Sass)
- **Supports**: Full SCSS compilation
- **Pros**: Complete SCSS understanding
- **Cons**: Deprecated upstream, compilation-focused

### Option C: `python-scss`
- **Status**: Community maintained
- **Supports**: SCSS parsing and compilation
- **Pros**: SCSS-native
- **Cons**: Less maintained than cssutils

## Implementation Strategy

**Note**: The specific approach will be determined after thorough research and experimentation. Multiple strategies may be evaluated before selecting the optimal solution.

### Potential Approaches (To Be Validated)

#### Strategy A: Professional CSS Parser Integration
- Integrate established library (cssutils, python-scss, etc.)
- Parse CSS/SCSS into proper AST
- Apply exclusion logic to parsed rules

#### Strategy B: Hybrid Preprocessing Approach
- Use SCSS compiler to normalize syntax first
- Apply professional CSS parser to normalized output
- Map exclusions back to original SCSS

#### Strategy C: Conservative Pattern Matching
- Advanced regex/string matching for CSS patterns
- Over-exclude rather than under-exclude
- Simpler but potentially broader exclusions

#### Strategy D: External Tool Integration
- Leverage existing CSS/SCSS tooling (PostCSS, etc.)
- Use subprocess calls to proven tools
- Handle tool output and errors gracefully

### Research & Evaluation Phase

**Before implementation**, conduct thorough evaluation:

1. **Library Compatibility Testing**
   - Test each library with real SCSS files from themes
   - Evaluate handling of SCSS-specific syntax
   - Check performance with large files

2. **Pattern Recognition Accuracy**
   - Test against known problematic patterns
   - Validate comma-separated selector handling
   - Verify nested media query support

3. **Integration Complexity Assessment**
   - Evaluate dependency management impact
   - Consider build/deployment complexity
   - Assess maintainability of each approach

### Implementation Phases (Strategy TBD)

#### Phase 1: Research & Proof of Concept
- Evaluate multiple approaches with small-scale tests
- Create prototypes for most promising strategies
- Document findings and trade-offs

#### Phase 2: Selected Implementation
- Implement chosen strategy based on research results
- Create comprehensive test suite
- Benchmark against current implementation

#### Phase 3: Integration & Validation
- Replace existing StyleClassifier
- Test with real theme files
- Performance and accuracy validation

## Implementation Plan

### Tasks
- [ ] **Research Phase**: Evaluate available CSS/SCSS parsing solutions
- [ ] **Prototype Phase**: Create small-scale implementations of top candidates
- [ ] **Validation Phase**: Test prototypes against real theme files
- [ ] **Selection Phase**: Choose optimal approach based on research findings
- [ ] **Implementation Phase**: Build selected solution
- [ ] **Testing Phase**: Comprehensive test suite and validation
- [ ] **Integration Phase**: Replace existing StyleClassifier
- [ ] **Cleanup Phase**: Remove deprecated parsing logic

### Success Criteria
- [ ] ferneliuscdjr theme compiles without errors
- [ ] All comma-separated selectors handled correctly
- [ ] Complex SCSS patterns (nesting, media queries) work
- [ ] No performance regression vs current implementation
- [ ] 100% test coverage for exclusion patterns

## Risk Assessment

### High Risk
- **Unknown implementation complexity** - chosen solution may be more complex than anticipated
- **Library compatibility** - selected library may not handle all SCSS patterns
- **Performance impact** - professional parsing may introduce latency
- **Breaking changes** - new exclusion behavior might be different

### Mitigation
- **Multi-strategy evaluation** - test multiple approaches before committing
- **Incremental implementation** - build and test in small iterations
- **Fallback planning** - maintain ability to revert if new approach fails
- **Comprehensive testing** - validate against all known problematic patterns
- **Performance benchmarking** - ensure no significant regression

## Dependencies

### External
- CSS parsing library (cssutils recommended)
- Updated requirements.txt

### Internal
- Modified StyleClassifier interface
- Updated tests for new exclusion behavior
- Documentation updates

## Timeline Estimate

- **Research & Evaluation**: 1-2 days
- **Prototyping & Testing**: 1-2 days
- **Strategy Selection**: 0.5 days
- **Implementation**: 2-4 days (varies by chosen approach)
- **Testing & Validation**: 1-2 days
- **Integration & Deployment**: 1 day

**Total**: 6-11 days (depends on research findings and chosen strategy)

## Post-Implementation

### Monitoring
- Track compilation success rates
- Monitor exclusion accuracy
- Performance metrics vs old implementation

### Maintenance
- Keep CSS parsing library updated
- Extend exclusion patterns as needed
- Document new exclusion capabilities

---

**Priority**: Critical
**Effort**: Medium
**Impact**: High (eliminates compilation failures)