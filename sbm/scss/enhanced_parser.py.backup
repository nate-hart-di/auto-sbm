"""
Enhanced SCSS parser for the SBM tool.

This module provides improved functions for extracting styles from style.scss based on page types.
Includes multi-selector CSS rule handling to properly categorize styles.
"""

import os
import re
from ..utils.logger import logger
from .parser import read_scss_file, clean_scss_content


def extract_section_from_style(content, section_name):
    """
    Extract a section from style.scss based on comment markers.
    
    Args:
        content (str): SCSS content to search in
        section_name (str): Section name to look for in comments (e.g., "HEADER", "NAVIGATION")
        
    Returns:
        str: Extracted section or empty string if not found
    """
    # Pattern to match section headers like "// HEADER" or "//  HEADER" or "// ***** HEADER *****"
    pattern = re.compile(
        r'\/\/\s*[\*]*\s*' + section_name + r'\s*[\*]*.*?\n(.*?)(?:\/\/\s*[\*]*|$)',
        re.DOTALL | re.IGNORECASE
    )
    
    match = pattern.search(content)
    if match:
        return match.group(1).strip()
    
    return ""


def extract_page_specific_styles(content, page_type):
    """
    Extract styles specific to a page type from style.scss.
    
    Args:
        content (str): SCSS content to search in
        page_type (str): Page type ("vdp", "vrp", "inside")
        
    Returns:
        str: Extracted styles specific to the page type
    """
    result = ""
    
    # Set up page-specific patterns
    if page_type == "vdp":
        patterns = [
            r'\.vdp',
            r'\.lightning-vdp',
            r'\.vehicle-details',
            r'\.vehicle-detail',
            r'#vehicle-details',
            r'\.page-template-.*?vdp',
            r'vdp-'
        ]
        # Also look for comments mentioning VDP
        result += extract_section_from_style(content, "VDP")
        
    elif page_type == "vrp":
        patterns = [
            r'\.vrp',
            r'\.srp',
            r'\.vehicle-results',
            r'\.vehicle-listings',
            r'\.vehicle-list',
            r'#vehicle-results',
            r'\.page-template-.*?vrp',
            r'\.page-template-.*?srp',
            r'vrp-',
            r'srp-'
        ]
        # Also look for comments mentioning VRP/SRP
        result += extract_section_from_style(content, "VRP")
        result += extract_section_from_style(content, "SRP")
        
    elif page_type == "inside":
        patterns = [
            r'\.page-template-default',
            r'\.page-template-page',
            r'\.page(?!-template)',
            r'\.entry-content',
            r'\.page-header',
            r'\.breadcrumbs',
            r'\.content-area',
            r'#content',
            r'\.contentcontainer'
        ]
        # Extract common sections that typically go to inside pages
        for section in ["HEADER", "NAVIGATION", "FOOTER", "LAYOUT", "CONTENT"]:
            section_content = extract_section_from_style(content, section)
            if section_content:
                result += f"/* {section} Styles */\n{section_content}\n\n"
    else:
        return ""
    
    # Extract rules matching the patterns
    extracted_styles = ""
    for pattern in patterns:
        # Find all rules that match the pattern
        matches = re.finditer(
            pattern + r'\s*{([^}]*(?:{[^}]*}[^}]*)*)}',
            content,
            re.DOTALL
        )
        
        for match in matches:
            extracted_styles += match.group(0) + "\n\n"
    
    # Add pattern-matched styles
    if extracted_styles:
        result += f"/* Pattern-matched {page_type.upper()} styles */\n{extracted_styles}\n"
        
    # Extract marked styles (ticket numbers or feature markers mentioning the page type)
    ticket_pattern = re.compile(
        r'\/\/\s*(?:start|begin).*?(' + page_type + r'.*?).*?\n(.*?)\/\/\s*(?:end)',
        re.DOTALL | re.IGNORECASE
    )
    
    ticket_matches = ticket_pattern.finditer(content)
    ticket_styles = ""
    
    for match in ticket_matches:
        marker, styles = match.groups()
        ticket_styles += f"/* {marker} */\n{styles}\n\n"
    
    if ticket_styles:
        result += f"/* Marked {page_type.upper()} sections */\n{ticket_styles}\n"
    
    return result.strip()


def analyze_style_scss(theme_dir, use_improved_parser=True):
    """
    Analyze the style.scss file and extract styles for each Site Builder file.
    
    Args:
        theme_dir (str): Path to the dealer theme directory
        use_improved_parser (bool): Whether to use the improved parser for multi-selector rules
        
    Returns:
        dict: Dictionary containing extracted styles for each Site Builder file
    """
    logger.info("Analyzing style.scss for page-specific styles")
    
    # Try to find style.scss in both the root and css directory
    style_path = os.path.join(theme_dir, "style.scss")
    if not os.path.exists(style_path):
        style_path = os.path.join(theme_dir, "css", "style.scss")
        if not os.path.exists(style_path):
            logger.warning("style.scss not found")
            return {}
    
    # Read the file
    style_content = read_scss_file(style_path)
    if not style_content:
        logger.warning("style.scss is empty or could not be read")
        return {}
    
    # Use the improved parser if requested
    if use_improved_parser:
        logger.info("Using improved style parser for multi-selector rules")
        
        # Parse the rules using the improved parser
        rules = parse_style_rules(style_content)
        
        # Count rules by category
        counts = {'vdp': 0, 'vrp': 0, 'inside': 0}
        for rule in rules:
            counts[rule['category']] += 1
        
        logger.info(f"Found {len(rules)} total style rules")
        logger.info(f"  - VDP rules: {counts['vdp']}")
        logger.info(f"  - VRP rules: {counts['vrp']}")
        logger.info(f"  - Inside rules: {counts['inside']}")
        
        # Distribute the rules to the appropriate categories
        categorized = distribute_rules(rules)
        
        # Create the return dictionary in the expected format
        results = {
            "sb-vdp.scss": categorized['vdp'],
            "sb-vrp.scss": categorized['vrp'],
            "sb-inside.scss": categorized['inside']
        }
    else:
        # Use the original implementation for backward compatibility
        logger.info("Using standard style parser")
        
        # Skip import statements
        import_pattern = re.compile(r'^.*?@import.*?$', re.MULTILINE)
        imports = import_pattern.findall(style_content)
        if imports:
            last_import = imports[-1]
            last_import_pos = style_content.rfind(last_import)
            if last_import_pos != -1:
                style_content = style_content[last_import_pos + len(last_import):]
        
        # Extract styles for each page type using the original method
        results = {
            "sb-vdp.scss": extract_page_specific_styles(style_content, "vdp"),
            "sb-vrp.scss": extract_page_specific_styles(style_content, "vrp"),
            "sb-inside.scss": extract_page_specific_styles(style_content, "inside")
        }
    
    # Log the extraction results
    for file_name, styles in results.items():
        line_count = len(styles.splitlines()) if styles else 0
        logger.info(f"Extracted {line_count} lines for {file_name}")
    
    return results


def parse_style_rules(style_content):
    """
    Parse SCSS content into discrete style rules and their categories.
    
    Args:
        style_content (str): Content of style.scss file
        
    Returns:
        list: List of dictionaries with 'rule' and 'category' keys
    """
    # Define patterns for classification
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
    
    # Remove imports to focus on the actual styles
    content_lines = style_content.splitlines()
    non_import_lines = []
    for line in content_lines:
        if not re.match(r'^\s*@import', line):
            non_import_lines.append(line)
    
    content = '\n'.join(non_import_lines)
    
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
        categorized[category] = clean_scss_content(categorized[category])
    
    return categorized
