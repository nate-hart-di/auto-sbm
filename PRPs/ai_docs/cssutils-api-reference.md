# cssutils API Reference for SCSS Parser Implementation

**Official Documentation**: https://cssutils.readthedocs.io/en/latest/parse.html  
**GitHub**: https://github.com/mackoel/python-cssutils  
**PyPI**: https://pypi.org/project/cssutils/

## Overview

cssutils is a higher-level CSS parser that provides a DOM-like interface for CSS manipulation. It's designed for comprehensive CSS processing with built-in validation and error handling.

## Key Characteristics for Our Use Case

- **High-level API**: Provides CSS DOM objects, easier to work with
- **Built-in validation**: Validates CSS syntax and properties
- **Error handling**: Graceful error handling with logging
- **CSS 2.1/3 support**: Comprehensive CSS specification support
- **Thread unsafe**: Not suitable for concurrent parsing

## Main API Functions

### Convenience Functions

```python
import cssutils

# Parse CSS from string
sheet = cssutils.parseString(css_text)

# Parse CSS from file
sheet = cssutils.parseFile('styles.css')

# Parse CSS from URL  
sheet = cssutils.parseUrl('http://example.com/styles.css')

# Parse inline style attribute
style = cssutils.parseStyle('color: red; background: blue;')
```

### CSSParser Class (Reusable)

```python
# Create reusable parser
parser = cssutils.CSSParser()

# Configure parser options
parser.setFetcher(custom_fetcher)  # Custom URL fetching

# Parse with parser
sheet = parser.parseString(css_text)
sheet = parser.parseFile('styles.css')
```

## Working with CSS DOM

### CSSStyleSheet Structure

```python
sheet = cssutils.parseString(css_text)

# Access all rules
for rule in sheet.cssRules:
    print(rule.type)  # Rule type constant
    print(rule.cssText)  # Serialized CSS

# Get serialized stylesheet
print(sheet.cssText)
```

### CSS Rule Types

```python
import cssutils.css

for rule in sheet.cssRules:
    if rule.type == cssutils.css.CSSRule.STYLE_RULE:
        # Style rule (.class { property: value; })
        style_rule = rule
        print(f"Selector: {style_rule.selectorText}")
        print(f"Declarations: {style_rule.style.cssText}")
        
    elif rule.type == cssutils.css.CSSRule.MEDIA_RULE:
        # Media query (@media screen { ... })
        media_rule = rule
        print(f"Media: {media_rule.media.mediaText}")
        for nested_rule in media_rule.cssRules:
            print(f"Nested: {nested_rule.cssText}")
            
    elif rule.type == cssutils.css.CSSRule.IMPORT_RULE:
        # Import rule (@import url(...))
        import_rule = rule
        print(f"Import: {import_rule.href}")
```

### Working with Selectors and Declarations

```python
# Access style rule components
style_rule = sheet.cssRules[0]  # Assuming first rule is style rule

# Selector manipulation
selectors = style_rule.selectorText  # "h1, h2, .class"
style_rule.selectorText = ".new-class"  # Modify selector

# Declaration manipulation  
declarations = style_rule.style

# Iterate through declarations
for property in declarations:
    print(f"{property.name}: {property.value}")
    print(f"Priority: {property.priority}")  # "important" or ""

# Add/modify declarations
declarations.setProperty('color', 'red', 'important')
declarations.removeProperty('background')

# Check if property exists
if declarations.getPropertyValue('color'):
    print("Color property exists")
```

## Implementation Pattern for StyleClassifier

```python
import cssutils
import re
from typing import Tuple, List

class ProfessionalStyleClassifier:
    def __init__(self):
        self.exclusion_patterns = [
            r'\.header\b', r'\.nav\b', r'\.footer\b'
        ]
        
        # Configure cssutils for our use case
        cssutils.log.setLevel('ERROR')  # Reduce logging noise
        
    def filter_scss_content(self, content: str) -> Tuple[str, ExclusionResult]:
        try:
            # Parse SCSS as CSS (limited SCSS support)
            sheet = cssutils.parseString(content)
        except Exception as e:
            logger.warning(f"CSS parsing failed, using fallback: {e}")
            return self._fallback_processing(content)
        
        # Filter rules
        filtered_rules = []
        excluded_rules = []
        
        # Process each rule
        for rule in list(sheet.cssRules):  # Create copy to allow modification
            if rule.type == cssutils.css.CSSRule.STYLE_RULE:
                should_exclude, reason = self._should_exclude_rule(rule)
                
                if should_exclude:
                    excluded_rules.append(rule.cssText)
                    sheet.deleteRule(rule)  # Remove from stylesheet
                    logger.debug(f"Excluded {reason} rule: {rule.selectorText}")
                else:
                    filtered_rules.append(rule.cssText)
            else:
                # Keep non-style rules (imports, media, etc.)
                filtered_rules.append(rule.cssText)
        
        # Generate result
        filtered_content = sheet.cssText
        return filtered_content, self._create_exclusion_result(excluded_rules)
    
    def _should_exclude_rule(self, rule) -> Tuple[bool, str]:
        """Check if CSS rule should be excluded."""
        selector_text = rule.selectorText
        
        for pattern in self.exclusion_patterns:
            if re.search(pattern, selector_text, re.IGNORECASE):
                if 'header' in pattern:
                    return True, 'header'
                elif 'nav' in pattern:
                    return True, 'navigation'  
                elif 'footer' in pattern:
                    return True, 'footer'
        
        return False, None
        
    def _create_exclusion_result(self, excluded_rules: List[str]) -> ExclusionResult:
        """Create exclusion result from excluded rules."""
        patterns_matched = {}
        for rule_text in excluded_rules:
            # Analyze rule to categorize exclusion reason
            if re.search(r'\.header\b', rule_text, re.IGNORECASE):
                patterns_matched['header'] = patterns_matched.get('header', 0) + 1
            elif re.search(r'\.nav\b', rule_text, re.IGNORECASE):
                patterns_matched['navigation'] = patterns_matched.get('navigation', 0) + 1
            elif re.search(r'\.footer\b', rule_text, re.IGNORECASE):
                patterns_matched['footer'] = patterns_matched.get('footer', 0) + 1
        
        return ExclusionResult(
            excluded_count=len(excluded_rules),
            included_count=0,  # Calculate separately if needed
            excluded_rules=excluded_rules,
            patterns_matched=patterns_matched
        )
```

## Advanced Features

### Custom URL Fetching

```python
def custom_fetcher(url):
    """Custom fetcher for imported stylesheets."""
    if url.startswith('http'):
        # Custom HTTP handling
        return 'utf-8', fetch_from_web(url)
    else:
        # Local file handling
        return 'utf-8', fetch_from_filesystem(url)

parser = cssutils.CSSParser()
parser.setFetcher(custom_fetcher)
```

### Error Handling and Logging

```python
import cssutils
import logging

# Configure cssutils logging
cssutils.log.setLevel(logging.ERROR)  # Only show errors

# Custom error handler
def handle_css_errors():
    try:
        sheet = cssutils.parseString(malformed_css)
    except Exception as e:
        logger.error(f"CSS parsing completely failed: {e}")
        return None
    
    # Check for parsing warnings/errors
    if cssutils.log.hasEffectiveLevel(logging.WARNING):
        logger.warning("CSS had parsing issues, but continued")
    
    return sheet
```

## Performance Considerations

- **Moderate performance**: Higher-level API has more overhead than tinycss2
- **Memory usage**: Creates DOM objects, uses more memory
- **Validation overhead**: Built-in validation slows parsing
- **Thread safety**: Not thread-safe, use separate parsers per thread

## SCSS Compatibility

cssutils has **limited SCSS support**:

```python
def preprocess_scss_for_cssutils(scss_content):
    """Basic SCSS preprocessing for cssutils."""
    # Remove SCSS-specific syntax that breaks CSS parsing
    
    # Remove SCSS variables (basic)
    content = re.sub(r'^\s*\$[\w-]+\s*:.*?;', '', scss_content, flags=re.MULTILINE)
    
    # Remove SCSS mixins (basic)
    content = re.sub(r'@mixin\s+[\w-]+.*?\{.*?\}', '', content, flags=re.DOTALL)
    
    # Remove SCSS includes
    content = re.sub(r'@include\s+[\w-]+.*?;', '', content)
    
    # Basic nesting flattening (very limited)
    # This is complex and error-prone for real SCSS
    
    return content

# Usage
preprocessed = preprocess_scss_for_cssutils(scss_content)
sheet = cssutils.parseString(preprocessed)
```

## Decision Matrix

**Pros for cssutils**:
- Higher-level, easier API
- Built-in CSS validation
- Good error handling
- Comprehensive CSS DOM
- Rule manipulation features

**Cons for cssutils**:
- Limited SCSS support
- Slower than low-level parsers
- Thread unsafe
- More memory usage
- Older codebase

## Recommendation

cssutils is suitable if:
1. We need comprehensive CSS manipulation
2. SCSS features in our files are minimal
3. We prefer higher-level, easier API
4. Built-in validation is valuable
5. Performance is not critical

Consider tinycss2 if:
1. We need better SCSS handling
2. Performance is critical
3. We want modern, actively maintained code
4. Lower-level control is acceptable

## Error Handling Strategy

```python
def robust_css_parsing(content):
    """Robust CSS parsing with fallback."""
    try:
        # First attempt: Parse as CSS
        sheet = cssutils.parseString(content)
        return sheet, "cssutils"
    except Exception as e:
        logger.warning(f"cssutils parsing failed: {e}")
        
        try:
            # Second attempt: Preprocess SCSS then parse
            preprocessed = preprocess_scss_for_cssutils(content)
            sheet = cssutils.parseString(preprocessed)
            return sheet, "cssutils_preprocessed"
        except Exception as e2:
            logger.error(f"Preprocessed CSS parsing failed: {e2}")
            
            # Final fallback: Use simple regex-based processing
            return None, "fallback_required"
```