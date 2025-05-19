#!/usr/bin/env python3
"""
SCSS File Reset

This script forcefully resets SCSS files by removing excess closing braces 
and then adding the correct number to balance the file.
"""

import sys
import os
import re

def reset_braces(file_path):
    """Reset braces in an SCSS file."""
    print(f"Resetting {os.path.basename(file_path)}...")
    
    # Read the content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create a backup
    with open(f"{file_path}.bak", 'w') as f:
        f.write(content)
    
    # Count braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    print(f"Initial counts: {open_braces} opening, {close_braces} closing")
    
    # Remove all trailing braces and excess whitespace at the end
    cleaned = re.sub(r'[}\s]+$', '', content)
    
    # Now add exactly the right number of closing braces
    new_open = cleaned.count('{')
    new_close = cleaned.count('}')
    missing = new_open - new_close
    
    if missing > 0:
        fixed = cleaned + '\n\n' + '}'.join([''] * (missing + 1))
    else:
        fixed = cleaned
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(fixed)
    
    # Verify
    final_open = fixed.count('{')
    final_close = fixed.count('}')
    print(f"Final counts: {final_open} opening, {final_close} closing")
    
    return True

def main():
    """Main function to process files."""
    if len(sys.argv) < 2:
        print("Usage: python reset-scss-files.py file1.scss [file2.scss ...]")
        return 1
    
    success = True
    for file_path in sys.argv[1:]:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} not found")
            success = False
            continue
        
        try:
            reset_braces(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
