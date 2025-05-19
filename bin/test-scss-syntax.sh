#!/bin/bash
# SCSS Syntax Validator
# A simple utility to test SCSS files for syntax errors
# Uses the validator function from site_builder_migration.py

# Check if a file was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <scss-file> [scss-file2 scss-file3 ...]"
  echo "Example: $0 dealer-themes/somedealer/sb-inside.scss"
  exit 1
fi

# Ensure the site_builder_migration.py script exists
if [ ! -f "site_builder_migration.py" ]; then
  echo "Error: site_builder_migration.py not found in current directory"
  echo "Please run this script from the directory containing site_builder_migration.py"
  exit 1
fi

# Process each file provided as an argument
for file in "$@"; do
  if [ ! -f "$file" ]; then
    echo "Error: File $file not found"
    continue
  fi
  
  echo "Testing syntax for: $file"
  echo "Performing pre-check cleanup..."
  
  # Create a temp file
  temp_file=$(mktemp)
  
  # Read the file and remove any excess closing braces at the end
  # This prevents the validator from adding more closing braces on top of existing ones
  content=$(cat "$file")
  filename=$(basename "$file")
  
  # Count braces
  opening_count=$(grep -o "{" "$file" | wc -l)
  closing_count=$(grep -o "}" "$file" | wc -l)
  echo "Current brace count: $opening_count opening, $closing_count closing"
  
  # Remove excess closing braces at the end if any
  if [ $closing_count -gt $opening_count ]; then
    excess=$((closing_count - opening_count))
    echo "Removing $excess excess closing braces from the end"
    
    # Remove excess closing braces at the end
    modified_content=$(echo "$content" | sed -E "s/}+\s*$//")
    echo "$modified_content" > "$temp_file"
    
    # Backup the original file
    cp "$file" "${file}.bak"
    
    # Replace with the cleaned version
    cp "$temp_file" "$file"
    
    echo "File cleaned, now running validator..."
  fi
  
  # Run the validator function through Python
  python3 -c "from site_builder_migration import validate_scss_syntax; validate_scss_syntax('$file')"
  
  # Clean up temp file
  rm -f "$temp_file"
  
  echo "----------------------------------------"
done

echo "Syntax testing complete." 
