import pytest
from sbm.scss.processor import SCSSProcessor


def test_nested_comment_cleanup_bug():
    """
    Test that specific nested/double comment patterns do not cause valid code
    to be orphaned or corrupted.
    """
    processor = SCSSProcessor("test-slug")

    # The problematic input provided by the user
    # Note: The valid code 'fill: var(--primary) !important;' is visibly inside the block
    # if the previous line is uncommented.
    # BUT in this case, the `// // .results` line is commented out.
    # The bug was likely that the regex consumed the `// .results...` but stopped early
    # or mishandled the closing brace, causing the `fill:` line to act as if it were outside.
    #
    # Actually, looking at the user's snippet:
    # // // .results-featured-facets ... {
    # fill: var(--primary) !important;
    # }
    #
    # If the `// // .results... {` line is effectively removed or comment-stripped such that
    # the opening `{` is ignored or removed, then the `fill:` property becomes top-level code,
    # which is invalid SCSS/CSS generally, or if processed, might be preserved while the selector was lost.
    #
    # We want to ensure that if the selector is commented out, the BODY is also treated as commented out
    # or that we don't accidentally "uncomment" the body by removing the comment markers but not the content.

    content = """
// All styles added with di-group-holman-automotive plugin
// // .results-featured-facets .quick-facets-container .facet-link .feature-icon svg {
fill: var(--primary) !important;
}
"""
    # The previous buggy regex was: re.sub(r"//\s*(?://\s*)*\s*\/\*[\s\S]*?\*/", "", content)
    # Wait, the user said "like adding comments to lines that shouldn't be commented out"
    # AND "caused errors during migration".
    #
    # If `fill: ...` is valid code (e.g. inside a mixin or another selector), it should remain.
    # If it was inside the commented out selector, then it is technically orphaned text if the selector line is removed.
    #
    # However, the user said: "comments in SCSS files are being incorrectly handled, leading to partial commenting of code"
    #
    # Let's try to reproduce what happens with the BAD regex first to understand the corruption.
    # But for this test, we just want to assert SANITY.

    processed = processor._clean_comment_blocks(content)

    # If the logic incorrectly comments out the `fill` line, that's bad.
    # If the logic incorrectly uncomments the `fill` line (making it orphaned), that's also bad (but maybe less destructive if it fails compilation).
    # The user said "adding comments to lines that shouldn't be commented out".

    # Let's assume the `fill` line SHOULD remain as is (uncommented) IF it was uncommented in input.
    # In the snippet:
    # // // ... {
    # fill: ...
    # }
    # The `fill` line IS uncommented.
    # So the output should contain `fill: var(--primary) !important;` verbatim.

    assert "fill: var(--primary) !important;" in processed

    # And crucially, we shouldn't see it get commented out or mangled.
    assert "// fill: var(--primary)" not in processed

    # Also check for the specific corruption where `/*` might have been inserted blindly
    assert "/*" not in processed or "*/" in processed  # usage of block comments should be balanced


def test_broken_block_comment_cleanup_safe():
    """
    Test that the regex (if we use one) doesn't consume valid code.
    """
    processor = SCSSProcessor("test-slug")
    content = """
    // Normal comment
    // /* Broken block comment start
    //    that spans lines */
    .valid-selector { color: red; }
    """

    # We want the broken block comment to be gone or safely ignored.
    # We DEFINITELY want to see .valid-selector.

    processed = processor._clean_comment_blocks(content)
    assert ".valid-selector" in processed
    assert "color: red" in processed


def test_fix_commented_selector_blocks_strips_multiple_markers():
    processor = SCSSProcessor("test-slug")
    content = """
// // // .mapRow {
  @media(min-width: 1025px){
    padding: 490px 0px 50px;
  }
}
"""

    processed = processor._fix_commented_selector_blocks(content)
    assert ".mapRow {" in processed
    assert "// .mapRow" not in processed
