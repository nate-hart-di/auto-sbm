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
    Test that removing @import preserves intentional blank lines.
    """
    processor = SCSSProcessor("test-slug")

    content = '''@import "file";

#selector {
  color: red;
}'''

    result = processor._remove_imports(content)

    # Should preserve one blank line
    assert '\n\n' in result or result.startswith('\n#selector')
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
