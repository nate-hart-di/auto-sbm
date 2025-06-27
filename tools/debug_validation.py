#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, '/Users/nathanhart/Desktop/projects/automation/auto-sbm')

from sbm.scss.processor import SCSSProcessor

def debug_validation():
    theme_dir = "/Users/nathanhart/di-websites-platform/dealer-themes/normandinchryslerjeepdodgeramfiat"
    slug = "normandinchryslerjeepdodgeramfiat"
    
    processor = SCSSProcessor(slug)
    results = processor.process_style_scss(theme_dir)
    
    # Write the sb-inside.scss to a temp file and examine it
    inside_content = results.get('sb-inside.scss', '')
    
    if inside_content:
        with open('debug_inside.scss', 'w') as f:
            f.write(inside_content)
        
        print("Generated debug_inside.scss")
        
        # Show lines around 551
        lines = inside_content.splitlines()
        print(f"\nTotal lines: {len(lines)}")
        
        if len(lines) >= 551:
            print("\nLines 545-555:")
            for i in range(544, min(556, len(lines))):
                print(f"{i+1:3d}: {lines[i]}")
        
        # Try validation and show the exact error
        is_valid, error = processor.validate_scss_syntax(inside_content)
        print(f"\nValidation result: {is_valid}")
        if error:
            print(f"Error: {error}")

if __name__ == "__main__":
    debug_validation() 
