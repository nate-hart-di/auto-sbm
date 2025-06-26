"""
SCSS transformer for the SBM tool.

This module provides functions for transforming SCSS variables and mixins to CSS.
"""

import re
import os
from ..utils.logger import logger


def replace_scss_variables(content):
    """
    Replace SCSS variables with CSS variables.
    
    Args:
        content (str): SCSS content to transform
        
    Returns:
        str: Transformed content
    """
    # Replace SCSS color functions first (before generic variable replacement)
    content = re.sub(r'darken\(\$primary,\s*\d+%\)', 'var(--primaryhover)', content)
    content = re.sub(r'lighten\(\$primary,\s*\d+%\)', 'var(--primary)', content)
    
    # Generic rule: Replace ALL $variable with var(--variable)
    # This matches any SCSS variable and converts it to CSS custom property
    content = re.sub(r'\$([a-zA-Z][a-zA-Z0-9_-]*)\b', r'var(--\1)', content)
    
    return content


def replace_scss_mixins(content):
    """
    Replace SCSS mixins with CSS equivalents.
    
    Args:
        content (str): SCSS content to transform
        
    Returns:
        str: Transformed content
    """
    # Replace @include flexbox() with display: flex
    content = re.sub(r'@include\s+flexbox\(\s*\)', 'display: flex', content)
    
    # Replace @include flex-direction(row) with flex-direction: row
    content = re.sub(r'@include\s+flex-direction\(\s*([^)]+)\s*\)', r'flex-direction: \1', content)
    
    # Replace @include flex-wrap(wrap) with flex-wrap: wrap
    content = re.sub(r'@include\s+flex-wrap\(\s*([^)]+)\s*\)', r'flex-wrap: \1', content)
    
    # Replace @include justify-content(center) with justify-content: center
    content = re.sub(r'@include\s+justify-content\(\s*([^)]+)\s*\)', r'justify-content: \1', content)
    
    # Replace @include align-items(center) with align-items: center
    content = re.sub(r'@include\s+align-items\(\s*([^)]+)\s*\)', r'align-items: \1', content)
    
    # Replace @include transition(...) with transition: ...
    content = re.sub(r'@include\s+transition\(\s*([^)]+)\s*\)', r'transition: \1', content)
    
    # Remove @extend directives
    content = re.sub(r'@extend\s+[^;]+;', '', content)
    
    return content


def replace_font_variables(content, variables_dict=None):
    """
    Replace font variables with their values.
    
    Args:
        content (str): SCSS content to transform
        variables_dict (dict, optional): Dictionary of font variables
        
    Returns:
        str: Transformed content
    """
    if variables_dict is None:
        # Default font variable replacements
        variables_dict = {
            "$heading-font": "'Lato', sans-serif",
            "$maintextfont": "'Open Sans', sans-serif"
        }
    
    # Replace each font variable
    for var, value in variables_dict.items():
        content = re.sub(re.escape(var), value, content)
    
    return content


def replace_relative_paths(content, slug):
    """
    Replace relative paths with absolute WordPress theme paths.
    
    Args:
        content (str): SCSS content to transform
        slug (str): Dealer theme slug
        
    Returns:
        str: Transformed content with absolute paths
    """
    # Replace relative paths in url() statements
    # ../../DealerInspireCommonTheme/file.png → /wp-content/themes/DealerInspireCommonTheme/file.png
    content = re.sub(
        r'url\([\'"]?\.\.\/\.\.\/DealerInspireCommonTheme\/([^\'"()]+)[\'"]?\)',
        r'url("/wp-content/themes/DealerInspireCommonTheme/\1")',
        content
    )
    
    # ../images/background.jpg → /wp-content/themes/DealerInspireDealerTheme/images/background.jpg
    content = re.sub(
        r'url\([\'"]?\.\.\/images\/([^\'"()]+)[\'"]?\)',
        r'url("/wp-content/themes/DealerInspireDealerTheme/images/\1")',
        content
    )
    
    # Replace relative paths in @import statements
    # @import "../file.scss" → @import "/wp-content/themes/DealerInspireDealerTheme/file.scss"
    content = re.sub(
        r'@import\s+[\'"]\.\.\/([^\'"]+)[\'"]',
        r'@import "/wp-content/themes/DealerInspireDealerTheme/\1"',
        content
    )
    
    # Fix double paths: ../../DealerInspireCommonTheme/ → /wp-content/themes/DealerInspireCommonTheme/
    content = re.sub(
        r'@import\s+[\'"]\.\.\/\.\.\/DealerInspireCommonTheme\/([^\'"]+)[\'"]',
        r'@import "/wp-content/themes/DealerInspireCommonTheme/\1"',
        content
    )
    
    # Fix double paths in commented imports too: // @import "../../DealerInspireCommonTheme/file"
    content = re.sub(
        r'//\s*@import\s+[\'"]\.\.\/\.\.\/DealerInspireCommonTheme\/([^\'"]+)[\'"]',
        r'// @import "/wp-content/themes/DealerInspireCommonTheme/\1"',
        content
    )
    
    return content


def remove_undefined_scss(content):
    """
    Remove undefined SCSS constructs.
    
    Args:
        content (str): SCSS content to clean
        
    Returns:
        str: Cleaned content
    """
    # Remove SCSS operations like $variable + 10px
    content = re.sub(r'\$[\w-]+\s*[\+\-\*\/]\s*\d+(?:px|em|rem|%)', 'auto', content)
    
    # Remove empty CSS rules
    content = re.sub(r'[^{}]+\{\s*\}', '', content)
    
    # Remove @include statements that weren't replaced
    content = re.sub(r'@include\s+[^;]+;', '', content)
    
    return content


def transform_scss(content, slug):
    """
    Apply all SCSS transformations.
    
    Args:
        content (str): SCSS content to transform
        slug (str): Dealer theme slug
        
    Returns:
        str: Transformed content
    """
    logger.info(f"Transforming SCSS content for {slug}")
    
    # Apply all transformations
    transformed = content
    transformed = replace_scss_variables(transformed)
    transformed = replace_scss_mixins(transformed)
    transformed = replace_font_variables(transformed)
    transformed = replace_relative_paths(transformed, slug)
    transformed = remove_undefined_scss(transformed)
    
    return transformed 
