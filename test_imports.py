import os
import re
from sbm.scss.processor import SCSSProcessor


def test_import_removal():
    processor = SCSSProcessor("test-slug", exclude_nav_styles=True)

    # TestCase 1: Basic import
    content = """
    $var: 1;
    @import 'variables';
    .foo { color: red; }
    """
    processed = processor._remove_imports(content)
    if "@import" in processed:
        print("FAIL: Basic import not removed")
    else:
        print("PASS: Basic import removed")

    # TestCase 2: Import with double quotes
    content = """@import "_variables.scss";"""
    processed = processor._remove_imports(content)
    if "@import" in processed:
        print("FAIL: Double quote import not removed")
    else:
        print("PASS: Double quote import removed")

    # TestCase 3: Import with spaces and newlines
    content = """
    @import 
        "variables"
    ;
    """
    processed = processor._remove_imports(content)
    if "@import" in processed:
        print(f"FAIL: Multiline import not removed: {processed}")
    else:
        print("PASS: Multiline import removed")

    # TestCase 4: Import with no semicolon (Invalid SCSS but might exist?)
    content = """@import "variables" """
    processed = processor._remove_imports(content)
    if "@import" in processed:
        print(
            f"WARN: Import without semicolon NOT removed (Expected behavior for regex requiring semicolon)"
        )
    else:
        print("PASS: Import without semicolon removed")


if __name__ == "__main__":
    test_import_removal()
