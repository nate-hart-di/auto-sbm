#!/usr/bin/env python3
"""
Test script for the improved style parser integration.

This script tests the improved style parser on a real dealer theme.
"""

import os
import sys
import argparse
from sbm.utils.logger import setup_logger, logger
from sbm.utils.path import get_dealer_theme_dir
from sbm.scss.enhanced_parser import analyze_style_scss, parse_style_rules
from sbm.scss.parser import read_scss_file


def test_improved_parser(slug, compare=False):
    """
    Test the improved style parser on a dealer theme's style.scss file.
    
    Args:
        slug (str): Dealer theme slug
        compare (bool): Whether to compare the improved parser with the legacy parser
        
    Returns:
        bool: True if successful, False otherwise
    """
    theme_dir = get_dealer_theme_dir(slug)
    logger.info(f"Testing improved style parser on {slug}")
    
    # Try to find style.scss in both the root and css directory
    style_path = os.path.join(theme_dir, "style.scss")
    if not os.path.exists(style_path):
        style_path = os.path.join(theme_dir, "css", "style.scss")
        if not os.path.exists(style_path):
            logger.error("style.scss not found")
            return False
    
    # Read the file
    content = read_scss_file(style_path)
    if not content:
        logger.error("style.scss is empty or could not be read")
        return False
    
    # Use the improved parser
    logger.info("Running improved style parser...")
    
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
    
    # Use the analyze_style_scss function with improved parser
    improved_results = analyze_style_scss(theme_dir, use_improved_parser=True)
    
    # Create test output directory
    os.makedirs("test-output", exist_ok=True)
    
    # Save results to test output directory
    for file_name, styles in improved_results.items():
        output_file = os.path.join("test-output", file_name)
        with open(output_file, 'w') as f:
            f.write(styles)
        logger.info(f"Saved {len(styles.splitlines()) if styles else 0} lines to {output_file}")
    
    # Compare with legacy parser if requested
    if compare:
        logger.info("Comparing with legacy parser...")
        legacy_results = analyze_style_scss(theme_dir, use_improved_parser=False)
        
        # Save legacy results for comparison
        for file_name, styles in legacy_results.items():
            output_file = os.path.join("test-output", "legacy-" + file_name)
            with open(output_file, 'w') as f:
                f.write(styles)
            logger.info(f"Saved {len(styles.splitlines()) if styles else 0} lines to {output_file}")
        
        # Compare number of lines
        for file_name in improved_results.keys():
            improved_lines = len(improved_results[file_name].splitlines()) if improved_results[file_name] else 0
            legacy_lines = len(legacy_results[file_name].splitlines()) if legacy_results[file_name] else 0
            
            logger.info(f"{file_name}: Improved: {improved_lines} lines, Legacy: {legacy_lines} lines")
            
            # Calculate line difference
            line_diff = improved_lines - legacy_lines
            if line_diff > 0:
                logger.info(f"  Improved parser extracted {line_diff} MORE lines")
            elif line_diff < 0:
                logger.info(f"  Improved parser extracted {abs(line_diff)} FEWER lines")
            else:
                logger.info(f"  Both parsers extracted the same number of lines")
    
    logger.info("Test completed successfully")
    return True


def main():
    """
    Main entry point for the script.
    """
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Test the improved style parser integration")
    parser.add_argument("slug", help="Dealer theme slug")
    parser.add_argument("--compare", action="store_true", help="Compare with legacy parser")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(level=log_level)
    
    # Run the test
    success = test_improved_parser(args.slug, args.compare)
    
    if not success:
        logger.error("Test failed")
        return 1
    
    logger.info("Test completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
