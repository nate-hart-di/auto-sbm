from sbm.scss.processor import SCSSProcessor


def test_variable_mapping_to_sb_names():
    """Test that Classic variables are correctly mapped to Site Builder equivalents."""
    processor = SCSSProcessor("test-dealer")

    scss_input = """
$secondary-button-bg: #ff0000;
$primary-button-bg: #008800;
$cta-button-bg: #00ff00;
$heading-text-transform: uppercase;
$button-border: 2px solid;
$secondary-button-border-color: #0000ff;
$primary-button-border-color: #004400;
"""

    # Access private method for testing purposes
    result = processor._process_scss_variables(scss_input)

    # Check for original CSS custom properties
    assert "--secondary-button-bg: #ff0000;" in result
    assert "--primary-button-bg: #008800;" in result
    assert "--cta-button-bg: #00ff00;" in result
    assert "--heading-text-transform: uppercase;" in result

    # Check for Site Builder mapped variables
    assert "--secondarybutton-bg: var(--secondary-button-bg);" in result
    assert "--primarybutton-bg: var(--primary-button-bg);" in result
    assert "--ctabutton-bg: var(--cta-button-bg);" in result

    # Check for Group Mappings (headings)
    assert "--h1-text-transform: var(--heading-text-transform);" in result
    assert "--h4-text-transform: var(--heading-text-transform);" in result
    assert "--h6-text-transform: var(--heading-text-transform);" in result

    # Check for Complex Mappings (borders)
    assert (
        "--secondarybutton-border: var(--button-border) var(--secondary-button-border-color);"
        in result
    )
    assert (
        "--primarybutton-border: var(--button-border) var(--primary-button-border-color);" in result
    )
    assert "--ctabutton-border: var(--button-border) var(--cta-button-bg);" in result


def test_variable_mapping_skips_missing_complex_parts():
    """Test that complex mappings are skipped if source variables are missing."""
    processor = SCSSProcessor("test-dealer")

    # Missing $button-border
    scss_input = "$secondary-button-border-color: #0000ff;"

    result = processor._process_scss_variables(scss_input)

    assert "--secondarybutton-border:" not in result
    assert "--secondary-button-border-color: #0000ff;" in result


def test_variable_mapping_handles_interpolation():
    """Test that variable mappings work even if variables are used elsewhere."""
    processor = SCSSProcessor("test-dealer")

    scss_input = """
$primary: #fff;
$secondary-button-bg: $primary;
"""

    result = processor._process_scss_variables(scss_input)

    assert "--secondary-button-bg: var(--primary);" in result
    assert "--secondarybutton-bg: var(--secondary-button-bg);" in result
