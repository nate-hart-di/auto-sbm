#!/usr/bin/env python3
"""
SCSS Brace Balancer

This script ensures SCSS files have properly balanced braces by completely
rebuilding the brace structure if needed.
"""

import sys
import os
import re

def fix_braces(file_path):
    """Fix braces in an SCSS file by ensuring proper balance."""
    filename = os.path.basename(file_path)
    print(f"Processing {filename}...")
    
    # Make a backup
    with open(file_path, 'r') as f:
        original_content = f.read()
    
    with open(f"{file_path}.bak", 'w') as f:
        f.write(original_content)
    
    # First check if there are excess closing braces
    open_count = original_content.count('{')
    close_count = original_content.count('}')
    
    print(f"Initial counts: {open_count} opening, {close_count} closing braces")
    
    # If we have too many closing braces, we need a more aggressive approach
    if close_count > open_count:
        # Remove all closing braces that appear at the end of the file without content
        content = re.sub(r'}+\s*$', '', original_content)
        
        # Extract sections and rebuild
        sections = []
        current_section = ""
        brace_level = 0
        
        for char in content:
            current_section += char
            
            if char == '{':
                brace_level += 1
            elif char == '}':
                brace_level -= 1
                
                # If we close a top-level section, store it and start a new one
                if brace_level == 0:
                    sections.append(current_section)
                    current_section = ""
        
        # Add any remaining content as the last section
        if current_section.strip():
            sections.append(current_section)
        
        # Rebuild the file with balanced braces
        new_content = "\n\n".join(sections)
        
        # Final check - make sure braces are balanced
        final_open = new_content.count('{')
        final_close = new_content.count('}')
        
        # If still imbalanced, add missing closing braces
        if final_open > final_close:
            new_content += '\n' + '}' * (final_open - final_close) + '\n'
        
        # Write the fixed content
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print(f"Fixed {filename}: Now has {new_content.count('{')} opening and {new_content.count('}')} closing braces")
    else:
        print(f"No excess closing braces found in {filename}")
    
    return True

def main():
    """Main function handling command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python fix-scss-braces.py file1.scss [file2.scss ...]")
        return 1
    
    success = True
    
    for file_path in sys.argv[1:]:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} not found.")
            success = False
            continue
            
        try:
            fix_braces(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
