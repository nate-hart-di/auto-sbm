#!/usr/bin/env python3
"""
Test script for the enhanced SCSS parser.

This script tests the enhanced SCSS parser with a provided style.scss file.
It analyzes the style.scss content and shows how it would be distributed to
Site Builder files without modifying any files.
"""

import os
import sys
import argparse
from sbm.scss.parser import read_scss_file, analyze_style_scss, clean_scss_content
from sbm.utils.logger import setup_logger

# Set up logger
logger = setup_logger()

def format_section(section, comment=""):
    """
    Format a section of CSS with an optional comment.
    
    Args:
        section (str): CSS section to format
        comment (str): Optional comment to prepend
        
    Returns:
        str: Formatted CSS section
    """
    section = section.strip()
    if not section:
        return ""
    
    if comment:
        return f"// {comment}\n{section}\n"
    
    return f"{section}\n"

def main():
    """
    Main entry point for the test script.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test enhanced SCSS parser with a style.scss file"
    )
    
    parser.add_argument(
        "style_file",
        help="Path to the style.scss file to test"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save the extracted styles to",
        default="."
    )
    
    args = parser.parse_args()
    
    # Check if the file exists
    if not os.path.exists(args.style_file):
        print(f"Error: File not found: {args.style_file}")
        return 1
    
    # Read the style.scss file
    content = read_scss_file(args.style_file)
    if not content:
        print(f"Error: Could not read {args.style_file}")
        return 1
    
    print(f"Analyzing style.scss: {args.style_file}")
    print(f"File size: {len(content.splitlines())} lines")
    
    # Analyze the style.scss content
    categorized_styles = analyze_style_scss(content)
    
    print("\nResults:")
    print(f"  - VDP sections: {len(categorized_styles['vdp'])}")
    print(f"  - VRP sections: {len(categorized_styles['vrp'])}")
    print(f"  - Inside sections: {len(categorized_styles['inside'])}")
    
    # If output directory is specified, save the categorized styles
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Format VDP styles
        vdp_styles = "\n\n".join([
            format_section(section, "VDP specific section")
            for section in categorized_styles["vdp"] if section.strip()
        ])
        
        # Format VRP styles
        vrp_styles = "\n\n".join([
            format_section(section, "VRP specific section")
            for section in categorized_styles["vrp"] if section.strip()
        ])
        
        # Format Inside styles
        inside_styles = "\n\n".join([
            format_section(section, "Inside pages section")
            for section in categorized_styles["inside"] if section.strip()
        ])
        
        # Write to files
        with open(os.path.join(args.output_dir, "sb-vdp.scss"), 'w') as f:
            f.write(vdp_styles)
        
        with open(os.path.join(args.output_dir, "sb-vrp.scss"), 'w') as f:
            f.write(vrp_styles)
        
        with open(os.path.join(args.output_dir, "sb-inside.scss"), 'w') as f:
            f.write(inside_styles)
        
        print(f"\nCategorized styles written to: {args.output_dir}")
        print(f"  - sb-vdp.scss: {len(vdp_styles.splitlines())} lines")
        print(f"  - sb-vrp.scss: {len(vrp_styles.splitlines())} lines")
        print(f"  - sb-inside.scss: {len(inside_styles.splitlines())} lines")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
