"""
SCSS parser for the SBM tool.

This module provides functions for extracting styles from SCSS files.
"""

import os
import re
from ..utils.logger import logger
from ..utils.helpers import extract_nested_rule, extract_content_between_comments


def read_scss_file(file_path):
    """
    Read an SCSS file and return its content.
    
    Args:
        file_path (str): Path to the SCSS file
        
    Returns:
        str: SCSS file content or empty string if file not found
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return ""
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
            
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""


def extract_content_after_imports(content):
    """
    Extract only the content that comes after the last @import in a file.
    
    Args:
        content (str): SCSS content to process
        
    Returns:
        str: Content after the last @import
    """
    if not content:
        return ""
    
    # Find all @import lines
    import_lines = re.findall(r'^\s*@import.*?;.*?$', content, re.MULTILINE)
    
    if not import_lines:
        return content
    
    # Get the last @import line
    last_import = import_lines[-1]
    
    # Find position of the last @import line
    last_import_pos = content.rfind(last_import)
    
    if last_import_pos == -1:
        return content
    
    # Get everything after the last @import line (including the line break)
    after_imports = content[last_import_pos + len(last_import):]
    
    # Clean up the extracted content
    after_imports = clean_scss_content(after_imports)
    
    return after_imports


def clean_scss_content(content):
    """
    Clean up SCSS content by removing unnecessary comments and whitespace.
    
    Args:
        content (str): SCSS content to clean
        
    Returns:
        str: Cleaned SCSS content
    """
    if not content:
        return ""
    
    # Remove comment blocks about sections/variables
    content = re.sub(r'\/\/\s*\*+[\s\*]*\n\/\/\s*[A-Z\s]+\n\/\/\s*\*+[\s\*]*\n', '', content)
    
    # Remove empty lines at the beginning and end
    content = content.strip()
    
    # Remove consecutive empty lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove incomplete selectors at the end (selectors that end with comma or have no opening brace)
    lines = content.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            cleaned_lines.append(line)
            continue
            
        # Check if this is the last non-empty line
        is_last_content = True
        for j in range(i + 1, len(lines)):
            if lines[j].strip():
                is_last_content = False
                break
        
        # If this is the last line and it looks like an incomplete selector, skip it
        if is_last_content and line_stripped:
            # Check if it's an incomplete selector (ends with comma, no opening brace, looks like CSS selector)
            if (line_stripped.endswith(',') or 
                ('{' not in line_stripped and 
                 not line_stripped.startswith('//') and 
                 not line_stripped.startswith('/*') and
                 not line_stripped.endswith(';') and
                 not line_stripped.endswith('}') and
                 ('.' in line_stripped or '#' in line_stripped or line_stripped.endswith(':')))):
                # This looks like an incomplete selector - skip it
                continue
        
        cleaned_lines.append(line)
    
    # Rejoin and clean up again
    content = '\n'.join(cleaned_lines).strip()
    
    # Remove consecutive empty lines again
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content


def extract_vdp_styles(theme_dir):
    """
    Extract VDP styles from source files.
    
    Args:
        theme_dir (str): Path to the dealer theme directory
        
    Returns:
        str: Extracted VDP styles
    """
    logger.info("Extracting VDP styles")
    
    # Try both vdp.scss and lvdp.scss from css directory
    vdp_content = read_scss_file(os.path.join(theme_dir, "css", "vdp.scss"))
    lvdp_content = read_scss_file(os.path.join(theme_dir, "css", "lvdp.scss"))
    
    # Extract content after imports
    vdp_content = extract_content_after_imports(vdp_content)
    lvdp_content = extract_content_after_imports(lvdp_content)
    
    # Combine content from both files
    combined = ""
    
    if lvdp_content.strip():
        combined += f"/* Styles from lvdp.scss */\n\n{lvdp_content}\n\n"
    
    if vdp_content.strip():
        combined += f"/* Styles from vdp.scss */\n\n{vdp_content}\n\n"
    
    # Also try to extract VDP styles from style.scss
    style_content = read_scss_file(os.path.join(theme_dir, "style.scss"))
    
    if style_content:
        # Extract content after imports first
        style_content = extract_content_after_imports(style_content)
        
        # Look for VDP sections in style.scss
        vdp_section = extract_nested_rule(style_content, ".vdp")
        if vdp_section:
            combined += f"{vdp_section}\n\n"
    
    # Final cleanup
    combined = combined.strip()
    
    return combined


def extract_vrp_styles(theme_dir):
    """
    Extract VRP styles from source files.
    
    Args:
        theme_dir (str): Path to the dealer theme directory
        
    Returns:
        str: Extracted VRP styles
    """
    logger.info("Extracting VRP styles")
    
    # Try both vrp.scss and lvrp.scss from css directory
    vrp_content = read_scss_file(os.path.join(theme_dir, "css", "vrp.scss"))
    lvrp_content = read_scss_file(os.path.join(theme_dir, "css", "lvrp.scss"))
    
    # Extract content after imports
    vrp_content = extract_content_after_imports(vrp_content)
    lvrp_content = extract_content_after_imports(lvrp_content)
    
    # Combine content from both files
    combined = ""
    
    if lvrp_content.strip():
        combined += f"/* Styles from lvrp.scss */\n\n{lvrp_content}\n\n"
    
    if vrp_content.strip():
        combined += f"/* Styles from vrp.scss */\n\n{vrp_content}\n\n"
    
    # Also try to extract VRP styles from style.scss
    style_content = read_scss_file(os.path.join(theme_dir, "style.scss"))
    
    if style_content:
        # Extract content after imports first
        style_content = extract_content_after_imports(style_content)
        
        # Look for VRP sections in style.scss
        vrp_section = extract_nested_rule(style_content, ".vrp")
        if vrp_section:
            combined += f"{vrp_section}\n\n"
    
    # Final cleanup
    combined = combined.strip()
    
    return combined


def extract_inside_styles(theme_dir):
    """
    Extract Inside page styles from source files.
    
    Args:
        theme_dir (str): Path to the dealer theme directory
        
    Returns:
        str: Extracted Inside page styles
    """
    logger.info("Extracting Inside page styles")
    
    # Try inside.scss in both root and css directory
    inside_content = read_scss_file(os.path.join(theme_dir, "css", "inside.scss"))
    if not inside_content:
        inside_content = read_scss_file(os.path.join(theme_dir, "inside.scss"))
    
    # Extract content after imports
    inside_content = extract_content_after_imports(inside_content)
    
    # Start with inside.scss content
    combined = ""
    
    if inside_content.strip():
        combined += f"/* Styles from inside.scss */\n\n{inside_content}\n\n"
    
    # Also try to extract Inside page styles from style.scss
    style_content = read_scss_file(os.path.join(theme_dir, "style.scss"))
    
    if style_content:
        # Extract content after imports first
        style_content = extract_content_after_imports(style_content)
        
        # Look for Inside page sections in style.scss
        inside_section = extract_nested_rule(style_content, ".page-template-default")
        if inside_section:
            combined += f"{inside_section}\n\n"
        
        # Also look for common inside page elements
        for selector in [".entry-content", ".page-header", ".breadcrumbs"]:
            section = extract_nested_rule(style_content, selector)
            if section:
                combined += f"{section}\n\n"
    
    # Final cleanup
    combined = combined.strip()
    
    return combined


def extract_home_styles(theme_dir):
    """
    Extract Home page styles from source files.
    
    Args:
        theme_dir (str): Path to the dealer theme directory
        
    Returns:
        str: Extracted Home page styles
    """
    logger.info("Extracting Home page styles")
    
    # Try home.scss
    home_content = read_scss_file(os.path.join(theme_dir, "home.scss"))
    
    # Start with home.scss content
    combined = ""
    
    if home_content:
        combined += f"/* Styles from home.scss */\n\n{home_content}\n\n"
    
    # Also try to extract Home page styles from style.scss
    style_content = read_scss_file(os.path.join(theme_dir, "style.scss"))
    
    if style_content:
        # Look for Home page sections in style.scss
        home_section = extract_nested_rule(style_content, ".home")
        if home_section:
            combined += f"/* Home page styles from style.scss */\n\n{home_section}\n\n"
        
        # Also look for front page specific elements
        front_page_section = extract_nested_rule(style_content, ".page-template-front-page")
        if front_page_section:
            combined += f"/* Front page styles from style.scss */\n\n{front_page_section}\n\n"
    
    return combined


def extract_cookie_disclaimer_styles():
    """
    Extract cookie disclaimer styles from the stellantis file.
    
    Returns:
        str: Cookie disclaimer styles
    """
    logger.info("Extracting cookie disclaimer styles")
    
    # Get the path to the stellantis cookie banner styles file
    stellantis_styles_file = os.path.join(os.getcwd(), 'stellantis', 'add-to-sb-inside', 'stellantis-cookie-banner-styles.scss')
    
    # Read the file directly
    if os.path.exists(stellantis_styles_file):
        try:
            with open(stellantis_styles_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading stellantis cookie banner styles: {e}")
    
    # Fallback to hardcoded version only if file can't be read
    logger.warning("Using hardcoded cookie banner styles (fallback)")
    return """
//▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
// _Cookie Banner
//▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄

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

  .cookie-banner-container {
    margin: 0 auto;
    padding: 0 12px;
    text-align: center;
    max-width: 1440px;
    justify-content: space-between;
    display: flex;

    .cookie-banner-paragraph {
      text-align: left;

      p {
        margin: 0;
      }
    }
    .cookie-button {
      width: auto;
      flex-shrink: 0;
      margin-left: 25px;
      padding: 0 18px;
      background-color: var(--primary);
      border-color: var(--primary);
      color: #ffffff;

      .fa {
        padding-left: 5px;
      }
    }
  }

  @media (max-width: 767px) {
    .cookie-banner-container {
      display: block;

      .cookie-banner-paragraph {
        text-align: center;
      }
      .cookie-button {
        padding: 8px 18px;
        margin-left: 0;
        margin-top: 15px;
      }
    }
  }
}
"""


def analyze_style_scss(style_scss_content):
    """
    Analyze style.scss content and categorize sections by page type.
    
    Args:
        style_scss_content (str): Content of style.scss file
        
    Returns:
        dict: Categorized styles by page type
    """
    # Initialize a dictionary to hold styles for each category
    categorized_styles = {
        "vdp": [],   # Styles for sb-vdp.scss
        "vrp": [],   # Styles for sb-vrp.scss
        "inside": [] # Styles for sb-inside.scss (default)
    }
    
    # Skip if content is empty
    if not style_scss_content:
        return categorized_styles
    
    # Extract content after imports
    content = extract_content_after_imports(style_scss_content)
    
    # Process the SCSS content section by section
    # First, split by major comment blocks
    sections = re.split(r'(/\*+|\*+/|//+\s*[\-=\*]{3,}|//+\s*[A-Z\s/]{3,}\s*//+\s*[\-=\*]{3,})', content)
    processed_sections = []
    
    current_section = ""
    for section in sections:
        if not section or section.strip() == "":
            continue
            
        # If it's a comment marker, start a new section
        if re.match(r'(/\*+|\*+/|//+\s*[\-=\*]{3,}|//+\s*[A-Z\s/]{3,}\s*//+\s*[\-=\*]{3,})', section):
            if current_section.strip():
                processed_sections.append(current_section)
            current_section = section
        else:
            current_section += section
    
    # Add the last section
    if current_section.strip():
        processed_sections.append(current_section)
    
    # Now process each section individually
    for section in processed_sections:
        # VDP patterns
        vdp_patterns = [
            r'\bvdp\b', 
            r'\blvdp\b', 
            r'\bpage-template-vehicle\b',
            r'\bvehicle-detail\b',
            r'\.page-template-page-lightning\.template-vdp\b'
        ]
        
        # VRP patterns
        vrp_patterns = [
            r'\bvrp\b', 
            r'\blvrp\b', 
            r'\bvehicle-list\b',
            r'\bsrp\b',
            r'\bpage-template-inventory\b',
            r'\.page-template-page-lightning\.template-srp\b'
        ]
        
        # Inside page patterns (common elements that should be in sb-inside.scss)
        inside_patterns = [
            r'\bheader\b',
            r'\bfooter\b',
            r'\bnavigation\b',
            r'\bheader-container\b',
            r'\bfooter-row\b',
            r'\bmenu\b',
            r'\bnavbar\b',
            r'\blogo\b',
            r'\bbreadcrumb\b',
            r'#header\b',
            r'#footer\b',
            r'\.di-stacks\b',
            r'\.cookie-banner\b',
            r'\.message-bar\b',
            r'\.contentcontainer\b',
            r'\.header-right\b'
        ]
        
        # Check VDP patterns first
        if any(re.search(pattern, section, re.IGNORECASE) for pattern in vdp_patterns):
            categorized_styles["vdp"].append(section)
            continue
            
        # Check VRP patterns next
        if any(re.search(pattern, section, re.IGNORECASE) for pattern in vrp_patterns):
            categorized_styles["vrp"].append(section)
            continue
        
        # Check Inside patterns last (more specific than the default)
        if any(re.search(pattern, section, re.IGNORECASE) for pattern in inside_patterns):
            categorized_styles["inside"].append(section)
            continue
            
        # If no specific pattern matched, look at the comment blocks for clues
        if re.search(r'(HEADER|NAVIGATION|FOOTER|LAYOUT|GLOBAL|TABLET|MOBILE)', section, re.IGNORECASE):
            categorized_styles["inside"].append(section)
            continue
            
        # Last check for selectors that are likely to be inside page related
        if re.search(r'(body|html|\*|\#page|\#main|\#content|\#wrapper|\.page|\.entry|\.\btop\b)', section, re.IGNORECASE):
            categorized_styles["inside"].append(section)
            continue
            
        # If still no match, default to inside
        categorized_styles["inside"].append(section)
    
    return categorized_styles


def extract_styles(slug, theme_dir):
    """
    Extract all relevant styles for Site Builder files.
    
    Args:
        slug (str): Dealer theme slug
        theme_dir (str): Path to the dealer theme directory
        
    Returns:
        dict: Dictionary containing extracted styles for each Site Builder file
    """
    logger.info(f"Extracting styles for {slug}")
    
    try:
        # Extract base styles from respective files
        vdp_styles = extract_vdp_styles(theme_dir)
        vrp_styles = extract_vrp_styles(theme_dir)
        inside_styles = extract_inside_styles(theme_dir)
        
        # Look for style.scss in various locations
        style_content = read_scss_file(os.path.join(theme_dir, "css", "style.scss"))
        if not style_content:
            style_content = read_scss_file(os.path.join(theme_dir, "style.scss"))
        
        # If style.scss exists, analyze and categorize its styles
        if style_content:
            logger.info(f"Analyzing {len(style_content.splitlines())} lines from style.scss")
            categorized_styles = analyze_style_scss(style_content)
            
            # Format and append style.scss sections to the appropriate files
            if categorized_styles["vdp"]:
                logger.info(f"Adding {len(categorized_styles['vdp'])} style.scss sections to VDP styles")
                
                # Join all VDP-specific sections from style.scss
                style_scss_vdp = "\n\n".join([
                    f"/* style.scss section */\n{section.strip()}" 
                    for section in categorized_styles["vdp"] if section.strip()
                ])
                
                # Add to existing VDP styles if any exist
                if style_scss_vdp:
                    if vdp_styles:
                        vdp_styles += f"\n\n/* From style.scss */\n{style_scss_vdp}"
                    else:
                        vdp_styles = f"/* Styles from style.scss */\n\n{style_scss_vdp}"
            
            # Do the same for VRP styles
            if categorized_styles["vrp"]:
                logger.info(f"Adding {len(categorized_styles['vrp'])} style.scss sections to VRP styles")
                
                # Join all VRP-specific sections from style.scss
                style_scss_vrp = "\n\n".join([
                    f"/* style.scss section */\n{section.strip()}" 
                    for section in categorized_styles["vrp"] if section.strip()
                ])
                
                # Add to existing VRP styles if any exist
                if style_scss_vrp:
                    if vrp_styles:
                        vrp_styles += f"\n\n/* From style.scss */\n{style_scss_vrp}"
                    else:
                        vrp_styles = f"/* Styles from style.scss */\n\n{style_scss_vrp}"
            
            # And for Inside styles (default)
            if categorized_styles["inside"]:
                logger.info(f"Adding {len(categorized_styles['inside'])} style.scss sections to Inside styles")
                
                # Join all Inside-specific sections from style.scss
                style_scss_inside = "\n\n".join([
                    f"/* style.scss section */\n{section.strip()}" 
                    for section in categorized_styles["inside"] if section.strip()
                ])
                
                # Add to existing Inside styles if any exist
                if style_scss_inside:
                    if inside_styles:
                        inside_styles += f"\n\n/* From style.scss */\n{style_scss_inside}"
                    else:
                        inside_styles = f"/* Styles from style.scss */\n\n{style_scss_inside}"
        
        # Create the final styles dictionary
        styles = {
            "sb-vdp.scss": vdp_styles,
            "sb-vrp.scss": vrp_styles,
            "sb-inside.scss": inside_styles
        }
        
        # Log the number of styles extracted for each file
        for file, content in styles.items():
            if content:
                logger.info(f"Extracted {len(content.splitlines())} lines for {file}")
            else:
                logger.warning(f"No styles extracted for {file}")
        
        return styles
        
    except Exception as e:
        logger.error(f"Error extracting styles: {e}")
        return {}
