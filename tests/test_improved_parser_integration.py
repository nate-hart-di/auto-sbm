#!/usr/bin/env python3
"""
Test script for the integrated improved style parser.

This script demonstrates how to use the improved style parser for multi-selector rules
that has been integrated into the SBM tool.
"""

import os
import sys
import argparse
from sbm.scss.enhanced_parser import analyze_style_scss, parse_style_rules, distribute_rules
from sbm.scss.parser import read_scss_file
from sbm.utils.logger import setup_logger, logger

def main():
    """
    Main function to test the improved style parser.
    """
    parser = argparse.ArgumentParser(
        description="Test the improved style parser for multi-selector rules"
    )
    
    parser.add_argument("slug", help="Dealer theme slug or path to style.scss file")
    
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use the legacy parser instead of the improved parser"
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
    
    # Check if input is a file or a slug
    if os.path.isfile(args.slug):
        # It's a direct file path
        style_file = args.slug
        logger.info(f"Using file: {style_file}")
        
        # Read the file
        content = read_scss_file(style_file)
        if not content:
            logger.error(f"Could not read {style_file}")
            return 1
        
        # Parse the rules using the improved parser
        rules = parse_style_rules(content)
        
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
        
        # Save to output directory for inspection
        os.makedirs("tests/output", exist_ok=True)
        
        # Write the categorized content to files
        for category, content in categorized.items():
            output_file = f"tests/output/sb-{category}.scss"
            with open(output_file, 'w') as f:
                f.write(content)
            logger.info(f"Saved {category} styles to {output_file}")
        
    else:
        # It's a slug, get the dealer theme directory
        platforms_dir = os.environ.get('DI_WEBSITES_PLATFORM_DIR')
        if not platforms_dir:
            logger.error("DI_WEBSITES_PLATFORM_DIR environment variable not set")
            return 1
        
        theme_dir = os.path.join(platforms_dir, "dealer-themes", args.slug)
        if not os.path.isdir(theme_dir):
            logger.error(f"Dealer theme directory not found: {theme_dir}")
            return 1
        
        # Process the style.scss file using the enhanced parser
        logger.info(f"Processing style.scss for {args.slug}")
        results = analyze_style_scss(theme_dir, use_improved_parser=not args.legacy)
        
        if not results:
            logger.error("No styles were extracted")
            return 1
        
        # Save to output directory for inspection
        os.makedirs("tests/output", exist_ok=True)
        
        # Write the results to files
        for file_name, content in results.items():
            output_file = f"tests/output/{file_name}"
            with open(output_file, 'w') as f:
                f.write(content)
            logger.info(f"Saved {len(content.splitlines())} lines to {output_file}")
    
    logger.info("Test completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
