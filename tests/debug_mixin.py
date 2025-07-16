#!/usr/bin/env python3
"""Debug mixin parser output"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.scss.mixin_parser import CommonThemeMixinParser

# Test the specific failing case
parser = CommonThemeMixinParser()

# Test with CSS variable
content = "@include color-classes(primary, var(--primary-color));"
result, errors, unconverted = parser.parse_and_convert_mixins(content)

print("=== CSS Variable Test ===")
print(f"Content: {content}")
print(f"Result: {result}")
print(f"Errors: {errors}")
print(f"Unconverted: {unconverted}")
print()

# Test with hex color
content = "@include color-classes(primary, #252525);"
result, errors, unconverted = parser.parse_and_convert_mixins(content)

print("=== Hex Color Test ===")
print(f"Content: {content}")
print(f"Result: {result}")
print(f"Errors: {errors}")
print(f"Unconverted: {unconverted}")
print()

# Test the actual problematic case from andersonchrysler
content = "color: lighten(var(--primary), 20%);"
print("=== Problematic Case ===")
print(f"Content: {content}")
print(f"This should be handled by SCSS processor, not mixin parser")