# tinycss2 API Reference for SCSS Parser Implementation

**Official Documentation**: https://doc.courtbouillon.org/tinycss2/stable/api_reference.html  
**GitHub**: https://github.com/Kozea/tinycss2  
**PyPI**: https://pypi.org/project/tinycss2/

## Overview

tinycss2 is a low-level CSS parser based on CSS Syntax Level 3 specification. It's designed to be composable and flexible, parsing CSS grammar without interpreting specific properties or at-rules.

## Key Characteristics for Our Use Case

- **Low-level parsing**: Provides CSS tokens and blocks, not semantic interpretation
- **CSS3 compliant**: Follows modern CSS syntax specification
- **No SCSS support**: Only parses CSS syntax, not SCSS-specific features
- **Composable**: Functions can be combined for specific parsing needs

## Main API Functions

### Core Parsing Functions

```python
import tinycss2

# Parse complete stylesheets
rules = tinycss2.parse_stylesheet(css_string)

# Parse rule content (declarations inside {})
declarations = tinycss2.parse_blocks_contents(rule_content)

# Parse a single CSS rule
rule = tinycss2.parse_one_rule(css_rule)

# Parse component values (selectors, property values)
components = tinycss2.parse_component_value_list(css_text)
```

### Node Types and Properties

#### QualifiedRule (Style Rules)
```python
for rule in rules:
    if rule.type == 'qualified-rule':
        # rule.prelude contains selector tokens
        # rule.content contains declaration block tokens
        selectors = tinycss2.serialize(rule.prelude)
        declarations = tinycss2.parse_blocks_contents(rule.content)
```

#### AtRule (@media, @import, etc.)
```python
for rule in rules:
    if rule.type == 'at-rule':
        # rule.at_keyword is the at-rule name ('media', 'import')
        # rule.prelude contains the at-rule parameters
        # rule.content contains nested rules (for @media)
```

#### Declaration (Property: value pairs)
```python
for declaration in declarations:
    if declaration.type == 'declaration':
        # declaration.name is the property name
        # declaration.value is the property value tokens
        property_name = declaration.name
        property_value = tinycss2.serialize(declaration.value)
```

## Implementation Strategy for SCSS

### Challenge: SCSS Compatibility
tinycss2 only parses CSS syntax. For SCSS files, we need preprocessing:

```python
import subprocess
import tinycss2

def preprocess_scss_to_css(scss_content):
    """Convert SCSS to CSS using external tool."""
    # Option 1: Use sass command line tool
    result = subprocess.run(['sass', '--stdin'], 
                          input=scss_content, 
                          capture_output=True, 
                          text=True)
    return result.stdout

def parse_scss_with_tinycss2(scss_content):
    """Parse SCSS by converting to CSS first."""
    css_content = preprocess_scss_to_css(scss_content)
    return tinycss2.parse_stylesheet(css_content)
```

### Alternative: Parse SCSS Directly (Limited)
For simple SCSS without advanced features:

```python
def parse_simple_scss(scss_content):
    """Parse SCSS with limited nesting support."""
    # Replace SCSS variables with CSS custom properties
    css_content = re.sub(r'\$([a-zA-Z-]+)', r'var(--\1)', scss_content)
    
    # Basic nesting expansion (very limited)
    # This is complex and error-prone for real SCSS
    
    return tinycss2.parse_stylesheet(css_content)
```

## Implementation Pattern for StyleClassifier

```python
import tinycss2
from typing import List, Tuple

class ProfessionalStyleClassifier:
    def __init__(self):
        self.exclusion_patterns = [
            r'\.header\b', r'\.nav\b', r'\.footer\b'
        ]
    
    def filter_scss_content(self, content: str) -> Tuple[str, ExclusionResult]:
        # Convert SCSS to CSS first
        css_content = self._preprocess_scss(content)
        
        # Parse with tinycss2
        rules = tinycss2.parse_stylesheet(css_content)
        
        # Filter rules
        filtered_rules = []
        excluded_rules = []
        
        for rule in rules:
            if rule.type == 'qualified-rule':
                selector_text = tinycss2.serialize(rule.prelude).strip()
                if self._should_exclude_selector(selector_text):
                    excluded_rules.append(tinycss2.serialize(rule))
                else:
                    filtered_rules.append(tinycss2.serialize(rule))
            else:
                # Keep at-rules, comments, etc.
                filtered_rules.append(tinycss2.serialize(rule))
        
        filtered_content = '\n'.join(filtered_rules)
        return filtered_content, self._create_exclusion_result(excluded_rules)
    
    def _should_exclude_selector(self, selector: str) -> bool:
        """Check if selector matches exclusion patterns."""
        return any(re.search(pattern, selector) for pattern in self.exclusion_patterns)
    
    def _preprocess_scss(self, scss_content: str) -> str:
        """Convert SCSS to CSS for parsing."""
        # Implementation depends on chosen preprocessing strategy
        pass
```

## Error Handling

```python
def safe_parse_css(css_content):
    """Parse CSS with error handling."""
    try:
        rules = tinycss2.parse_stylesheet(css_content)
        return rules, None
    except Exception as e:
        logger.error(f"CSS parsing failed: {e}")
        return [], str(e)
```

## Performance Considerations

- **Fast**: tinycss2 is designed for performance
- **Memory efficient**: Low-level parsing with minimal object creation
- **Streaming capable**: Can parse large stylesheets incrementally

## Limitations for Our Use Case

1. **No SCSS support**: Requires preprocessing step
2. **Low-level**: More work to extract high-level rule information
3. **No semantic validation**: Doesn't validate CSS property values
4. **Manual selector parsing**: Need to implement selector pattern matching

## Decision Matrix

**Pros for tinycss2**:
- Modern, actively maintained
- CSS3 compliant
- Fast and efficient
- Flexible, composable API

**Cons for tinycss2**:
- Requires SCSS preprocessing
- More complex implementation
- Low-level API needs more code

## Recommendation

tinycss2 is suitable if:
1. We can reliably preprocess SCSS to CSS
2. We need precise CSS parsing control
3. Performance is critical
4. We want modern, well-maintained parser

Consider cssutils if:
1. We need higher-level CSS manipulation
2. SCSS preprocessing is problematic
3. We prefer simpler, more direct API