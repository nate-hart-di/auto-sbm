"""
Tests for SCSS @import removal to ensure it doesn't consume following content.
Regression test for bug where _remove_imports regex was eating indentation.
"""

import pytest
from sbm.scss.processor import SCSSProcessor


def test_import_removal_preserves_indentation():
    r"""
    Test that removing @import statements preserves indentation of following lines.

    Bug: The original regex r"@import\s*['\"]?[^;'\"]+['\"]?(\s*;)?\s*" with
    re.DOTALL flag would consume whitespace after the import, eating indentation
    from the next line.

    Fix: Changed trailing \s* to \n? to only consume one newline, not arbitrary
    whitespace.
    """
    processor = SCSSProcessor("test-slug")

    content = '''@import "toolbar-overlay";
  #side-toolbar {
    top: 230px !important;
  }'''

    result = processor._remove_imports(content)

    # Should preserve the indentation of #side-toolbar
    assert '  #side-toolbar {' in result
    assert 'top: 230px !important' in result

    # Import should be removed
    assert '@import' not in result


def test_import_removal_preserves_blank_lines():
    """
    Test that removing @import removes trailing newlines but preserves content.

    Note: The regex [\r\n]* removes ALL trailing newlines after import.
    This is correct behavior - blank lines after imports are not significant.
    """
    processor = SCSSProcessor("test-slug")

    content = '''@import "file";

#selector {
  color: red;
}'''

    result = processor._remove_imports(content)

    # Import and all trailing newlines removed
    assert '@import' not in result
    # Content should start immediately (no leading newlines from import removal)
    assert result.startswith('#selector') or result.startswith('\n#selector')
    assert '#selector' in result


def test_import_removal_handles_multiple_imports():
    """
    Test that multiple @import statements are all removed correctly.
    """
    processor = SCSSProcessor("test-slug")

    content = '''@import "reset";
@import "variables";
@import "mixins";

.content {
  margin: 0;
}'''

    result = processor._remove_imports(content)

    # All imports should be removed
    assert '@import' not in result

    # Content should be preserved
    assert '.content' in result
    assert 'margin: 0' in result


def test_import_removal_no_trailing_content():
    """
    Test that @import removal works when there's no content after it.
    """
    processor = SCSSProcessor("test-slug")

    content = '@import "file";'
    result = processor._remove_imports(content)

    assert result == ''


def test_import_removal_with_different_quote_styles():
    """
    Test that @import removal handles different quote styles.
    """
    processor = SCSSProcessor("test-slug")

    test_cases = [
        '@import "double-quotes";\n',
        "@import 'single-quotes';\n",
        '@import"no-space";\n',
        '@import url("with-url");\n',
    ]

    for test in test_cases:
        result = processor._remove_imports(test)
        assert '@import' not in result


def test_import_removal_in_comments():
    """
    Test that @import in comments is removed (expected behavior).

    Note: The regex will match @import anywhere, including in comments.
    This is acceptable since commented imports should be removed anyway.
    """
    processor = SCSSProcessor("test-slug")

    content = '''// @import "commented";
.selector {
  color: red;
}'''

    result = processor._remove_imports(content)

    # Import in comment should be removed
    assert '@import' not in result

    # Selector should be preserved (though comment marker '//' remains)
    assert '.selector' in result
    assert 'color: red' in result


def test_import_removal_windows_line_endings():
    """
    CRITICAL: Test that Windows line endings (\\r\\n) after @import are removed.

    This is a real-world scenario - files created on Windows will have \\r\\n.
    The regex removes \\r\\n from the import line, preventing orphaned \\r at start.

    Note: The regex only removes line endings AFTER the @import statement.
    It does NOT convert all line endings in the file (that's not its job).
    """
    processor = SCSSProcessor("test-slug")

    # Simulate Windows file with \\r\\n line endings
    content = '@import "common-styles";\r\n.dealer-header {\r\n  color: var(--primary);\r\n}'

    result = processor._remove_imports(content)

    # Import should be removed
    assert '@import' not in result

    # Selector should be preserved (with its original \\r\\n line endings)
    assert '.dealer-header' in result
    assert 'color: var(--primary)' in result

    # Critical: No orphaned \\r at the START (import removal should be clean)
    # The file's internal \\r\\n line endings are preserved (correct behavior)
    assert not result.startswith('\r')
    assert result.startswith('.dealer-header')


def test_import_removal_without_semicolon():
    """
    CRITICAL: Test imports without semicolons (valid SCSS).

    SCSS allows imports without semicolons in some contexts.
    The regex should handle this gracefully.
    """
    processor = SCSSProcessor("test-slug")

    content = '@import "file"\n.selector { color: red; }'

    result = processor._remove_imports(content)

    # Import should be removed
    assert '@import' not in result

    # Selector should be preserved without extra spaces
    assert result.startswith('.selector') or result.startswith('\n.selector')
    assert 'color: red' in result


def test_import_removal_with_trailing_spaces():
    """
    CRITICAL: Test imports with spaces before newline.

    Handles case: @import "file";   \\n.selector
    Should remove import and trailing spaces but preserve newline.
    """
    processor = SCSSProcessor("test-slug")

    content = '@import "file";   \n  .selector { color: red; }'

    result = processor._remove_imports(content)

    # Import should be removed
    assert '@import' not in result

    # Indentation of selector should be preserved
    assert '  .selector' in result


def test_import_removal_at_eof():
    """
    CRITICAL: Test import at end of file with no trailing newline.

    Edge case: File ends with @import "file"; (no \\n)
    Should remove entire import leaving empty string.
    """
    processor = SCSSProcessor("test-slug")

    content = '@import "file";'

    result = processor._remove_imports(content)

    # Should be completely empty or just whitespace
    assert result.strip() == ''
    assert '@import' not in result


def test_import_removal_mixed_line_endings():
    """
    CRITICAL: Test file with mixed \\n and \\r\\n line endings.

    Real-world scenario: File edited on multiple platforms.
    All imports should be removed regardless of line ending style.
    """
    processor = SCSSProcessor("test-slug")

    # Mix of Unix and Windows line endings
    content = '@import "reset";\n@import "variables";\r\n@import "mixins";\n\n.content { margin: 0; }'

    result = processor._remove_imports(content)

    # All imports should be removed
    assert '@import' not in result

    # No orphaned \\r characters
    assert '\r' not in result

    # Content should be preserved
    assert '.content' in result
    assert 'margin: 0' in result


def test_import_removal_multiple_newlines_after_import():
    """
    Test that multiple newlines after import are all removed.

    Input: @import "file";\\n\\n\\n.selector
    Expected: .selector (all newlines after import removed)
    """
    processor = SCSSProcessor("test-slug")

    content = '@import "file";\n\n\n.selector { color: red; }'

    result = processor._remove_imports(content)

    # Import and ALL trailing newlines should be removed
    assert '@import' not in result
    assert result.startswith('.selector')


def test_import_removal_old_mac_line_endings():
    """
    CRITICAL: Test old Mac line endings (\\r only, pre-OS X).

    While rare, some legacy files may have \\r-only line endings.
    The regex should handle this.
    """
    processor = SCSSProcessor("test-slug")

    content = '@import "file";\r.selector { color: red; }'

    result = processor._remove_imports(content)

    # Import should be removed
    assert '@import' not in result

    # No orphaned \\r
    assert '\r' not in result

    # Selector preserved
    assert '.selector' in result
