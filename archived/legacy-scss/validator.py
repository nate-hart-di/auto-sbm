"""
SCSS validator for the SBM tool.

This module provides functions for validating SCSS syntax and fixing common issues.
"""

import re
import os
from ..utils.logger import logger


def count_braces(content):
    """
    Count opening and closing braces in SCSS content.
    
    Args:
        content (str): SCSS content to analyze
        
    Returns:
        tuple: (opening_count, closing_count) - counts of opening and closing braces
    """
    opening_count = content.count('{')
    closing_count = content.count('}')
    
    return opening_count, closing_count


def fix_missing_semicolons(content):
    """
    Fix missing semicolons in SCSS content.
    
    Args:
        content (str): SCSS content to fix
        
    Returns:
        str: Fixed SCSS content
    """
    # Find CSS property declarations without semicolons
    # Look for property: value pairs that are followed by a closing brace or newline without a semicolon
    pattern = re.compile(r'([\w-]+\s*:\s*[^;{}]+)(?=\n\s*[}]|\n\s*[\w-]+\s*:)', re.MULTILINE)
    fixed = pattern.sub(r'\1;', content)
    
    return fixed


def fix_unbalanced_braces(content):
    """
    Fix unbalanced braces in SCSS content.
    
    Args:
        content (str): SCSS content to fix
        
    Returns:
        str: Fixed SCSS content with balanced braces
    """
    # First count the braces
    opening_count, closing_count = count_braces(content)
    
    logger.info(f"Brace count: {opening_count} opening, {closing_count} closing")
    
    if opening_count == closing_count:
        # Braces already balanced
        return content
    
    # Remove all closing braces at the end
    cleaned = re.sub(r'}+\s*$', '', content)
    
    # Count again
    new_opening, new_closing = count_braces(cleaned)
    missing = new_opening - new_closing
    
    if missing > 0:
        # Add the missing closing braces
        logger.info(f"Adding {missing} missing closing braces")
        fixed = cleaned + '\n' + '}\n' * missing
    else:
        # Too many closing braces, try more aggressive cleaning
        logger.info("Too many closing braces, attempting deeper fix")
        fixed = rebuild_brace_structure(cleaned)
    
    return fixed


def rebuild_brace_structure(content):
    """
    Completely rebuild the brace structure by analyzing the CSS rule structure.
    
    Args:
        content (str): SCSS content to fix
        
    Returns:
        str: Fixed SCSS content with properly structured braces
    """
    # First, let's identify CSS rule blocks properly
    lines = content.split('\n')
    fixed_lines = []
    
    # Keep track of rule nesting
    stack = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            fixed_lines.append(line)
            continue
            
        # Handle comments
        if stripped.startswith('//') or stripped.startswith('/*'):
            fixed_lines.append(line)
            continue
            
        # Count braces in this line
        open_braces = stripped.count('{')
        close_braces = stripped.count('}')
        
        # Push to stack for each opening brace
        for _ in range(open_braces):
            stack.append(1)
            
        # Pop from stack for each closing brace
        for _ in range(close_braces):
            if stack:
                stack.pop()
                
        # Keep the original line
        fixed_lines.append(line)
    
    # Add missing closing braces
    if stack:
        fixed_lines.append('')
        fixed_lines.append('/* Added missing closing braces */')
        for _ in range(len(stack)):
            fixed_lines.append('}')
    
    # Join lines to form fixed content
    fixed = '\n'.join(fixed_lines)
    
    # Check for any remaining brace issues - in case we didn't fix everything
    opening_count, closing_count = count_braces(fixed)
    if opening_count > closing_count:
        fixed += '\n' + '}' * (opening_count - closing_count) + '\n'
    
    return fixed


def fix_invalid_css_rules(content):
    """
    Fix invalid CSS rules in SCSS content.
    
    Args:
        content (str): SCSS content to fix
        
    Returns:
        str: Fixed SCSS content
    """
    # IMPORTANT: Check if the content has nesting issues with indented rules without proper braces
    # This pattern detects indented CSS properties that are likely missing their parent selector's opening brace
    # First let's fix nested rules without proper braces
    content_lines = content.split('\n')
    fixed_lines = []
    
    # Track if we're inside a rule
    in_rule = False
    rule_indent = 0
    last_selector = None
    
    for line in content_lines:
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            fixed_lines.append(line)
            continue
            
        # Check for selector line (ends with opening brace)
        if stripped.endswith('{'):
            in_rule = True
            rule_indent = len(line) - len(line.lstrip())
            last_selector = line
            fixed_lines.append(line)
            
        # Check for closing brace
        elif stripped == '}':
            in_rule = False
            fixed_lines.append(line)
            
        # Check for property without being in a rule - these are problematic indented rules
        elif ':' in stripped and ';' in stripped and not in_rule:
            # This is a property outside a rule - we should wrap it
            if last_selector is None:
                # Create a placeholder selector if none exists
                fixed_lines.append("/* Start of fixed rule structure */")
                fixed_lines.append("{")
                fixed_lines.append(line)
            else:
                # We have a previous selector to use
                if not fixed_lines[-1].endswith('{'):
                    fixed_lines.append("{")
                fixed_lines.append(line)
                
        # Any other line
        else:
            fixed_lines.append(line)
    
    # Now process with regular expressions
    content = '\n'.join(fixed_lines)
    
    # Fix rules with missing values
    pattern = re.compile(r'([\w-]+\s*:)\s*;', re.MULTILINE)
    fixed = pattern.sub(r'\1 initial;', content)
    
    # Fix rules with missing property names, but don't add "Empty rule" comments
    pattern = re.compile(r':\s*([^;{}]+);', re.MULTILINE)
    
    # Only replace if there's no property name before the colon
    def replace_if_invalid(match):
        line = match.string[:match.start()].split('\n')[-1].strip()
        if not re.match(r'[\w-]+\s*$', line):
            # No valid property name found, but don't comment it out
            # Just preserve the original text
            return match.group(0)
        return match.group(0)
    
    fixed = pattern.sub(replace_if_invalid, fixed)
    
    return fixed


def fix_invalid_media_queries(content):
    """
    Fix invalid media queries in SCSS content.
    
    Args:
        content (str): SCSS content to fix
        
    Returns:
        str: Fixed SCSS content
    """
    # Fix the double parentheses pattern with simpler, more direct regex
    fixed = re.sub(r'@media\s*\(\(', '@media (', content)
    fixed = re.sub(r'@media\s+screen\s+and\s+\(\(', '@media (', fixed)
    
    # Additional patterns to catch other variations
    fixed = re.sub(r'@media\s+([^(]+)\s*\(\(', r'@media \1 (', fixed)
    
    # Standardize media queries - remove unnecessary "screen and" for consistency
    fixed = re.sub(r'@media\s+screen\s+and\s+\(', '@media (', fixed)
    
    # Additional general cleanup
    # Fix missing closing parenthesis in media query conditions
    fixed = re.sub(r'@media[^{]*\([^)]*{', lambda match: match.group(0).replace('{', ') {'), fixed)
    
    # Remove any stray % characters at the end of blocks
    fixed = re.sub(r'}\s*%', '}', fixed)
    
    return fixed


def validate_scss_syntax(file_path):
    """
    Validate and fix SCSS syntax in a file.
    
    Args:
        file_path (str): Path to the SCSS file
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Validating SCSS syntax for {os.path.basename(file_path)}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Apply fixes in order
    fixed = content
    fixed = fix_missing_semicolons(fixed)
    fixed = fix_invalid_css_rules(fixed)
    fixed = fix_invalid_media_queries(fixed)
    fixed = fix_unbalanced_braces(fixed)
    
    # Count braces one more time to verify
    opening_count, closing_count = count_braces(fixed)
    
    logger.info(f"Final brace count: {opening_count} opening, {closing_count} closing")
    
    if opening_count != closing_count:
        logger.warning(f"Could not fully balance braces: {opening_count} opening, {closing_count} closing")
    
    # Write the fixed content back to the file
    with open(file_path, 'w') as f:
        f.write(fixed)
    
    return opening_count == closing_count 
