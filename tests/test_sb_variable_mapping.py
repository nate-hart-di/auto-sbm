from sbm.scss.processor import SCSSProcessor


def test_variable_mapping_to_sb_names():
    """Test that Classic variables are correctly mapped to Site Builder equivalents."""
    processor = SCSSProcessor("test-dealer")

    scss_input = """
.btn-secondary { background: $secondary-button-bg; }
.btn-primary { background: $primary-button-bg; }
.btn-cta { background: $cta-button-bg; }
h1 { text-transform: $heading-text-transform; }
"""

    # Access private method for testing purposes
    result = processor._process_scss_variables(scss_input)

    # Check for Site Builder mapped variables
    assert "background: var(--secondarybutton-bg);" in result
    assert "background: var(--primarybutton-bg);" in result
    assert "background: var(--ctabutton-bg);" in result
    assert "text-transform: var(--heading-text-transform);" in result


def test_variable_mapping_skips_missing_complex_parts():
    """Test that complex mappings are skipped if source variables are missing."""
    processor = SCSSProcessor("test-dealer")

    # Missing $button-border
    scss_input = ".btn { border-color: $secondary-button-border-color; }"

    result = processor._process_scss_variables(scss_input)

    assert "border-color: var(--secondary-button-border-color);" in result


def test_variable_mapping_handles_interpolation():
    """Test that variable mappings work even if variables are used elsewhere."""
    processor = SCSSProcessor("test-dealer")

    scss_input = """
$primary: #fff;
$secondary-button-bg: $primary;
.btn { background: $secondary-button-bg; }
"""

    result = processor._process_scss_variables(scss_input)

    assert "background: var(--secondarybutton-bg);" in result
