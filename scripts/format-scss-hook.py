#!/usr/bin/env python3
"""
Pre-commit hook to format sb-*.scss files using the built-in SCSS formatter.

This ensures all SCSS files are properly formatted before being committed.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path to import sbm modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sbm.scss.formatter import SCSSFormatter


def main() -> int:
    """
    Format all sb-*.scss files passed as arguments.

    Returns:
        0 if all files were already formatted or successfully formatted
        1 if any files needed formatting (prompts user to stage changes)
    """
    if len(sys.argv) < 2:
        print("Usage: format-scss-hook.py <file1.scss> <file2.scss> ...")  # noqa: T201
        return 0

    formatter = SCSSFormatter(indent_size=2, indent_char=" ")
    files_modified = []

    for filepath in sys.argv[1:]:
        path = Path(filepath)

        # Only process sb-*.scss files
        if not path.name.startswith("sb-") or path.suffix != ".scss":
            continue

        if not path.exists():
            print(f"⚠️  File not found: {filepath}")  # noqa: T201
            continue

        try:
            # Read original content
            original_content = path.read_text()

            # Format content
            formatted_content = formatter.format(original_content)

            # Check if formatting changed the file
            if original_content != formatted_content:
                # Write formatted content back
                path.write_text(formatted_content)
                files_modified.append(filepath)
                print(f"✅ Formatted: {filepath}")  # noqa: T201

        except Exception as e:
            print(f"❌ Error formatting {filepath}: {e}")  # noqa: T201
            return 1

    if files_modified:
        print(f"\n🔧 {len(files_modified)} file(s) were formatted.")  # noqa: T201
        print("📝 Please stage the formatted files and commit again:")  # noqa: T201
        for filepath in files_modified:
            print(f"   git add {filepath}")  # noqa: T201
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
