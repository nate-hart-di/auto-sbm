"""
Tests for SCSS style classification and exclusion system.

This module tests the StyleClassifier's ability to identify and exclude
header, footer, and navigation styles that should not be migrated to
Site Builder to prevent conflicts.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

from sbm.scss.classifiers import StyleClassifier, filter_scss_for_site_builder


class TestStyleClassifier:
    """Test SCSS style classification and exclusion."""

    def test_classifier_initialization(self):
        """Test StyleClassifier initializes correctly."""
        classifier = StyleClassifier(strict_mode=True)
        assert classifier.strict_mode is True
        assert len(classifier.excluded_patterns) > 0
        assert classifier.get_exclusion_stats()["total_processed"] == 0

    def test_header_pattern_exclusion(self):
        """Test that header styles are correctly identified for exclusion."""
        classifier = StyleClassifier()

        # Test cases for header styles that should be excluded
        header_test_cases = [
            ".header { color: red; }",
            "#header { background: blue; }",
            ".main-header .logo { font-size: 2em; }",
            ".site-header nav { display: flex; }",
            ".page-header h1 { margin: 0; }",
            ".top-header .contact { color: white; }",
            ".masthead { height: 100px; }",
            ".banner { width: 100%; }"
        ]

        for css_rule in header_test_cases:
            should_exclude, reason = classifier.should_exclude_rule(css_rule)
            assert should_exclude is True, f"Header rule should be excluded: {css_rule}"
            assert reason == "header", f"Should identify as header rule: {css_rule}"

    def test_navigation_pattern_exclusion(self):
        """Test that navigation styles are correctly identified for exclusion."""
        classifier = StyleClassifier()

        nav_test_cases = [
            ".nav { display: flex; }",
            ".navigation ul { list-style: none; }",
            ".main-nav li { display: inline; }",
            ".navbar { background: #333; }",
            ".menu { position: fixed; }",
            ".primary-menu a { text-decoration: none; }",
            ".main-menu .dropdown { position: absolute; }",
            ".site-nav { z-index: 1000; }",
            ".nav-menu { margin: 0; }",
            ".breadcrumb { font-size: 0.8em; }"
        ]

        for css_rule in nav_test_cases:
            should_exclude, reason = classifier.should_exclude_rule(css_rule)
            assert should_exclude is True, f"Navigation rule should be excluded: {css_rule}"
            assert reason == "navigation", f"Should identify as navigation rule: {css_rule}"

    def test_footer_pattern_exclusion(self):
        """Test that footer styles are correctly identified for exclusion."""
        classifier = StyleClassifier()

        footer_test_cases = [
            ".footer { background: #000; }",
            "#footer { color: white; }",
            ".main-footer .copyright { text-align: center; }",
            ".site-footer { padding: 20px; }",
            ".page-footer { margin-top: 50px; }",
            ".bottom-footer { border-top: 1px solid; }",
            ".footer-content { max-width: 1200px; }"
        ]

        for css_rule in footer_test_cases:
            should_exclude, reason = classifier.should_exclude_rule(css_rule)
            assert should_exclude is True, f"Footer rule should be excluded: {css_rule}"
            assert reason == "footer", f"Should identify as footer rule: {css_rule}"

    def test_content_styles_included(self):
        """Test that content styles are NOT excluded."""
        classifier = StyleClassifier()

        # These should NOT be excluded - they're content styles
        content_test_cases = [
            ".content { padding: 20px; }",
            ".main { max-width: 1200px; }",
            ".article { margin-bottom: 2em; }",
            ".sidebar { width: 300px; }",
            ".widget { background: #f5f5f5; }",
            ".button { padding: 10px 20px; }",
            ".form-field { margin-bottom: 1em; }",
            ".vehicle-card { border: 1px solid #ddd; }",
            ".dealer-info { background: white; }",
            ".contact-form { width: 100%; }"
        ]

        for css_rule in content_test_cases:
            should_exclude, reason = classifier.should_exclude_rule(css_rule)
            assert should_exclude is False, f"Content rule should NOT be excluded: {css_rule}"
            assert reason is None, f"Content rule should have no exclusion reason: {css_rule}"

    def test_scss_content_filtering(self):
        """Test filtering of complete SCSS content."""
        scss_content = """
/* Variables */
$primary-color: #007bff;
$secondary-color: #6c757d;

/* Header styles - should be excluded */
.header {
    background: $primary-color;
    padding: 20px;

    .logo {
        font-size: 2em;
        color: white;
    }
}

/* Navigation styles - should be excluded */
.nav {
    display: flex;
    list-style: none;

    li {
        margin-right: 20px;
    }
}

/* Content styles - should be included */
.content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.vehicle-card {
    border: 1px solid #ddd;
    padding: 15px;
    margin-bottom: 20px;
}

/* Footer styles - should be excluded */
.footer {
    background: #333;
    color: white;
    text-align: center;
    padding: 40px 0;
}
"""

        classifier = StyleClassifier()
        filtered_content, result = classifier.filter_scss_content(scss_content)

        # Check that exclusions were made
        assert result.excluded_count > 0, "Should have excluded some rules"
        assert result.patterns_matched.get("header", 0) > 0, "Should have excluded header styles"
        assert result.patterns_matched.get("navigation", 0) > 0, "Should have excluded navigation styles"
        assert result.patterns_matched.get("footer", 0) > 0, "Should have excluded footer styles"

        # Check that content styles remain
        assert ".content" in filtered_content, "Content styles should remain"
        assert ".vehicle-card" in filtered_content, "Vehicle card styles should remain"
        assert "$primary-color" in filtered_content, "Variables should remain"

        # Check that excluded styles are commented
        assert "EXCLUDED HEADER RULE" in filtered_content, "Should have exclusion comments"
        assert "EXCLUDED FOOTER RULE" in filtered_content, "Should have exclusion comments"

    def test_convenience_function(self):
        """Test the convenience function for filtering."""
        scss_content = """
.header { background: blue; }
.content { padding: 20px; }
.footer { background: black; }
"""

        filtered_content, result = filter_scss_for_site_builder(scss_content)

        assert result.excluded_count == 2, "Should exclude header and footer"
        assert ".content" in filtered_content, "Should keep content styles"
        assert result.patterns_matched.get("header", 0) == 1, "Should match one header rule"
        assert result.patterns_matched.get("footer", 0) == 1, "Should match one footer rule"

    def test_file_analysis(self):
        """Test analyzing an actual SCSS file."""
        scss_content = """
.header { color: red; }
.nav { display: flex; }
.content { padding: 20px; }
.footer { background: #000; }
"""

        # Create a temporary file
        with NamedTemporaryFile(mode="w", suffix=".scss", delete=False) as temp_file:
            temp_file.write(scss_content)
            temp_file.flush()

            classifier = StyleClassifier()
            result = classifier.analyze_file(Path(temp_file.name))

            assert result.excluded_count == 3, "Should find 3 excluded rules (header, nav, footer)"
            assert result.patterns_matched.get("header", 0) == 1
            assert result.patterns_matched.get("navigation", 0) == 1
            assert result.patterns_matched.get("footer", 0) == 1

    def test_empty_content_handling(self):
        """Test handling of empty or whitespace-only content."""
        classifier = StyleClassifier()

        # Test empty content
        filtered, result = classifier.filter_scss_content("")
        assert filtered == ""
        assert result.excluded_count == 0

        # Test whitespace-only content
        filtered, result = classifier.filter_scss_content("   \n  \n   ")
        assert result.excluded_count == 0

    def test_stats_tracking(self):
        """Test that exclusion statistics are tracked correctly."""
        classifier = StyleClassifier()

        # Process some content
        scss_content = """
.header { color: red; }
.nav { display: flex; }
.content { padding: 20px; }
"""

        classifier.filter_scss_content(scss_content)
        stats = classifier.get_exclusion_stats()

        assert stats["header"] == 1
        assert stats["navigation"] == 1
        assert stats["footer"] == 0
        assert stats["total_excluded"] == 2
        assert stats["total_processed"] == 1

        # Reset stats
        classifier.reset_stats()
        stats_after_reset = classifier.get_exclusion_stats()
        assert stats_after_reset["total_excluded"] == 0
        assert stats_after_reset["total_processed"] == 0

    def test_complex_nested_rules(self):
        """Test handling of complex nested SCSS rules."""
        scss_content = """
.header {
    background: blue;

    .logo {
        font-size: 2em;

        img {
            height: 40px;
        }
    }

    .nav {
        display: flex;

        ul {
            list-style: none;

            li {
                display: inline;
            }
        }
    }
}

.content {
    .vehicle-list {
        display: grid;

        .vehicle-card {
            border: 1px solid #ddd;
        }
    }
}
"""

        classifier = StyleClassifier()
        filtered_content, result = classifier.filter_scss_content(scss_content)

        # The entire .header block should be excluded
        assert result.excluded_count > 0, "Should exclude header rules"
        assert ".content" in filtered_content, "Should keep content styles"
        assert ".vehicle-list" in filtered_content, "Should keep nested content styles"


class TestStyleExclusionIntegration:
    """Test integration of style exclusion with the broader system."""

    def test_classifier_with_real_scss_patterns(self):
        """Test classifier with realistic SCSS patterns from actual themes."""
        realistic_scss = """
// Common theme patterns
.site-header {
    position: relative;
    z-index: 1000;

    .header-top {
        background: #f8f9fa;
        padding: 10px 0;

        .contact-info {
            font-size: 0.9em;
        }
    }

    .header-main {
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);

        .logo {
            max-height: 60px;
        }

        .primary-menu {
            display: flex;
            align-items: center;

            li {
                margin: 0 15px;

                a {
                    color: #333;
                    text-decoration: none;
                    font-weight: 500;

                    &:hover {
                        color: #007bff;
                    }
                }

                .dropdown-menu {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    background: white;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                }
            }
        }
    }
}

// Vehicle inventory styles - should be kept
.vehicle-inventory {
    .search-filters {
        background: #f8f9fa;
        padding: 20px;
        margin-bottom: 30px;

        .filter-group {
            margin-bottom: 15px;

            label {
                font-weight: 600;
                margin-bottom: 5px;
                display: block;
            }
        }
    }

    .vehicle-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;

        .vehicle-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            transition: transform 0.2s ease;

            &:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }

            .vehicle-image {
                position: relative;
                height: 200px;
                overflow: hidden;

                img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
            }

            .vehicle-info {
                padding: 15px;

                .vehicle-title {
                    font-size: 1.2em;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #333;
                }

                .vehicle-price {
                    font-size: 1.5em;
                    font-weight: 700;
                    color: #007bff;
                    margin-bottom: 10px;
                }

                .vehicle-details {
                    font-size: 0.9em;
                    color: #666;

                    .detail-item {
                        margin-bottom: 4px;
                    }
                }
            }
        }
    }
}

// Footer styles - should be excluded
.site-footer {
    background: #333;
    color: white;
    margin-top: 60px;

    .footer-main {
        padding: 40px 0;

        .footer-column {
            h4 {
                color: #fff;
                margin-bottom: 15px;
            }

            ul {
                list-style: none;

                li {
                    margin-bottom: 8px;

                    a {
                        color: #ccc;
                        text-decoration: none;

                        &:hover {
                            color: white;
                        }
                    }
                }
            }
        }
    }

    .footer-bottom {
        background: #222;
        padding: 20px 0;
        text-align: center;
        border-top: 1px solid #444;

        .copyright {
            font-size: 0.9em;
            color: #999;
        }
    }
}
"""

        classifier = StyleClassifier()
        filtered_content, result = classifier.filter_scss_content(realistic_scss)

        # Should exclude header and footer sections
        assert result.excluded_count >= 2, "Should exclude header and footer rules"

        # Should keep vehicle inventory styles
        assert ".vehicle-inventory" in filtered_content
        assert ".vehicle-grid" in filtered_content
        assert ".vehicle-card" in filtered_content

        # Should have excluded header and footer
        assert result.patterns_matched.get("header", 0) > 0
        assert result.patterns_matched.get("footer", 0) > 0

        # Check exclusion comments are added
        assert "EXCLUDED HEADER RULE" in filtered_content
        assert "EXCLUDED FOOTER RULE" in filtered_content
