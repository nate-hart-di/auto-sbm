#!/usr/bin/env python3
"""
Site Builder Migration Automation Script

This script automates the process of migrating dealer themes to the Site Builder format.
It handles git operations, file creation, and style migrations according to DI specifications.
"""

import os
import sys
import subprocess
import argparse
import re
from datetime import datetime
import shutil
import glob
import threading


def execute_command(command, error_message="Command failed"):
    """
    Execute a shell command and handle errors.
    Show real-time output to the user.
    
    Args:
        command (str): Command to execute
        error_message (str): Message to display on error
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Executing: {command}")
        
        # Use subprocess.run directly with real-time output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Define functions to read from stdout and stderr to prevent deadlocks
        def read_output(pipe, prefix=''):
            for line in iter(pipe.readline, ''):
                print(f"{prefix}{line}", end='')
        
        # Create threads for reading stdout and stderr
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, ''))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, ''))
        
        # Start the threads
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for the command to complete
        exit_code = process.wait()
        
        # Wait for the threads to finish
        stdout_thread.join()
        stderr_thread.join()
        
        if exit_code != 0:
            print(f"ERROR: {error_message} (exit code: {exit_code})")
            return False
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {error_message}")
        print(f"Command output: {e.stderr}")
        return False
    except KeyboardInterrupt:
        print("\nCommand interrupted by user.")
        return False


def validate_slug(slug):
    """
    Validate that the slug contains only allowed characters.
    
    Args:
        slug (str): Dealer theme slug to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not slug:
        print("Error: Slug cannot be empty.")
        return False
    
    if re.search(r'[^a-zA-Z0-9/_-]', slug):
        print("Error: Slug contains invalid characters. Only letters, numbers, dashes, underscores, and slashes are allowed.")
        return False
    
    return True


def git_operations(slug):
    """
    Perform required Git operations: checkout main, pull, create branch.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("\n=== Performing Git Operations ===")
    
    # Navigate to DI websites platform directory
    platform_dir = os.environ.get('DI_WEBSITES_PLATFORM_DIR')
    if not platform_dir:
        print("ERROR: DI_WEBSITES_PLATFORM_DIR environment variable is not set.")
        return False
        
    os.chdir(platform_dir)
    print(f"Changed directory to {platform_dir}")
    
    # Checkout main branch and pull latest changes
    if not execute_command("git checkout main && git pull", 
                          "Failed to checkout or pull main branch"):
        return False
    
    # Create a new branch with dynamic MMYY
    current_date = datetime.now().strftime("%m%y")
    branch_name = f"{slug}-sbm{current_date}"
    
    print(f"Creating a new branch: {branch_name}")
    if not execute_command(f"git checkout -b {branch_name}", 
                          f"Failed to create branch {branch_name}"):
        return False
    
    return True


def run_just_start(slug):
    """
    Run the 'just start' command for the given slug with production database.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n=== Starting Site Build for {slug} with Production Database ===")
    
    # Verify the 'just' command is available
    if not execute_command("which just", "'just' command not found"):
        print("Please install 'just' or ensure it's in your PATH.")
        return False
    
    # Run the 'just start' command with 'prod' parameter to pull production database
    if not execute_command(f"just start {slug} prod", 
                          f"Failed to run 'just start {slug} prod'"):
        return False
    
    return True


def create_sb_files(slug):
    """
    Create necessary Site Builder SCSS files if they don't exist.
    Only creates sb-inside.scss by default, as other files are created only when needed.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n=== Creating Site Builder Files for {slug} ===")
    
    # Define the theme directory
    theme_dir = os.path.join(os.environ.get('DI_WEBSITES_PLATFORM_DIR', ''), 
                            'dealer-themes', slug)
    
    if not os.path.isdir(theme_dir):
        print(f"Error: Directory {theme_dir} does not exist.")
        return False
    
    # Only create sb-inside.scss by default
    sb_files = ['sb-inside.scss']
    
    for file in sb_files:
        file_path = os.path.join(theme_dir, file)
        try:
            # Create file if it doesn't exist
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    # Create empty file without automation script comment
                    f.write("")
                print(f"Created {file}")
            else:
                # Remove automation script comment if it exists
                with open(file_path, 'r') as f:
                    content = f.read()
                content = re.sub(r'// .*Created by SBM automation script.*\n+', '', content)
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"{file} already exists")
        except Exception as e:
            print(f"Error creating {file}: {str(e)}")
            return False
    
    return True


def extract_content_between_comments(content, start_marker, end_marker):
    """
    Extract content between specified comment markers.
    
    Args:
        content (str): File content to search through
        start_marker (str): Start comment marker
        end_marker (str): End comment marker
        
    Returns:
        str: Extracted content or empty string if not found
    """
    pattern = re.compile(f"{start_marker}(.*?){end_marker}", re.DOTALL)
    match = pattern.search(content)
    
    if match:
        return match.group(1).strip()
    
    return ""


def get_cookie_disclaimer_styles():
    """
    Return the cookie disclaimer styles as per documentation.
    
    Returns:
        str: Cookie disclaimer styles
    """
    cookie_styles = """// Cookie Banner
.cookie-banner {
  z-index: 2147483650; // might need to adjust per site - depending on 3rd parties
  bottom: 0; // might need to adjust per site - depending on 3rd parties
  border-top: 2px solid var(--primary);
  position: fixed;
  right: 0;
  left: 0;
  padding: 16px 24px;
  color: #fff; // might need to adjust per site - depending on secondary color
  background-color: var(--secondary);
  
  -webkit-transition: -webkit-transform 200ms cubic-bezier(0.4, 0, 1, 1) 400ms;
  -moz-transition: -moz-transform 200ms cubic-bezier(0.4, 0, 1, 1) 400ms;
  -o-transition: -o-transform 200ms cubic-bezier(0.4, 0, 1, 1) 400ms;
  transition: transform 200ms cubic-bezier(0.4, 0, 1, 1) 400ms;
  -webkit-transform: translate(0, 100%);
  -ms-transform: translate(0, 100%);
  -o-transform: translate(0, 100%);
  transform: translate(0, 100%);
  
  &.on {
    -webkit-transform: translate(0, 0);
    -ms-transform: translate(0, 0);
    -o-transform: translate(0, 0);
    transform: translate(0, 0);
    -webkit-transition: -webkit-transform 200ms cubic-bezier(0, 0, 0.2, 1) 400ms;
    -moz-transition: -moz-transform 200ms cubic-bezier(0, 0, 0.2, 1) 400ms;
    -o-transition: -o-transform 200ms cubic-bezier(0, 0, 0.2, 1) 400ms;
    transition: transform 200ms cubic-bezier(0, 0, 0.2, 1) 400ms;
  }
}"""
    return cookie_styles


def extract_nested_rule(content, selector):
    """
    Extract a CSS rule with all its nested content.
    
    Args:
        content (str): The SCSS content to search
        selector (str): The selector to find
        
    Returns:
        str: The complete rule with nested content, or empty string if not found
    """
    # Find the selector
    start_idx = content.find(selector)
    if start_idx == -1:
        return ""
    
    # Find opening bracket
    open_idx = content.find('{', start_idx)
    if open_idx == -1:
        return ""
    
    # Find matching closing bracket (accounting for nesting)
    bracket_count = 1
    close_idx = open_idx + 1
    while bracket_count > 0 and close_idx < len(content):
        if content[close_idx] == '{':
            bracket_count += 1
        elif content[close_idx] == '}':
            bracket_count -= 1
        close_idx += 1
    
    if bracket_count == 0:
        return content[start_idx:close_idx]
    
    return ""


def migrate_styles(slug):
    """
    Migrate styles from source files to Site Builder files.
    Intelligently identifies and extracts custom styles from SCSS files 
    and moves them to the appropriate sb-*.scss files.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n=== Migrating Styles for {slug} ===")
    
    # Define the theme directory
    theme_dir = os.path.join(os.environ.get('DI_WEBSITES_PLATFORM_DIR', ''), 
                            'dealer-themes', slug)
    
    css_dir = os.path.join(theme_dir, 'css')
    if not os.path.isdir(css_dir):
        print(f"Error: CSS directory {css_dir} does not exist.")
        return False
    
    # Create mapping of source files to target SB files - ALL files need to be reviewed
    source_files = {
        'style.scss': os.path.join(css_dir, 'style.scss'),
        'inside.scss': os.path.join(css_dir, 'inside.scss'),
        'vdp.scss': os.path.join(css_dir, 'vdp.scss'),
        'vrp.scss': os.path.join(css_dir, 'vrp.scss'),
        'lvrp.scss': os.path.join(css_dir, 'lvrp.scss'),
        'lvdp.scss': os.path.join(css_dir, 'lvdp.scss'),
        'home.scss': os.path.join(css_dir, 'home.scss')
    }
    
    # Also check for any additional SCSS files in the css directory
    for file in os.listdir(css_dir):
        if file.endswith('.scss') and not file.startswith('_') and file not in source_files:
            source_files[file] = os.path.join(css_dir, file)
            print(f"Found additional SCSS file: {file}")
    
    # Initialize target files - always create these regardless of whether there's content
    target_files = {
        'sb-inside.scss': os.path.join(theme_dir, 'sb-inside.scss'),
        'sb-vdp.scss': os.path.join(theme_dir, 'sb-vdp.scss'),
        'sb-vrp.scss': os.path.join(theme_dir, 'sb-vrp.scss')
    }
    
    # Create all necessary SB files
    for sb_file, sb_path in target_files.items():
        if not os.path.exists(sb_path):
            with open(sb_path, 'w') as f:
                f.write(f"""/*
\tLoads on Site Builder {sb_file.replace('sb-', '').upper().replace('.SCSS', '')}

\tDocumentation: https://dealerinspire.atlassian.net/wiki/spaces/WDT/pages/498572582/SCSS+Set+Up

\t- After updating you'll need to generate the css in Site Builder settings
\t- You can check if it compiled here:
\t\twp-content > uploads > sb-asset-cache > {sb_file}
*/

""")
            print(f"Created {sb_file}")
        else:
            print(f"{sb_file} already exists")
    
    # Track which files had content migrated
    migrated_files = []
    
    try:
        # Process each source file
        for source_name, source_path in source_files.items():
            if not os.path.exists(source_path):
                continue
                
            print(f"Processing {source_name}...")
            
            with open(source_path, 'r') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                continue
            
            # Determine which target file to use based on the documentation
            target_path = None
            
            # Determine target file based on name or content
            if source_name in ['vdp.scss', 'lvdp.scss'] or re.search(r'(vehicle.*detail|vdp)', source_name, re.IGNORECASE):
                target_path = target_files['sb-vdp.scss']
            elif source_name in ['vrp.scss', 'lvrp.scss'] or re.search(r'(vehicle.*results|vrp|search)', source_name, re.IGNORECASE):
                target_path = target_files['sb-vrp.scss']
            else:
                # Default to sb-inside.scss for other files
                target_path = target_files['sb-inside.scss']
                
                # But check content to see if it contains VDP or VRP specific code
                if re.search(r'(#vehicle-details|\.vdp|#vdp|#similar-vehicles|#vehicle-sidebar)', content):
                    target_path = target_files['sb-vdp.scss']
                elif re.search(r'(#vehicle-results|\.vrp|#vrp|\.vehicle-result|#search-filter)', content):
                    target_path = target_files['sb-vrp.scss']
            
            # Extract custom styles directly - NEVER include imports
            custom_rules = []
            
            # Extract CSS rules with pattern: selector { properties }
            rule_pattern = re.compile(r'([^{@]+)\s*\{\s*([^}]*)\}', re.DOTALL)
            for match in rule_pattern.finditer(content):
                selector = match.group(1).strip()
                properties = match.group(2).strip()
                
                # Skip empty rules
                if not properties:
                    continue
                
                # Skip selectors with imports - NEVER include imports
                if '@import' in selector or '@import' in properties:
                    continue
                
                # Skip rules that don't have any actual CSS properties
                if not re.search(r'[a-z-]+\s*:', properties):
                    continue
                
                # Skip common DealerInspire theme selectors
                common_selectors = [
                    'body', 
                    'html', 
                    '.container', 
                    '.row', 
                    '.di-button',
                    '.navbar .navbar-nav',
                    '.nav-link',
                    '#header',
                    '#footer',
                    '#main-nav',
                    '.footer'
                ]
                if any(s in selector for s in common_selectors) and len(selector.strip()) < 20:
                    # Only skip if it's a simple selector match
                    if not re.search(r'>' , selector):
                        continue
                
                # Get the full nested content for this rule, including any nested blocks
                full_rule = extract_nested_rule(content, selector)
                if full_rule and not any(s in full_rule for s in ['@import ', 'import ']):
                    custom_rules.append(full_rule)
            
            # Also extract media query blocks that contain custom rules
            media_patterns = re.findall(r'(@media[^{]+\{)([^@]*?)(\})', content, re.DOTALL)
            for media_start, media_content, media_end in media_patterns:
                # Skip empty media queries
                if not media_content.strip() or '{' not in media_content:
                    continue
                
                # Skip media queries with imports
                if '@import' in media_content:
                    continue
                
                # Only include media queries with actual CSS properties
                if re.search(r'[a-z-]+\s*:', media_content):
                    # Get the full media query with all nested content
                    media_start_idx = content.find(media_start)
                    if media_start_idx != -1:
                        full_media_query = extract_nested_rule(content, media_start.strip())
                        if full_media_query and not '@import' in full_media_query:
                            custom_rules.append(full_media_query)
            
            # Handle specific cases for each source file type
            if source_name in ['vdp.scss', 'lvdp.scss']:
                # Look for VDP-specific selectors
                vdp_patterns = [
                    r'#vehicle-details',
                    r'\.vdp',
                    r'#vdp',
                    r'#similar-vehicles',
                    r'#vehicle-sidebar',
                    r'#vehicle-features',
                    r'#ctabox',
                    r'#location',
                    r'#ap-offers-modal',
                    r'\.incentives'
                ]
                for pattern in vdp_patterns:
                    rule = extract_nested_rule(content, pattern)
                    if rule and not '@import' in rule:
                        custom_rules.append(rule)
                
            elif source_name in ['vrp.scss', 'lvrp.scss']:
                # Look for VRP-specific selectors
                vrp_patterns = [
                    r'#vehicle-results',
                    r'\.vrp',
                    r'#vrp',
                    r'\.vehicle-result',
                    r'#search-filter',
                    r'#results-wrapper',
                    r'#lvrp',
                    r'\.lvrp',
                    r'#results',
                    r'\.incentives',
                    r'\.hit',
                    r'\.ap-offers',
                    r'#lvrp-results-wrapper',
                    r'\.result-wrap'
                ]
                for pattern in vrp_patterns:
                    rule = extract_nested_rule(content, pattern)
                    if rule and not '@import' in rule:
                        custom_rules.append(rule)
            
            # Look for specific custom sections in well-known files
            if source_name == 'style.scss':
                # In style.scss, focus on comments about custom styles
                custom_sections = re.findall(r'//\s*CUSTOM[^*]+.+?(?=//\s*\*+|$)', content, re.DOTALL | re.IGNORECASE)
                for section in custom_sections:
                    # Skip sections with imports
                    if '@import' in section:
                        continue
                    
                    # Extract rules from the custom section
                    section_rules = re.findall(r'([^{@]+)\s*\{\s*([^}]*?)\}', section, re.DOTALL)
                    for selector, properties in section_rules:
                        if selector.strip() and properties.strip():
                            rule = extract_nested_rule(content, selector.strip())
                            if rule and not '@import' in rule:
                                custom_rules.append(rule)
                
                # Special case for style.scss - look for the hero overlay styles
                if "hero overlay" in content.lower():
                    hero_rule = re.search(r'#main-content[^{]*?hero[^{]*?{[^}]*}', content, re.DOTALL)
                    if hero_rule:
                        rule = extract_nested_rule(content, hero_rule.group().split('{')[0].strip())
                        if rule and not '@import' in rule:
                            custom_rules.append(rule)
            
            # Look for map styles in all files and always add to sb-inside.scss
            map_patterns = [
                r'#mapRow', 
                r'\.map-row',
                r'#map-canvas',
                r'#googleMap',
                r'\.google-map',
                r'#directionsBox',
                r'\.directions-box',
                r'\.map-container'
            ]
            
            map_styles_content = ""
            for pattern in map_patterns:
                # Use extract_nested_rule helper to get complete map rule
                rule = extract_nested_rule(content, pattern)
                if rule and not '@import' in rule and rule not in map_styles_content:
                    map_styles_content += f"\n\n{rule}"
            
            # If map styles were found, add them to sb-inside.scss
            if map_styles_content:
                sb_inside_path = target_files['sb-inside.scss']
                
                # Check if content already exists
                with open(sb_inside_path, 'r') as f:
                    existing_content = f.read()
                
                if f"// Map styles from {source_name}" not in existing_content:
                    with open(sb_inside_path, 'a') as f:
                        f.write(f"\n\n// Map styles from {source_name}\n")
                        f.write(map_styles_content)
                        f.write(f"\n// End of map styles from {source_name}\n")
                    print(f"Added map styles from {source_name} to sb-inside.scss")
            
            # Special case for specific files
            if source_name == 'lvrp.scss':
                special_cases = [
                    '#ap-offers-modal', 
                    '.incentives.incentives-breakdown',
                    '#lvrp-results-wrapper'
                ]
                for case in special_cases:
                    rule = extract_nested_rule(content, case)
                    if rule and not '@import' in rule and rule not in custom_rules:
                        custom_rules.append(rule)
            
            elif source_name == 'lvdp.scss':
                special_cases = [
                    '#location', 
                    '#ap-offers-modal',
                    '.incentives.incentives-breakdown'
                ]
                for case in special_cases:
                    rule = extract_nested_rule(content, case)
                    if rule and not '@import' in rule and rule not in custom_rules:
                        custom_rules.append(rule)
            
            # Consolidate and remove duplicates
            processed_rules = []
            processed_selectors = set()
            
            for rule in custom_rules:
                # Extract the selector
                selector_match = re.match(r'([^{]+)', rule)
                if selector_match:
                    selector = selector_match.group(1).strip()
                    if selector not in processed_selectors:
                        processed_selectors.add(selector)
                        # Ensure all braces are balanced
                        if rule.count('{') == rule.count('}'):
                            processed_rules.append(rule)
                        else:
                            # Fix unbalanced braces
                            fixed_rule = rule
                            if rule.count('{') > rule.count('}'):
                                fixed_rule = rule + ('}' * (rule.count('{') - rule.count('}')))
                            processed_rules.append(fixed_rule)
            
            # If no custom rules were found, skip the file
            if not processed_rules:
                print(f"No custom styles found in {source_name}")
                continue
            
            # Combine processed rules with proper spacing
            processed_content = "\n\n".join(processed_rules)
            
            # Verify final content doesn't contain imports
            if '@import' in processed_content or 'import ' in processed_content:
                # Remove any remaining import statements
                processed_content = re.sub(r'@import\s+[\'"].*?[\'"];', '', processed_content)
                processed_content = re.sub(r'import\s+[\'"].*?[\'"];', '', processed_content)
            
            # If there's content, add it to the target file
            if processed_content:
                # First check if these styles already exist in the target file
                with open(target_path, 'r') as f:
                    existing_content = f.read()
                
                # Check for duplicates by using a simplified version of the content for comparison
                simplified_content = re.sub(r'\s+', ' ', processed_content).strip()
                simplified_existing = re.sub(r'\s+', ' ', existing_content).strip()
                
                if simplified_content not in simplified_existing:
                    with open(target_path, 'a') as f:
                        f.write(f"\n\n// Custom styles from {source_name}\n")
                        f.write(processed_content)
                        f.write(f"\n// End of custom styles from {source_name}\n")
                    print(f"Added custom styles from {source_name} to {os.path.basename(target_path)}")
                    migrated_files.append(source_name)
                else:
                    print(f"Custom styles from {source_name} already exist in {os.path.basename(target_path)}")
                    migrated_files.append(source_name)

        # Check for map styles in functions.php and add to sb-inside.scss
        functions_file = os.path.join(theme_dir, 'functions.php')
        if os.path.exists(functions_file):
            print(f"Checking functions.php for map styles...")
            
            with open(functions_file, 'r') as f:
                content = f.read()
            
            # Look for map shortcodes or includes
            map_patterns = [
                r'add_shortcode\s*\(\s*[\'"]full-map[\'"]',
                r'add_shortcode\s*\(\s*[\'"]map[\'"]',
                r'add_shortcode\s*\(\s*[\'"]google-?map[\'"]',
                r'get_template_part\s*\(\s*[\'"][^\']*map[^\']*[\'"]',
                r'include.*partials.*map',
                r'require.*partials.*map'
            ]
            
            map_found = False
            for pattern in map_patterns:
                if re.search(pattern, content):
                    map_found = True
                    break
            
            if map_found:
                # Add Stellantis directions if needed
                print("Map references found in functions.php, adding map styles to sb-inside.scss")
                
                # Check existing content first
                sb_inside_path = target_files['sb-inside.scss']
                with open(sb_inside_path, 'r') as f:
                    existing_content = f.read()
                
                # Only add if not already there
                if "Map styles from functions.php" not in existing_content:
                    stellantis_dir = os.path.join(os.getcwd(), 'stellantis', 'add-to-sb-inside')
                    map_styles_file = os.path.join(stellantis_dir, 'stellantis-directions-row-styles.scss')
                    
                    if os.path.exists(map_styles_file):
                        with open(map_styles_file, 'r') as f:
                            map_styles = f.read()
                    else:
                        # Default map styles
                        map_styles = """/* MAP ROW **************************************************/
#mapRow {
  position: relative;
  .mapwrap {
    height: 600px;
  }
}
#map-canvas {
  height: 100%;
}
/* DIRECTIONS BOX **************************************************/
#directionsBox {
  padding: 50px 0;
  text-align: left;
  width: 400px;
  position: absolute;
  top: 200px;
  left: 50px;
  background: #fff;
  text-align: left;
  color: #111;
  font-family: "Lato", sans-serif;
  .getdirectionstext {
    display: inline-block;
    font-size: 24px;
    margin: 0;
  }
  .locationtext {
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 20px;
  }
  .address {
    margin-bottom: 20px;
  }
}
@media (max-width: 920px) {
  #mapRow {
    .mapwrap {
      height: 250px;
    }
    #directionsBox {
      width: unset;
      height: 100%;
      top: 0;
      left: 0;
      padding: 20px;
      max-width: 45%;
    }
  }
}"""
            
            if os.path.exists(target_file):
                with open(target_file, 'a') as f:
                    f.write("\n\n// Stellantis Directions Row Styles\n")
                    f.write(stellantis_styles)
                    f.write("\n// End of Stellantis Directions Row Styles\n")
                
                print(f"Added Stellantis directions row styles to sb-inside.scss")
                return True
            else:
                # If sb-inside.scss doesn't exist, create it with the styles
                with open(target_file, 'w') as f:
                    f.write("// sb-inside.scss\n\n")
                    f.write("// Stellantis Directions Row Styles\n")
                    f.write(stellantis_styles)
                    f.write("\n// End of Stellantis Directions Row Styles\n")
                
                print(f"Created sb-inside.scss with Stellantis directions row styles")
                return True
        except Exception as e:
            print(f"Error adding Stellantis directions styles: {str(e)}")
            return False


def migrate_map_partials(slug):
    """
    Dynamically discover and migrate map shortcodes and their associated styles.
    Handles different dealer groups and map implementations.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if map styles were migrated, False otherwise
    """
    print(f"\n=== Discovering and Migrating Map Components for {slug} ===")
    
    # Define paths
    platform_dir = os.environ.get('DI_WEBSITES_PLATFORM_DIR', '')
    theme_dir = os.path.join(platform_dir, 'dealer-themes', slug)
    common_theme_dir = "/Users/nathanhart/code/dealerinspire/dealerinspire-core/dealer-inspire/wp-content/themes/DealerInspireCommonTheme"
    
    # Verify CommonTheme directory exists
    if not os.path.isdir(common_theme_dir):
        print(f"Error: CommonTheme directory not found at {common_theme_dir}")
        print("Map migration will be skipped.")
        return False
    
    print(f"Using CommonTheme directory: {common_theme_dir}")
    
    # Map shortcode patterns to look for
    map_shortcode_patterns = [
        r'add_shortcode\s*\(\s*[\'"]full-map[\'"]',
        r'add_shortcode\s*\(\s*[\'"]map[\'"]',
        r'add_shortcode\s*\(\s*[\'"]google-?map[\'"]',
        r'add_shortcode\s*\(\s*[\'"].*?map.*?[\'"]',  # More general pattern
    ]
    
    # Track what we find
    found_map_shortcodes = []
    map_partial_paths = []
    
    # Step 1: DISCOVERY - Search for map shortcodes in functions.php
    functions_file = os.path.join(theme_dir, 'functions.php')
    print("Searching for map shortcodes in functions.php...")
    
    if os.path.exists(functions_file):
        try:
            with open(functions_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Search for each shortcode pattern
                for pattern in map_shortcode_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # Found a map shortcode, now look for the partial path
                        shortcode_context = content[max(0, match.start() - 300):min(len(content), match.end() + 500)]
                        
                        # Look for include or require statement
                        include_patterns = [
                            r'include\s*\(\s*[\'"](.+?partials/dealer-groups/[^\'")]+)[\'"]',
                            r'require\s*\(\s*[\'"](.+?partials/dealer-groups/[^\'")]+)[\'"]',
                            r'get_template_part\s*\(\s*[\'"](.+?partials/dealer-groups/[^\'")]+)[\'"]',
                            r'locate_template\s*\(\s*[\'"](.+?partials/dealer-groups/[^\'")]+)[\'"]',
                            r'include\s*\(\s*[\'"](.+?map-row-\d+\.php)[\'"]', # More general pattern
                            r'get_template_part\s*\(\s*[\'"]([^\'")]+?map[^\'")]*)[\'"]', # Look for any map-related template part
                            r'get_template_part\s*\(\s*[\'"]([^\'")]+)[\'"],\s*[\'"]([^\'")]+)[\'"]', # get_template_part with two args
                            r'get_template_part\s*\(\s*[\'"]partials/([^\'")]+)[\'"]', # Any partials in get_template_part
                        ]
                        
                        for include_pattern in include_patterns:
                            path_matches = re.finditer(include_pattern, shortcode_context)
                            for path_match in path_matches:
                                partial_path = path_match.group(1)
                                
                                # Normalize path if it uses variables
                                partial_path = re.sub(r'\$[a-zA-Z0-9_]+', '', partial_path)
                                partial_path = re.sub(r'\s*\.\s*', '', partial_path)
                                
                                # Check if this is a template part call with multiple arguments
                                # Example: get_template_part('partials/dealer-groups/bmw', 'map-row-1')
                                template_part_second_arg = None
                                if 'get_template_part' in shortcode_context and match.start() < shortcode_context.find('get_template_part') < match.end() + 500:
                                    second_arg_match = re.search(r'get_template_part\s*\(\s*[\'"][^\'")]+[\'"],\s*[\'"]([^\'")]+)[\'"]', shortcode_context)
                                    if second_arg_match:
                                        template_part_second_arg = second_arg_match.group(1)
                                
                                # If we have a second template part argument, append it to the path
                                if template_part_second_arg:
                                    # For cases like get_template_part('partials/dealer-groups/bmw', 'map-row-1')
                                    # should become partials/dealer-groups/bmw-map-row-1
                                    if not partial_path.endswith('/'):
                                        partial_path += '-'
                                    partial_path += template_part_second_arg
                                
                                # Fix path that's missing the partials/ prefix
                                if partial_path.startswith('dealer-groups/') and not partial_path.startswith('partials/'):
                                    partial_path = 'partials/' + partial_path
                                
                                # Cleanup and normalize path
                                partial_path = partial_path.strip()
                                if partial_path and partial_path not in map_partial_paths:
                                    map_partial_paths.append(partial_path)
                                    found_map_shortcodes.append({
                                        'file': functions_file,
                                        'shortcode_match': match.group(0),
                                        'partial_path': partial_path
                                    })
                                    print(f"  Found map shortcode in functions.php using partial: {partial_path}")
        except Exception as e:
            print(f"  Error reading functions.php: {str(e)}")
    
    # Step 2: Check front-page.php for direct map partial usage
    front_page_file = os.path.join(theme_dir, 'front-page.php')
    print("Checking front-page.php for map partial inclusions...")
    
    if os.path.exists(front_page_file):
        try:
            with open(front_page_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for specific include statements for map partials
                # Make the patterns more specific to only match actual map partials
                map_include_patterns = [
                    r'(?:include|require|get_template_part|locate_template)\s*\(\s*[\'"](.+?map-row[^\'")]+)[\'"]',
                    r'(?:include|require|get_template_part|locate_template)\s*\(\s*[\'"](.+?directions[^\'")]+)[\'"]',
                    r'(?:include|require|get_template_part|locate_template)\s*\(\s*[\'"](.+?location[^\'")]+?map[^\'")]*)[\'"]',
                ]
                
                for pattern in map_include_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        partial_path = match.group(1)
                        
                        # Fix path that's missing the partials/ prefix
                        if partial_path.startswith('dealer-groups/') and not partial_path.startswith('partials/'):
                            partial_path = 'partials/' + partial_path
                        
                        # Cleanup and normalize path
                        partial_path = partial_path.strip()
                        if partial_path and partial_path not in map_partial_paths:
                            map_partial_paths.append(partial_path)
                            print(f"  Found map partial inclusion in front-page.php: {partial_path}")
                
                # Check for get_template_part with two arguments where second argument contains map
                # Example: get_template_part('partials/dealer-groups/bmw', 'map-row-1')
                two_arg_matches = re.finditer(r'get_template_part\s*\(\s*[\'"]([^\'")]+)[\'"],\s*[\'"]([^\'")]+)[\'"]', content)
                for match in two_arg_matches:
                    first_arg = match.group(1)
                    second_arg = match.group(2)
                    
                    # Only include if second argument explicitly mentions maps
                    if re.search(r'map-row|google-?map|directions', second_arg.lower()):
                        partial_path = first_arg
                        
                        # Append the second arg to the path
                        if not partial_path.endswith('/'):
                            partial_path += '-'
                        partial_path += second_arg
                        
                        # Fix path that's missing the partials/ prefix
                        if partial_path.startswith('dealer-groups/') and not partial_path.startswith('partials/'):
                            partial_path = 'partials/' + partial_path
                        
                        if partial_path and partial_path not in map_partial_paths:
                            map_partial_paths.append(partial_path)
                            print(f"  Found map partial inclusion in front-page.php: {partial_path}")
        except Exception as e:
            print(f"  Error reading front-page.php: {str(e)}")
    
    # Step 3: Check for map styles in stylesheets
    print("\nVerifying map styles in stylesheets...")
    
    # Look for map styles in style.scss and home.scss
    css_files = [
        os.path.join(theme_dir, 'css', 'style.scss'),
        os.path.join(theme_dir, 'css', 'home.scss'),
        os.path.join(theme_dir, 'css', 'inside.scss')
    ]
    
    map_style_imports = []
    map_style_patterns = [
        r'@import\s+[\'"].*map.*[\'"]',
        r'#mapRow',
        r'\.map-row',
        r'#map-canvas',
        r'#directionsBox',
        r'\.directions-box',
        r'\.google-map',
    ]
    
    map_styles_found = False
    for css_file in css_files:
        if os.path.exists(css_file):
            try:
                with open(css_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for map style imports
                    import_matches = re.finditer(r'@import\s+[\'"]([^\'"]+map[^\'"]+)[\'"]', content)
                    for match in import_matches:
                        import_path = match.group(1)
                        if import_path not in map_style_imports:
                            map_style_imports.append(import_path)
                            print(f"  Found map style import in {os.path.basename(css_file)}: {import_path}")
                            map_styles_found = True
                    
                    # Look for direct map styles
                    for pattern in map_style_patterns:
                        if re.search(pattern, content):
                            print(f"  Found direct map styles in {os.path.basename(css_file)}")
                            map_styles_found = True
                            break
            except Exception as e:
                print(f"  Error reading {css_file}: {str(e)}")
    
    # If no map partials or styles found, we can skip migration
    if not map_partial_paths and not map_style_imports and not map_styles_found:
        print("No map components found. Skipping map migration.")
        return False
    
    # Step 4: MIGRATE MAP PARTIALS - Only if they're directly referenced
    if map_partial_paths:
        print("\nMigrating referenced map partials...")
        
        for partial_path in map_partial_paths:
            try:
                # Normalize path - ensure it starts with 'partials/'
                if partial_path.startswith('dealer-groups/') and not partial_path.startswith('partials/'):
                    partial_path = 'partials/' + partial_path
                
                # Determine OEM/dealer group from the path
                oem_match = re.search(r'dealer-groups/([^/]+)', partial_path)
                oem_name = oem_match.group(1) if oem_match else "common"
                
                # Source path in CommonTheme
                source_path = os.path.join(common_theme_dir, partial_path)
                
                # Add .php extension if missing, accounting for paths that intentionally exclude it
                # Some shortcodes use partial paths without the .php extension
                php_found = False
                if not source_path.endswith('.php'):
                    source_path_with_php = source_path + '.php'
                    # Check if either path exists (with or without .php)
                    if os.path.exists(source_path_with_php):
                        source_path = source_path_with_php
                        php_found = True
                    elif not os.path.exists(source_path):
                        # Try without the extension for template parts
                        if os.path.exists(os.path.dirname(source_path)):
                            potential_matches = glob.glob(f"{os.path.dirname(source_path)}/*{os.path.basename(source_path)}*.php")
                            if potential_matches:
                                source_path = potential_matches[0]
                                php_found = True
                                print(f"  Found matching file: {source_path}")
                            else:
                                print(f"  No matching files found for {partial_path}")
                else:
                    php_found = True
                
                # Check if source exists after all our attempts
                if not os.path.exists(source_path):
                    print(f"  Warning: Source partial file {source_path} not found. Skipping.")
                    continue
                
                # Check if the file actually contains map-related content before copying
                with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
                    # Look for map-related indicators in the file
                    if not re.search(r'map|location|directions|google.*?map|#map', file_content, re.IGNORECASE):
                        print(f"  Skipping {partial_path} - not a map-related partial")
                        continue
                    
                # Create target directory in DealerTheme if needed
                target_path = os.path.join(theme_dir, os.path.relpath(source_path, common_theme_dir))
                target_dir = os.path.dirname(target_path)
                
                # Create target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)
                
                # Copy the partial file
                shutil.copy2(source_path, target_path)
                print(f"  Copied map partial from: {source_path}")
                print(f"  To: {target_path}")
            except Exception as e:
                print(f"  Error processing map partial {partial_path}: {str(e)}")
    else:
        print("No direct map partial references found. Skipping map partial migration.")
    
    # Step 5: MIGRATE MAP STYLES - Always migrate if found
    map_styles_migrated = False
    if map_styles_found or map_style_imports:
        print("\nMigrating map styles...")
        
        for import_path in map_style_imports:
            try:
                # Extract the relative path from the import
                # Convert paths like ../../DealerInspireCommonTheme/css/dealer-groups/fca/map-row-2
                # to css/dealer-groups/fca/map-row-2.scss or _map-row-2.scss
                
                rel_path = import_path.replace('../../DealerInspireCommonTheme/', '')
                if not rel_path.endswith('.scss'):
                    rel_path += '.scss'
                
                # Check for files with and without leading underscore
                source_css_paths = [
                    os.path.join(common_theme_dir, rel_path),
                    os.path.join(common_theme_dir, os.path.dirname(rel_path), f"_{os.path.basename(rel_path)}")
                ]
                
                source_css_path = None
                for path in source_css_paths:
                    if os.path.exists(path):
                        source_css_path = path
                        break
                
                if not source_css_path:
                    print(f"  Warning: Could not find map style file for import: {import_path}")
                    continue
                
                print(f"  Found associated CSS: {source_css_path}")
                
                # Read the CSS content
                with open(source_css_path, 'r', encoding='utf-8', errors='ignore') as f:
                    css_content = f.read()
                
                # Fix imports and paths in the CSS
                css_content = fix_imports(css_content)
                css_content = replace_relative_paths(css_content, source_css_path)
                css_content = replace_with_variables(css_content)
                
                # Append to sb-inside.scss
                sb_inside_path = os.path.join(theme_dir, 'sb-inside.scss')
                
                # Create if it doesn't exist
                if not os.path.exists(sb_inside_path):
                    with open(sb_inside_path, 'w') as f:
                        f.write("// sb-inside.scss\n\n")
                
                # First check if these map styles already exist in the file
                map_style_already_exists = False
                if os.path.exists(sb_inside_path):
                    with open(sb_inside_path, 'r') as f:
                        existing_content = f.read()
                        # Use a more specific check for duplicate content
                        if f"// Map Styles from {os.path.basename(source_css_path)}" in existing_content:
                            map_style_already_exists = True
                
                if not map_style_already_exists:
                    # Append the styles
                    with open(sb_inside_path, 'a') as f:
                        f.write(f"\n\n// Map Styles from {os.path.basename(source_css_path)}\n")
                        f.write(css_content)
                        f.write("\n// End of Map Styles\n")
                    
                    map_styles_migrated = True
                    print(f"  Added map styles to sb-inside.scss")
                else:
                    print(f"  Map styles from {os.path.basename(source_css_path)} already exist in sb-inside.scss, skipping")
            except Exception as e:
                print(f"  Error processing map style import {import_path}: {str(e)}")
    
    # Step 6: OPTIMIZE - Clean up and complete migration
    print("\nFinalizing map migration...")
    
    # Fix any remaining paths and update variables
    sb_inside_path = os.path.join(theme_dir, 'sb-inside.scss')
    if os.path.exists(sb_inside_path):
        update_mixins_and_variables(sb_inside_path, slug)
        remove_undefined_variables_and_mixins(sb_inside_path)
        print("  Optimized map styles in sb-inside.scss")
    
    print("Map migration completed successfully.")
    return map_styles_migrated


def main():
    """Main function to run the site builder migration process."""
    parser = argparse.ArgumentParser(description='Site Builder Migration Automation')
    parser.add_argument('slugs', nargs='+', help='Dealer theme slug(s) to migrate')
    parser.add_argument('--platform-dir', dest='platform_dir', help='Path to DI Websites Platform directory (overrides DI_WEBSITES_PLATFORM_DIR env var)')
    parser.add_argument('--skip-git', dest='skip_git', action='store_true', help='Skip git operations (useful for testing)')
    parser.add_argument('--skip-just', dest='skip_just', action='store_true', help='Skip just start command (useful for testing)')
    parser.add_argument('--run-just', dest='run_just', action='store_true', help='Run just start command (overrides default behavior)')
    
    args = parser.parse_args()
    
    # Check if platform directory is specified or in environment
    if args.platform_dir:
        os.environ['DI_WEBSITES_PLATFORM_DIR'] = args.platform_dir
    
    platform_dir = os.environ.get('DI_WEBSITES_PLATFORM_DIR')
    if not platform_dir:
        print("ERROR: DI_WEBSITES_PLATFORM_DIR environment variable is not set.")
        print("Please either:")
        print("  1. Set the DI_WEBSITES_PLATFORM_DIR environment variable")
        print("     Example: export DI_WEBSITES_PLATFORM_DIR=/path/to/di-websites-platform")
        print("  2. Use the --platform-dir argument")
        print("     Example: ./site_builder_migration.sh --platform-dir=/path/to/di-websites-platform <slug>")
        sys.exit(1)
    
    # Check if the directory exists
    if not os.path.isdir(platform_dir):
        print(f"ERROR: Directory '{platform_dir}' does not exist.")
        print("Please provide a valid path to your DI Websites Platform directory.")
        sys.exit(1)
    
    # Track successfully migrated slugs
    successful_slugs = []
    
    # Process each slug
    for slug in args.slugs:
        print(f"\n===== Starting Site Builder Migration for {slug} =====")
        
        # Validate slug
        if not validate_slug(slug):
            print(f"Skipping invalid slug: {slug}")
            continue
        
        try:
            # Perform Git operations unless skipped
            if not args.skip_git:
                if not git_operations(slug):
                    print(f"Failed to complete Git operations for {slug}")
                    continue
            else:
                print(f"\n=== Skipping Git operations per user request ===")
            
            # Run just start only if explicitly requested (default is to skip)
            if args.run_just and not args.skip_just:
                if not run_just_start(slug):
                    print(f"Failed to run 'just start' for {slug}")
                    continue
            else:
                print(f"\n=== Skipping 'just start {slug} prod' command ===")
                print(f"Note: Use the helper script start-dealer.sh to start the dealer theme separately")
                print(f"      or use the --run-just flag to run it as part of this script")
            
            # Create SB files
            if not create_sb_files(slug):
                print(f"Failed to create Site Builder files for {slug}")
                continue
            
            # Migrate styles - this will return target_files
            migrate_result = migrate_styles(slug)
            if not migrate_result:
                print(f"Failed to migrate styles for {slug}")
                continue
                
            # Dynamically migrate map components
            map_styles_migrated = migrate_map_partials(slug)
                
            # Add cookie consent styles to sb-inside.scss only
            if not add_consent_styles(slug):
                print(f"Warning: Failed to add cookie consent styles for {slug}")
                # Continue anyway as this is not critical
                
            # Add Stellantis directions if needed - only if no map styles were migrated
            if not map_styles_migrated:
                add_stellantis_directions(slug)
            else:
                print("\nMap styles were already migrated. Skipping Stellantis directions row styles.")
            
            # Clean up undefined variables and mixins for each target file
            # Get the list of target files based on the theme directory
            theme_dir = os.path.join(os.environ.get('DI_WEBSITES_PLATFORM_DIR', ''), 'dealer-themes', slug)
            
            # Check which files exist and clean them up
            possible_files = ['sb-vrp.scss', 'sb-vdp.scss', 'sb-inside.scss']
            for file in possible_files:
                file_path = os.path.join(theme_dir, file)
                if os.path.exists(file_path):
                    if not remove_undefined_variables_and_mixins(file_path):
                        print(f"Warning: Failed to clean up undefined variables and mixins in {file} for {slug}")
            
            print(f"\n===== Site Builder Migration for {slug} completed successfully =====")
            successful_slugs.append(slug)
        
        except KeyboardInterrupt:
            print("\nOperation canceled by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\nUnexpected error during migration of {slug}: {str(e)}")
            print("Please check the logs above for details.")
            continue
    
    print("\nAll migrations completed.")
    
    # Offer to run post-migration for successful slugs
    if successful_slugs:
        print("\n===== Post-Migration Options =====")
        print("The following slugs were successfully migrated:")
        for i, slug in enumerate(successful_slugs, 1):
            print(f"  {i}. {slug}")
        
        print("\nWould you like to run the post-migration workflow for any of these dealers?")
        print("This will commit and push changes, and prepare a PR description.")
        
        try:
            selected = input("Enter the number of the dealer to process (or 0 to skip): ")
            selected = int(selected.strip())
            
            if selected > 0 and selected <= len(successful_slugs):
                selected_slug = successful_slugs[selected-1]
                print(f"\nRunning post-migration workflow for {selected_slug}...")
                
                # Construct path to post-migration script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                post_migration_script = os.path.join(script_dir, "post-migration.sh")
                
                if os.path.exists(post_migration_script):
                    cmd = f"bash '{post_migration_script}' {selected_slug}"
                    print(f"Executing: {cmd}")
                    os.system(cmd)
                else:
                    print(f"Post-migration script not found at {post_migration_script}")
                    print("You can manually run the post-migration steps:")
                    print(f"  git add .")
                    print(f"  git commit -m \"{selected_slug.capitalize()} SBM FE Audit\"")
                    print(f"  git push origin {selected_slug}-sbm{datetime.now().strftime('%m%y')}")
            else:
                print("Skipping post-migration workflow.")
        except (ValueError, KeyboardInterrupt):
            print("No dealer selected. Skipping post-migration workflow.")
    
    return True


# Test function to run directly on a dealer theme without Git operations
def test_direct_migration(slug):
    """Test function to run the migration directly on a dealer theme without Git operations."""
    print(f"\n===== Starting Direct Migration Test for {slug} =====")
    
    # Set path to DI websites platform
    os.environ['DI_WEBSITES_PLATFORM_DIR'] = '/Users/nathanhart/di-websites-platform'
    
    try:
        # Perform Git operations
        if not git_operations(slug):
            print(f"Failed to complete Git operations for {slug}")
            return
            
        # Skip the just start command by default
        print(f"\n=== Skipping 'just start {slug} prod' command ===")
        print(f"Note: Use the helper script start-dealer.sh to start the dealer theme separately")
        print(f"      or use the --run-just flag when running the main script")
        
        # Create SB files
        if not create_sb_files(slug):
            print(f"Failed to create Site Builder files for {slug}")
            return
        
        # Migrate styles
        if not migrate_styles(slug):
            print(f"Failed to migrate styles for {slug}")
            return
            
        # Dynamically migrate map components
        map_styles_migrated = migrate_map_partials(slug)
            
        # Add cookie consent styles to sb-inside.scss only
        if not add_consent_styles(slug):
            print(f"Warning: Failed to add cookie consent styles for {slug}")
        
        # Add Stellantis directions if needed - only if no map styles were migrated
        if not map_styles_migrated:
            add_stellantis_directions(slug)
        else:
            print("\nMap styles were already migrated. Skipping Stellantis directions row styles.")
        
        # Clean up undefined variables and mixins for all created files
        theme_dir = os.path.join(os.environ.get('DI_WEBSITES_PLATFORM_DIR', ''), 'dealer-themes', slug)
        
        # Check which files exist and clean them up
        possible_files = ['sb-vrp.scss', 'sb-vdp.scss', 'sb-inside.scss']
        for file in possible_files:
            file_path = os.path.join(theme_dir, file)
            if os.path.exists(file_path):
                remove_undefined_variables_and_mixins(file_path)
        
        print(f"\n===== Direct Migration Test for {slug} completed successfully =====")
    
        # Offer to run post-migration workflow
        print("\n===== Post-Migration Options =====")
        print(f"Would you like to run the post-migration workflow for {slug}?")
        print("This will commit and push changes, and prepare a PR description.")
        
        try:
            response = input("Enter 'y' to proceed or any other key to skip: ")
            
            if response.lower() == 'y':
                print(f"\nRunning post-migration workflow for {slug}...")
                
                # Construct path to post-migration script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                post_migration_script = os.path.join(script_dir, "post-migration.sh")
                
                if os.path.exists(post_migration_script):
                    cmd = f"bash '{post_migration_script}' {slug}"
                    print(f"Executing: {cmd}")
                    os.system(cmd)
                else:
                    print(f"Post-migration script not found at {post_migration_script}")
                    print("You can manually run the post-migration steps:")
                    print(f"  git add .")
                    print(f"  git commit -m \"{slug.capitalize()} SBM FE Audit\"")
                    print(f"  git push origin {slug}-sbm{datetime.now().strftime('%m%y')}")
            else:
                print("Skipping post-migration workflow.")
        except KeyboardInterrupt:
            print("Skipping post-migration workflow.")
        
    except Exception as e:
        print(f"\nUnexpected error during direct migration test of {slug}: {str(e)}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    # Process command line arguments and run the appropriate function
    import argparse
    
    parser = argparse.ArgumentParser(description='Site Builder Migration Tool')
    parser.add_argument('slugs', nargs='+', help='Dealer theme slug(s) to migrate')
    parser.add_argument('--platform-dir', dest='platform_dir', help='Path to the DI Websites Platform directory')
    parser.add_argument('--skip-just', action='store_true', help='Skip the just start command')
    parser.add_argument('--legacy-parser', action='store_true', help='Use the legacy style parser instead of the improved parser')
    
    args = parser.parse_args()
    
    # Set platform directory from command line if provided
    if args.platform_dir:
        os.environ['DI_WEBSITES_PLATFORM_DIR'] = args.platform_dir
    
    # Set the parser type in the environment for modules to access
    if args.legacy_parser:
        os.environ['USE_LEGACY_PARSER'] = 'true'
    
    # Run migration for each slug
    for slug in args.slugs:
        if args.skip_just:
            # Run direct migration without just start
            test_direct_migration(slug)
        else:
            # Run normal migration with just start
            main(slugs=[slug]) 
