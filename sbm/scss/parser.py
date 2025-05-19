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
        styles = {
            "sb-vdp.scss": extract_vdp_styles(theme_dir),
            "sb-vrp.scss": extract_vrp_styles(theme_dir),
            "sb-inside.scss": extract_inside_styles(theme_dir)
        }
        
        # Log the number of styles extracted for each file
        for file, content in styles.items():
            logger.info(f"Extracted {len(content.splitlines())} lines for {file}")
        
        return styles
        
    except Exception as e:
        logger.error(f"Error extracting styles: {e}")
        return {} 
