#!/usr/bin/env python3
"""
Improved style parser for the SBM tool.

This script improves the style extraction by properly handling complex CSS rules
and keeping related selectors together.
"""

import os
import re
import sys
import argparse
from sbm.utils.logger import setup_logger, logger
from sbm.utils.path import get_dealer_theme_dir
from sbm.scss.parser import read_scss_file, clean_scss_content


def parse_style_rules(style_content):
    """
    Parse SCSS content into discrete style rules and their categories.
    
    Args:
        style_content (str): Content of style.scss file
        
    Returns:
        list: List of dictionaries with 'rule' and 'category' keys
    """
    # Remove imports to focus on the actual styles
    content_lines = style_content.splitlines()
    non_import_lines = []
    for line in content_lines:
        if not re.match(r'^\s*@import', line):
            non_import_lines.append(line)
    
    content = '\n'.join(non_import_lines)
    
    # Define patterns for classification - expanded to catch more variations
    vdp_patterns = [
        r'\.vdp\b', r'\.lvdp\b', r'\.vehicle-detail', r'vdp--', r'\bvehicle-details',
        r'vdp-price-box', r'page-template-vehicle', r'single-vehicle', r'vehicle-page',
        r'\bvdp[\s_-]', r'[\s_-]vdp\b', r'vehicle-detail-page', r'vehicle_detail', 
        r'details-page', r'detail-view', r'single-inventory-vehicle'
    ]
    vrp_patterns = [
        r'\.vrp\b', r'\.lvrp\b', r'\.srp\b', r'\.vehicle-list', r'\.vehicle-results',
        r'inventory-page', r'page-template-inventory', r'search-results-page',
        r'\bvrp[\s_-]', r'[\s_-]vrp\b', r'\bsrp[\s_-]', r'[\s_-]srp\b',
        r'vehicle-results-page', r'inventory-results', r'inventory-listing'
    ]
    
    # First, try to find and handle ticket-wrapped rules specifically
    # This is a special case to handle complete rules with ticket numbers
    ticket_rules = []
    ticket_pattern = re.compile(r'(//.*?\d{5,}.*?start\s*\n)(.*?)(//.*?\d{5,}.*?end)', re.DOTALL)
    
    for match in ticket_pattern.finditer(content):
        ticket_start = match.group(1)
        rule_content = match.group(2)
        ticket_end = match.group(3)
        ticket_num = re.search(r'\d{5,}', ticket_start).group(0) if re.search(r'\d{5,}', ticket_start) else None
        
        # Extract ticket information for debugging
        logger.debug(f"Processing ticket rule #{ticket_num if ticket_num else 'unknown'}")
        
        # Check if this rule contains VDP patterns
        has_vdp = any(re.search(pattern, rule_content, re.IGNORECASE) for pattern in vdp_patterns)
        
        # Check if this rule contains VRP patterns
        has_vrp = any(re.search(pattern, rule_content, re.IGNORECASE) for pattern in vrp_patterns)
        
        # Assign to appropriate category - VDP takes precedence over VRP
        if has_vdp:
            # This rule has VDP content - entire rule goes to VDP
            ticket_rules.append({
                'rule': ticket_start + rule_content + ticket_end,
                'category': 'vdp',
                'ticket': ticket_num
            })
            logger.debug(f"Ticket rule #{ticket_num if ticket_num else 'unknown'} assigned to VDP")
        elif has_vrp:
            # This rule has VRP content - entire rule goes to VRP
            ticket_rules.append({
                'rule': ticket_start + rule_content + ticket_end,
                'category': 'vrp',
                'ticket': ticket_num
            })
            logger.debug(f"Ticket rule #{ticket_num if ticket_num else 'unknown'} assigned to VRP")
        else:
            # Default to inside
            ticket_rules.append({
                'rule': ticket_start + rule_content + ticket_end,
                'category': 'inside',
                'ticket': ticket_num
            })
            logger.debug(f"Ticket rule #{ticket_num if ticket_num else 'unknown'} assigned to inside")
        
        # Remove this rule from content to avoid processing it again
        content = content.replace(match.group(0), '')
    
    # Now proceed with normal rule extraction
    rules = ticket_rules  # Start with the ticket rules we already processed
    current_rule = []
    bracket_count = 0
    
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines at the start of a rule
        if not current_rule and not line.strip():
            i += 1
            continue
        
        # Check if this might be a comment block or section header
        if (line.strip().startswith('//') or line.strip().startswith('/*')) and not bracket_count:
            # Collect comment block
            comment_block = [line]
            i += 1
            while i < len(lines) and ((lines[i].strip().startswith('//') or 
                                       lines[i].strip().startswith('/*')) and
                                       not '{' in lines[i]):
                comment_block.append(lines[i])
                i += 1
            
            if i < len(lines) and ('{' in lines[i] or (i+1 < len(lines) and '{' in lines[i+1])):
                # This comment belongs to the next rule
                current_rule.extend(comment_block)
            else:
                # This is a standalone comment or section header
                if comment_block:
                    rules.append({
                        'rule': '\n'.join(comment_block),
                        'category': 'inside'  # Default category for comments
                    })
            continue
        
        # Count brackets to track rule boundaries
        bracket_count += line.count('{')
        bracket_count -= line.count('}')
        
        current_rule.append(line)
        
        # If brackets are balanced and we have content, we've reached the end of a rule
        if bracket_count == 0 and current_rule:
            rule_text = '\n'.join(current_rule)
            
            # Determine the category
            category = 'inside'  # Default
            
            # First check entire rule for ticket numbers containing specific keywords
            if re.search(r'//.*?(vdp|vehicle\s*detail).*?(start|end)', rule_text, re.IGNORECASE):
                category = 'vdp'
            elif re.search(r'//.*?(vrp|srp|inventory).*?(start|end)', rule_text, re.IGNORECASE):
                category = 'vrp'
            # Special case: multi-selector rules with commas - check each selector
            elif ',' in rule_text.split('{')[0]:
                # Extract all selectors before the first opening brace
                selectors_part = rule_text.split('{')[0]
                
                # Check if the entire rule contains VDP or VRP patterns first - faster check
                rule_has_vdp = any(re.search(pattern, rule_text, re.IGNORECASE) for pattern in vdp_patterns)
                rule_has_vrp = any(re.search(pattern, rule_text, re.IGNORECASE) for pattern in vrp_patterns)
                
                # If the rule contains VDP patterns, put the whole rule in VDP
                if rule_has_vdp:
                    category = 'vdp'
                    logger.debug(f"Multi-selector rule assigned to VDP due to containing VDP selectors")
                # If not VDP but contains VRP patterns, put the whole rule in VRP
                elif rule_has_vrp:
                    category = 'vrp'
                    logger.debug(f"Multi-selector rule assigned to VRP due to containing VRP selectors")
                else:
                    # More detailed analysis - split the selectors and check each one
                    # First, handle any nested selectors by temporarily replacing commas within parentheses
                    modified_selectors = re.sub(r'\([^)]*,[^)]*\)', lambda m: m.group(0).replace(',', '###COMMA###'), selectors_part)
                    
                    # Now split by comma
                    selectors = [s.strip().replace('###COMMA###', ',') for s in modified_selectors.split(',')]
                    
                    # Check each selector
                    has_vdp = False
                    has_vrp = False
                    
                    for selector in selectors:
                        if any(re.search(pattern, selector, re.IGNORECASE) for pattern in vdp_patterns):
                            has_vdp = True
                            logger.debug(f"Found VDP selector: {selector}")
                        elif any(re.search(pattern, selector, re.IGNORECASE) for pattern in vrp_patterns):
                            has_vrp = True
                            logger.debug(f"Found VRP selector: {selector}")
                    
                    # If any selector matches VDP, the whole rule goes to VDP
                    if has_vdp:
                        category = 'vdp'
                        logger.debug(f"Multi-selector rule assigned to VDP category")
                    # Otherwise, if any selector matches VRP, the whole rule goes to VRP
                    elif has_vrp:
                        category = 'vrp'
                        logger.debug(f"Multi-selector rule assigned to VRP category")
                    # Default to inside if no patterns match
                    else:
                        logger.debug(f"Multi-selector rule assigned to inside category (no VDP/VRP matches)")
            # Check for VDP or VRP patterns in the entire rule text
            elif any(re.search(pattern, rule_text, re.IGNORECASE) for pattern in vdp_patterns):
                category = 'vdp'
            elif any(re.search(pattern, rule_text, re.IGNORECASE) for pattern in vrp_patterns):
                category = 'vrp'
            
            # Check if this rule has a ticket number
            ticket_match = re.search(r'//.*?(\d{5,}).*?(start|end)', rule_text, re.IGNORECASE)
            ticket_num = ticket_match.group(1) if ticket_match else None
            
            rules.append({
                'rule': rule_text,
                'category': category,
                'ticket': ticket_num
            })
            
            current_rule = []
        
        i += 1
    
    return rules


def clean_style_output(content):
    """
    Clean up the style output to remove redundant formatting and ensure consistent style.
    
    Args:
        content (str): Content to clean
        
    Returns:
        str: Cleaned content
    """
    if not content:
        return ""
    
    # Remove redundant empty lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Ensure the content starts and ends with a newline
    content = content.strip()
    
    return content


def distribute_rules(rules, include_comments=True):
    """
    Distribute rules to the appropriate style files.
    
    Args:
        rules (list): List of rule dictionaries
        include_comments (bool): Whether to include ticket comments in the output
        
    Returns:
        dict: Categorized style content
    """
    categorized = {
        'vdp': [],
        'vrp': [],
        'inside': []
    }
    
    for rule in rules:
        category = rule['category']
        rule_text = rule['rule']
        
        # Add ticket comment if present and comments are enabled
        if include_comments and rule.get('ticket'):
            # Keep the ticket comments as they are already part of the rule_text
            pass
        
        categorized[category].append(rule_text)
    
    # Join rules for each category
    for category in categorized:
        categorized[category] = '\n\n'.join(categorized[category])
        # Clean up the output
        categorized[category] = clean_style_output(categorized[category])
    
    return categorized


def process_style_scss(slug, dry_run=False):
    """
    Process style.scss file and distribute styles to appropriate Site Builder files.
    
    Args:
        slug (str): Dealer theme slug
        dry_run (bool): If True, only print what would be done without modifying files
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get dealer theme directory
        theme_dir = get_dealer_theme_dir(slug)
        logger.info(f"Processing style.scss for {slug} in {theme_dir}")
        
        # Find style.scss file
        style_file_paths = [
            os.path.join(theme_dir, "css", "style.scss"),
            os.path.join(theme_dir, "style.scss")
        ]
        
        style_content = None
        style_file_path = None
        
        for path in style_file_paths:
            content = read_scss_file(path)
            if content:
                style_content = content
                style_file_path = path
                logger.info(f"Found style.scss at {path}")
                break
        
        if not style_content:
            logger.warning(f"No style.scss found for {slug}")
            return False
        
        # Parse style rules
        logger.info(f"Analyzing {len(style_content.splitlines())} lines in style.scss")
        rules = parse_style_rules(style_content)
        
        # Count rules by category
        counts = {'vdp': 0, 'vrp': 0, 'inside': 0}
        for rule in rules:
            counts[rule['category']] += 1
        
        logger.info(f"Found {len(rules)} total style rules")
        logger.info(f"  - VDP rules: {counts['vdp']}")
        logger.info(f"  - VRP rules: {counts['vrp']}")
        logger.info(f"  - Inside rules: {counts['inside']}")
        
        # Distribute rules to appropriate files
        categorized = distribute_rules(rules)
        
        # Write to files if not dry run
        if not dry_run:
            # Add to sb-vdp.scss
            if categorized['vdp']:
                vdp_file = os.path.join(theme_dir, "sb-vdp.scss")
                try:
                    with open(vdp_file, 'a') as f:
                        f.write("\n\n/* Styles from style.scss */\n")
                        f.write(categorized['vdp'])
                    logger.info(f"Added VDP styles to {vdp_file}")
                except Exception as e:
                    logger.error(f"Error writing to {vdp_file}: {e}")
            
            # Add to sb-vrp.scss
            if categorized['vrp']:
                vrp_file = os.path.join(theme_dir, "sb-vrp.scss")
                try:
                    with open(vrp_file, 'a') as f:
                        f.write("\n\n/* Styles from style.scss */\n")
                        f.write(categorized['vrp'])
                    logger.info(f"Added VRP styles to {vrp_file}")
                except Exception as e:
                    logger.error(f"Error writing to {vrp_file}: {e}")
            
            # Add to sb-inside.scss
            if categorized['inside']:
                inside_file = os.path.join(theme_dir, "sb-inside.scss")
                try:
                    with open(inside_file, 'a') as f:
                        f.write("\n\n/* Styles from style.scss */\n")
                        f.write(categorized['inside'])
                    logger.info(f"Added Inside styles to {inside_file}")
                except Exception as e:
                    logger.error(f"Error writing to {inside_file}: {e}")
        else:
            logger.info("Dry run - no files were modified")
            
            # Show sample output
            if categorized['vdp']:
                logger.info(f"Sample VDP styles ({len(categorized['vdp'].splitlines())} lines):")
                sample_lines = categorized['vdp'].splitlines()[:5]
                for line in sample_lines:
                    logger.info(f"  {line}")
                if len(sample_lines) < len(categorized['vdp'].splitlines()):
                    logger.info("  ...")
            
            if categorized['vrp']:
                logger.info(f"Sample VRP styles ({len(categorized['vrp'].splitlines())} lines):")
                sample_lines = categorized['vrp'].splitlines()[:5]
                for line in sample_lines:
                    logger.info(f"  {line}")
                if len(sample_lines) < len(categorized['vrp'].splitlines()):
                    logger.info("  ...")
            
            if categorized['inside']:
                logger.info(f"Sample Inside styles ({len(categorized['inside'].splitlines())} lines):")
                sample_lines = categorized['inside'].splitlines()[:5]
                for line in sample_lines:
                    logger.info(f"  {line}")
                if len(sample_lines) < len(categorized['inside'].splitlines()):
                    logger.info("  ...")
        
        # Save to test output directory for inspection
        os.makedirs("test-output", exist_ok=True)
        
        with open("test-output/sb-vdp.scss", 'w') as f:
            f.write(categorized['vdp'])
        
        with open("test-output/sb-vrp.scss", 'w') as f:
            f.write(categorized['vrp'])
        
        with open("test-output/sb-inside.scss", 'w') as f:
            f.write(categorized['inside'])
        
        logger.info("Saved categorized styles to test-output/ directory")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing style.scss: {e}")
        return False


def main():
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(
        description="Improved style parser for SBM"
    )
    
    parser.add_argument("slug", help="Dealer theme slug")
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done, without modifying files"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set up logger with appropriate verbosity
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logger(level=log_level)
    
    # Process style.scss
    success = process_style_scss(args.slug, args.dry_run)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
