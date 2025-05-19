#!/usr/bin/env python3
"""
Test script to verify cookie banner styles are correctly loaded.
"""

import os
from sbm.scss.parser import extract_cookie_disclaimer_styles

def main():
    """Main test function."""
    # Get the cookie banner styles
    styles = extract_cookie_disclaimer_styles()
    
    # Check if the media query is correct
    if '@media ((max-width:' in styles:
        print("ERROR: Double parentheses in media query detected!")
    elif '@media (max-width:' in styles:
        print("SUCCESS: Media query has correct syntax")
    else:
        print("WARNING: Media query not found in cookie banner styles")
    
    # Print a preview of the styles
    print("\nPreview of cookie banner styles:")
    for line in styles.split('\n'):
        if '@media' in line:
            print(f"MEDIA QUERY: {line}")
    
    print("\nFull cookie banner styles:")
    print(styles)

if __name__ == "__main__":
    main() 
