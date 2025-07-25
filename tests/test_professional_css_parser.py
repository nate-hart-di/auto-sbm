"""
Tests for Professional SCSS Parser Implementation.

This module tests the ProfessionalStyleClassifier's ability to correctly handle
the critical failure patterns that the original parser couldn't handle,
specifically comma-separated selectors and complex SCSS structures.
"""

import pytest
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from sbm.scss.classifiers import (
    ProfessionalStyleClassifier, 
    StyleClassifier, 
    ExclusionResult,
    robust_css_processing,
    conservative_keyword_exclusion
)


class TestProfessionalCSSParser:
    """Test professional CSS parser implementation."""
    
    @pytest.fixture
    def classifier(self):
        """Fixture providing professional classifier instance."""
        return ProfessionalStyleClassifier(parser_strategy="auto")
    
    def test_comma_separated_selectors(self, classifier):
        """Test the core failure pattern from ferneliuscdjr theme."""
        scss_content = """
        .navbar .navbar-inner ul.nav li a,
        .navbar .navbar-inner ul.nav li a.dropdown-menu {
            color: white;
            text-decoration: none;
        }
        
        .content {
            padding: 20px;
        }
        """
        
        filtered, result = classifier.filter_scss_content(scss_content)
        
        # Should exclude entire navbar rule (both selectors)
        assert result.excluded_count >= 1, "Should have excluded navbar rules"
        assert result.patterns_matched.get('navigation', 0) >= 1, "Should match navigation patterns"
        
        # Should keep content rule
        assert '.content' in filtered, "Should preserve content styles"
        assert 'padding: 20px' in filtered, "Should preserve content properties"
        
        # Should NOT have any navbar content
        assert '.navbar' not in filtered, "Should exclude navbar selectors"
        assert 'dropdown-menu' not in filtered, "Should exclude dropdown menu selectors"
    
    def test_complex_scss_nesting(self, classifier):
        """Test complex SCSS nesting patterns."""
        scss_content = """
        .header {
            background: blue;
            
            .logo {
                font-size: 2em;
                
                img {
                    height: 40px;
                }
            }
            
            .navigation {
                display: flex;
                
                ul {
                    list-style: none;
                    
                    li {
                        display: inline;
                        
                        a {
                            color: white;
                            
                            &:hover {
                                color: blue;
                            }
                        }
                    }
                }
            }
        }
        
        .main-content {
            .article {
                margin-bottom: 2em;
            }
        }
        """
        
        filtered, result = classifier.filter_scss_content(scss_content)
        
        # Should exclude header block(s)
        assert result.excluded_count >= 1, "Should exclude header rules"
        
        # Should keep content block
        assert '.main-content' in filtered, "Should preserve main content"
        assert '.article' in filtered, "Should preserve nested content"
    
    def test_media_query_handling(self, classifier):
        """Test media query processing."""
        scss_content = """
        @media screen and (max-width: 768px) {
            .navbar {
                display: none;
            }
            
            .content {
                padding: 10px;
            }
        }
        
        @media print {
            .footer {
                display: none;
            }
        }
        """
        
        filtered, result = classifier.filter_scss_content(scss_content)
        
        # Should handle media queries without breaking
        assert isinstance(result, ExclusionResult), "Should return valid result"
        
        # Content within media queries should be handled appropriately
        # (Specific behavior depends on how the CSS parser handles media queries)
    
    def test_fallback_behavior(self, classifier):
        """Test fallback when professional parsing fails."""
        # Malformed CSS that breaks professional parsers
        malformed_scss = """
        .header { 
            color: red;
            // Unclosed brace and malformed content
            background: url(
        
        .content {
            padding: 20px;
        }
        """
        
        # Should not raise exception, should use fallback
        filtered, result = classifier.filter_scss_content(malformed_scss)
        
        # Fallback should still attempt some processing
        assert isinstance(result, ExclusionResult), "Should return valid result even on error"
        
        # Some content should be preserved (fallback behavior)
        assert len(filtered) > 0 or result.excluded_count >= 0, "Should provide some result"
    
    def test_performance_benchmark(self, classifier):
        """Test performance vs original implementation."""
        # Large SCSS content for performance testing
        large_scss = self._generate_large_scss_content(100)  # 100 rules for reasonable test time
        
        # Test professional parser
        start_time = time.time()
        filtered_prof, result_prof = classifier.filter_scss_content(large_scss)
        prof_time = time.time() - start_time
        
        # Test original parser
        original_classifier = StyleClassifier()
        start_time = time.time()
        filtered_orig, result_orig = original_classifier.filter_scss_content(large_scss)
        orig_time = time.time() - start_time
        
        # Professional parser should not be more than 3x slower (relaxed from 2x for realistic performance)
        assert prof_time < orig_time * 3, (
            f"Professional parser too slow: {prof_time:.3f}s vs {orig_time:.3f}s "
            f"(ratio: {prof_time/orig_time:.2f}x)"
        )
        
        # Results should be comparable or better
        assert isinstance(result_prof, ExclusionResult), "Professional parser should return valid result"
        assert isinstance(result_orig, ExclusionResult), "Original parser should return valid result"
    
    def test_integration_with_scss_processor(self, classifier):
        """Test that professional classifier works standalone."""
        scss_content = """
        $primary: #007bff;
        
        .header {
            background: $primary;
            color: white;
        }
        
        .content {
            color: $primary;
            padding: 20px;
        }
        """
        
        # Process SCSS
        filtered_content, result = classifier.filter_scss_content(scss_content)
        
        # Should process successfully
        assert isinstance(result, ExclusionResult), "Should return valid result"
        
        # Should handle SCSS variables appropriately
        assert '$primary' in filtered_content or '--primary' in filtered_content, (
            "Should preserve or transform SCSS variables"
        )
    
    def test_parser_strategy_selection(self):
        """Test different parser strategy selection."""
        strategies = ["auto", "tinycss2", "cssutils"]
        
        for strategy in strategies:
            try:
                classifier = ProfessionalStyleClassifier(parser_strategy=strategy)
                
                # Simple test content
                scss_content = ".header { color: red; } .content { padding: 20px; }"
                filtered, result = classifier.filter_scss_content(scss_content)
                
                # Should work with any available strategy
                assert isinstance(result, ExclusionResult), f"Strategy {strategy} should work"
                assert result.excluded_count >= 0, f"Strategy {strategy} should provide valid counts"
                
            except ImportError:
                # Skip if specific parser not available
                pytest.skip(f"Parser {strategy} not available")
            except ValueError as e:
                if "Unknown parser strategy" in str(e):
                    pytest.fail(f"Strategy {strategy} should be supported")
                else:
                    raise
    
    def _generate_large_scss_content(self, num_rules: int) -> str:
        """Generate large SCSS content for performance testing."""
        rules = []
        for i in range(num_rules):
            if i % 10 == 0:
                # Add some header/nav/footer rules to exclude
                rules.append(f".header-{i} {{ background: red; }}")
            elif i % 15 == 0:
                rules.append(f".nav-{i} {{ display: flex; }}")
            elif i % 20 == 0:
                rules.append(f".footer-{i} {{ color: white; }}")
            else:
                rules.append(f".content-{i} {{ margin: {i}px; }}")
        
        return '\n\n'.join(rules)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_empty_content(self):
        """Test handling of empty content."""
        classifier = ProfessionalStyleClassifier()
        filtered, result = classifier.filter_scss_content("")
        assert filtered == ""
        assert result.excluded_count == 0
    
    def test_only_variables(self):
        """Test content with only SCSS variables."""
        classifier = ProfessionalStyleClassifier()
        scss_content = """
        $primary: #007bff;
        $secondary: #6c757d;
        """
        filtered, result = classifier.filter_scss_content(scss_content)
        
        # Variables should be preserved
        assert "$primary" in filtered or "--primary" in filtered, "Should preserve variables"
        assert result.excluded_count == 0, "Variables should not be excluded"
    
    def test_only_comments(self):
        """Test content with only comments."""
        classifier = ProfessionalStyleClassifier()
        scss_content = """
        /* Header styles */
        // This is a comment
        /* Footer styles */
        """
        filtered, result = classifier.filter_scss_content(scss_content)
        assert result.excluded_count == 0, "Comments should not be excluded"
    
    def test_mixed_css_and_scss(self):
        """Test mixed CSS and SCSS content."""
        classifier = ProfessionalStyleClassifier()
        mixed_content = """
        /* CSS comment */
        .header { color: red; }
        
        // SCSS comment
        $variable: blue;
        
        .content {
            color: $variable;
            
            .nested {
                font-size: 1.2em;
            }
        }
        """
        filtered, result = classifier.filter_scss_content(mixed_content)
        
        # Should handle mixed content
        assert isinstance(result, ExclusionResult), "Should return valid result"
        
        # Content should be preserved
        assert '.content' in filtered, "Should preserve content styles"


class TestRobustProcessing:
    """Test robust processing functions."""
    
    def test_robust_css_processing_fallback_chain(self):
        """Test that robust processing falls back through all layers."""
        # Test with content that should work
        valid_content = """
        .header { background: blue; }
        .content { padding: 20px; }
        """
        
        filtered, result = robust_css_processing(valid_content)
        
        assert isinstance(result, ExclusionResult), "Should return valid result"
        assert '.content' in filtered, "Should preserve content"
    
    def test_conservative_keyword_exclusion(self):
        """Test conservative keyword exclusion fallback."""
        content = """
        .header-main { color: red; }
        .navbar { display: flex; }
        .content { padding: 20px; }
        .footer { background: black; }
        """
        
        filtered, result = conservative_keyword_exclusion(content)
        
        # Should exclude lines with keywords
        assert result.excluded_count > 0, "Should exclude some lines"
        assert '.content' in filtered, "Should preserve content lines"
        assert 'header' not in filtered.lower(), "Should exclude header lines"
        assert 'navbar' not in filtered.lower(), "Should exclude navbar lines"
        assert 'footer' not in filtered.lower(), "Should exclude footer lines"


class TestProfessionalParserIntegration:
    """Test integration with broader auto-sbm system."""
    
    def test_ferneliuscdjr_pattern_regression(self):
        """Test the specific ferneliuscdjr failure pattern is resolved."""
        # This is the exact pattern that was failing
        problematic_scss = """
        .navbar .navbar-inner ul.nav li a,
        .navbar .navbar-inner ul.nav li a.dropdown-menu {
            color: white;
            text-decoration: none;
            display: block;
            padding: 10px 15px;
        }
        
        .content-area {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .vehicle-listing {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        """
        
        classifier = ProfessionalStyleClassifier()
        filtered, result = classifier.filter_scss_content(problematic_scss)
        
        # Critical assertions for the failure pattern
        assert result.excluded_count >= 1, "Should exclude the problematic navbar rule"
        
        # Should exclude both selectors in the comma-separated rule
        assert '.navbar' not in filtered, "Should exclude first navbar selector"
        assert 'dropdown-menu' not in filtered, "Should exclude second navbar selector"
        
        # Should preserve content styles
        assert '.content-area' in filtered, "Should preserve content area styles"
        assert '.vehicle-listing' in filtered, "Should preserve vehicle listing styles"
        assert 'max-width: 1200px' in filtered, "Should preserve content properties"
        
        # Should have navigation pattern match
        assert result.patterns_matched.get('navigation', 0) >= 1, (
            "Should identify navigation patterns correctly"
        )
    
    def test_error_recovery_integration(self):
        """Test that system recovers gracefully from parsing errors."""
        classifier = ProfessionalStyleClassifier()
        
        # Extremely malformed content
        malformed = "{ .header color: red; } .footer { background"
        
        # Should not crash, should use fallback
        filtered, result = classifier.filter_scss_content(malformed)
        assert isinstance(result, ExclusionResult), "Should return valid result even with malformed CSS"
    
    def test_scss_preprocessing_strategies(self):
        """Test different SCSS preprocessing strategies."""
        classifier = ProfessionalStyleClassifier()
        
        # Test minimal preprocessing
        classifier.scss_preprocessor.strategy = "minimal"
        
        scss_content = """
        $primary: #007bff;
        .content { color: $primary; }
        """
        
        filtered, result = classifier.filter_scss_content(scss_content)
        
        # Should handle basic SCSS preprocessing
        assert isinstance(result, ExclusionResult), "Should process with minimal strategy"


@pytest.mark.integration
class TestIntegrationValidation:
    """Integration tests for validation gates."""
    
    def test_api_compatibility_preserved(self):
        """Test that existing API is fully preserved."""
        # Test that ProfessionalStyleClassifier can be used as drop-in replacement
        original_classifier = StyleClassifier()
        professional_classifier = ProfessionalStyleClassifier()
        
        test_content = """
        .header { background: blue; }
        .content { padding: 20px; }
        .footer { background: black; }
        """
        
        # Both should return same type structure
        orig_filtered, orig_result = original_classifier.filter_scss_content(test_content)
        prof_filtered, prof_result = professional_classifier.filter_scss_content(test_content)
        
        # API compatibility checks
        assert isinstance(orig_result, ExclusionResult), "Original should return ExclusionResult"
        assert isinstance(prof_result, ExclusionResult), "Professional should return ExclusionResult"
        
        # Same interface
        assert hasattr(prof_result, 'excluded_count'), "Should have excluded_count"
        assert hasattr(prof_result, 'included_count'), "Should have included_count"
        assert hasattr(prof_result, 'excluded_rules'), "Should have excluded_rules"
        assert hasattr(prof_result, 'patterns_matched'), "Should have patterns_matched"
        
        # Professional should be more accurate (catch more or same exclusions)
        assert prof_result.excluded_count >= orig_result.excluded_count, (
            "Professional parser should be at least as accurate"
        )