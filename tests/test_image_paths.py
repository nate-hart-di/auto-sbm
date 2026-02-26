from sbm.scss.processor import SCSSProcessor


def test_double_quoted_relative_paths():
    """Test conversion of double-quoted relative paths"""
    processor = SCSSProcessor("test-theme", exclude_nav_styles=False)

    input_scss = """
    #videoRow {
      background: url("../images/video-bg.jpg") center center no-repeat;
      .gridwrap {
        background: url("../images/gridoverlay.png") repeat 0 0;
      }
    }
    """

    result = processor._convert_image_paths(input_scss)

    assert 'url("/wp-content/themes/DealerInspireDealerTheme/images/video-bg.jpg")' in result
    assert 'url("/wp-content/themes/DealerInspireDealerTheme/images/gridoverlay.png")' in result
    assert "../images/" not in result


def test_single_quoted_relative_paths():
    """Test conversion of single-quoted relative paths"""
    processor = SCSSProcessor("test-theme", exclude_nav_styles=False)

    input_scss = "background: url('../images/bg.jpg');"
    result = processor._convert_image_paths(input_scss)

    assert 'url("/wp-content/themes/DealerInspireDealerTheme/images/bg.jpg")' in result


def test_unquoted_relative_paths():
    """Test conversion of unquoted relative paths"""
    processor = SCSSProcessor("test-theme", exclude_nav_styles=False)

    input_scss = "background: url(../images/bg.jpg);"
    result = processor._convert_image_paths(input_scss)

    assert 'url("/wp-content/themes/DealerInspireDealerTheme/images/bg.jpg")' in result


def test_paths_with_css_properties():
    """Test paths with additional CSS properties are preserved"""
    processor = SCSSProcessor("test-theme", exclude_nav_styles=False)

    input_scss = 'background: url("../images/bg.jpg") center center no-repeat;'
    result = processor._convert_image_paths(input_scss)

    assert "center center no-repeat" in result
    assert 'url("/wp-content/themes/DealerInspireDealerTheme/images/bg.jpg")' in result
