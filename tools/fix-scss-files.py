#!/usr/bin/env python3
"""
SCSS File Fixer

This script properly balances braces in SCSS files.
It analyzes the file structure and ensures each opening brace has a corresponding closing brace.
Then it validates the syntax using the validator from site_builder_migration.py.
"""

import sys
import re
import os
import importlib.util

def load_validator():
    """Load the validate_scss_syntax function from site_builder_migration.py."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    migration_script = os.path.join(script_dir, 'site_builder_migration.py')
    
    if not os.path.exists(migration_script):
        print("Error: site_builder_migration.py not found")
        return None
    
    try:
        spec = importlib.util.spec_from_file_location("site_builder_migration", migration_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.validate_scss_syntax
    except Exception as e:
        print(f"Error loading validate_scss_syntax function: {e}")
        return None

def balance_braces(file_path):
    """Balance opening and closing braces in an SCSS file."""
    print(f"Fixing braces in: {os.path.basename(file_path)}")
    
    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Make a backup of the original file
    backup_path = f"{file_path}.bak"
    with open(backup_path, 'w') as f:
        f.write(content)
    
    # Count opening and closing braces
    opening_count = content.count('{')
    closing_count = content.count('}')
    
    print(f"Initial brace count: {opening_count} opening, {closing_count} closing")
    
    # Clean up any extraneous closing braces at the end
    clean_content = re.sub(r'}+\s*$', '', content)
    
    # Now let's properly balance the braces
    # Find all opening and closing braces with their positions
    opening_positions = [m.start() for m in re.finditer(r'{', clean_content)]
    closing_positions = [m.start() for m in re.finditer(r'}', clean_content)]
    
    # Count again after cleanup
    opening_count = len(opening_positions)
    closing_count = len(closing_positions)
    
    print(f"After cleanup: {opening_count} opening, {closing_count} closing")
    
    # Check if we need to add closing braces
    if opening_count > closing_count:
        # Add missing closing braces at the end
        missing = opening_count - closing_count
        print(f"Adding {missing} missing closing braces")
        
        # Find the last non-whitespace character
        last_content_match = re.search(r'[^\s]}*$', clean_content)
        if last_content_match:
            last_pos = last_content_match.end()
        else:
            last_pos = len(clean_content)
        
        # Add the needed closing braces
        final_content = clean_content[:last_pos] + '\n' + '}' * missing + '\n'
    else:
        final_content = clean_content
    
    # Write the fixed content back to the file
    with open(file_path, 'w') as f:
        f.write(final_content)
    
    print(f"File fixed: {os.path.basename(file_path)}")
    return True

def main():
    """Main function to process command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python fix-scss-files.py <scss_file> [<scss_file2> ...]")
        return 1
    
    # Load the validator function from site_builder_migration.py
    validate_scss_syntax = load_validator()
    
    files = sys.argv[1:]
    success = True
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} not found")
            success = False
            continue
        
        if not file_path.endswith('.scss'):
            print(f"Warning: {file_path} doesn't appear to be an SCSS file. Processing anyway.")
        
        try:
            # First balance the braces
            balance_braces(file_path)
            
            # Then run the validator for more comprehensive fixes if available
            if validate_scss_syntax:
                print(f"Running syntax validator on {os.path.basename(file_path)}...")
                validate_scss_syntax(file_path)
            else:
                print("Syntax validator not available, skipping validation step")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
