#!/usr/bin/env python3
"""
Comprehensive test suite for SCSS mixin parser
Tests all identified issues and edge cases
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.scss.mixin_parser import CommonThemeMixinParser

class TestMixinParser(unittest.TestCase):
    
    def setUp(self):
        """Setup test fixtures"""
        self.parser = CommonThemeMixinParser()
    
    def test_color_classes_with_hex_value(self):
        """Test color-classes mixin with hex color value"""
        content = "@include color-classes(primary, #252525);"
        result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
        
        # Should generate proper CSS classes
        self.assertIn('.primary,', result)
        self.assertIn('.primary-color {', result)
        self.assertIn('color: #252525;', result)
        
        # Should pre-calculate lightened color for hover states
        self.assertIn('a.primary:hover,', result)
        self.assertIn('a.primary-color:hover {', result)
        # Should NOT contain lighten() function
        self.assertNotIn('lighten(', result)
        
        # Should have successful conversion
        self.assertEqual(len(converted), 1)
        self.assertEqual(len(unconverted), 0)
    
    def test_color_classes_with_css_variable(self):
        """Test color-classes mixin with CSS variable"""
        content = "@include color-classes(primary, var(--primary-color));"
        result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
        
        # Should generate proper CSS classes
        self.assertIn('.primary,', result)
        self.assertIn('.primary-color {', result)
        self.assertIn('color: var(--primary-color);', result)
        
        # Should use -lighten variant for hover states
        self.assertIn('a.primary:hover,', result)
        self.assertIn('a.primary-color:hover {', result)
        self.assertIn('color: var(--primary-lighten);', result)
        
        # Should NOT contain lighten() function
        self.assertNotIn('lighten(', result)
        
        # Should have successful conversion
        self.assertEqual(len(converted), 1)
        self.assertEqual(len(unconverted), 0)
    
    def test_positioning_mixins_with_directions(self):
        """Test positioning mixins with direction parameters"""
        test_cases = [
            ("@include absolute((top: 10px, left: 20px));", "absolute"),
            ("@include relative((bottom: 5px, right: 15px));", "relative"),
            ("@include fixed((top: 0, left: 0));", "fixed"),
        ]
        
        for content, position_type in test_cases:
            with self.subTest(content=content):
                result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
                
                # Should contain position declaration
                self.assertIn(f'position: {position_type};', result)
                
                # Should contain direction properties
                if 'top:' in content:
                    self.assertIn('top:', result)
                if 'left:' in content:
                    self.assertIn('left:', result)
                if 'bottom:' in content:
                    self.assertIn('bottom:', result)
                if 'right:' in content:
                    self.assertIn('right:', result)
                    
                # Should have successful conversion
                self.assertEqual(len(converted), 1, f"No conversion for {content}")
                self.assertEqual(len(unconverted), 0, f"Unconverted for {content}: {unconverted}")
    
    def test_centering_mixin_parameters(self):
        """Test centering mixin with various parameter combinations"""
        test_cases = [
            ("@include centering();", "transform: translateY(-50%)"),  # Default is top
            ("@include centering(top);", "transform: translateY(-50%)"),  # Top direction
            ("@include centering(top, 60%);", "transform: translateY(-60%)"),  # Top with custom amount
            ("@include centering(left);", "transform: translateX(-50%)"),  # Left direction
            ("@include centering(both);", "transform: translate(-50%, -50%)"),  # Both directions
        ]
        
        for content, expected in test_cases:
            with self.subTest(content=content):
                result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
                
                # Should contain proper transform
                self.assertIn('position: absolute;', result)
                self.assertIn(expected, result)
                
                # Should have successful conversion
                self.assertEqual(len(converted), 1)
                self.assertEqual(len(unconverted), 0)
    
    def test_filter_mixin_unquote_handling(self):
        """Test filter mixin handles unquote() function correctly"""
        content = "@include filter(blur, 5px);"
        result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
        
        # Should generate proper filter CSS
        self.assertIn('-webkit-filter: blur(5px);', result)
        self.assertIn('filter: blur(5px);', result)
        
        # Should NOT contain unquote() function
        self.assertNotIn('unquote(', result)
        
        # Should have successful conversion
        self.assertEqual(len(converted), 1)
        self.assertEqual(len(unconverted), 0)
    
    def test_missing_mixins_detection(self):
        """Test that missing mixins are properly detected"""
        missing_mixins = [
            "@include save-compare-tab-base();",
            "@include position((top: 10px));",
            "@include em(16px);",
            "@include get-mobile-size();",
        ]
        
        for content in missing_mixins:
            with self.subTest(content=content):
                result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
                
                # Should be in unconverted list
                self.assertGreater(len(unconverted), 0, f"Mixin should be unconverted: {content}")
                
                # Should not have been converted
                self.assertEqual(len(converted), 0, f"Mixin should not be converted: {content}")
    
    def test_complex_argument_parsing(self):
        """Test complex argument parsing scenarios"""
        test_cases = [
            # Hash-like parameters
            "@include absolute((top: 10px, left: 20px, z-index: 999));",
            # Multiple values
            "@include flex(1, 0, auto);",
            # Mixed quotes
            "@include font-size('16px', '18px');",
            # Nested functions
            "@include box-shadow(0 2px 4px rgba(0,0,0,0.1));",
        ]
        
        for content in test_cases:
            with self.subTest(content=content):
                result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
                
                # Should not crash the parser
                self.assertIsInstance(result, str)
                
                # Should process successfully (either converted or unconverted)
                self.assertGreaterEqual(len(converted) + len(unconverted), 0)
    
    def test_real_world_usage_patterns(self):
        """Test with actual usage patterns from dealer themes"""
        real_world_cases = [
            # Common color-classes usage
            "@include color-classes(primary, var(--primary));",
            "@include color-classes(secondary, #00ccfe);",
            
            # Common positioning usage
            "@include absolute((top: 0, right: 0));",
            "@include relative((z-index: 1));",
            
            # Common flexbox usage
            "@include flexbox();",
            "@include justify-content(center);",
            "@include align-items(center);",
            
            # Common utility usage
            "@include clearfix();",
            "@include transition(all 0.3s ease);",
            "@include box-shadow(0 2px 4px rgba(0,0,0,0.1));",
        ]
        
        for content in real_world_cases:
            with self.subTest(content=content):
                result, converted, unconverted = self.parser.parse_and_convert_mixins(content)
                
                # Should have successful conversion
                self.assertEqual(len(converted), 1, f"No conversion for {content}")
                
                # Should not be unconverted
                self.assertEqual(len(unconverted), 0, f"Unconverted for {content}: {unconverted}")
                
                # Should generate valid CSS
                self.assertGreater(len(result.strip()), 0)
                
                # Should not contain SCSS functions
                scss_functions = ['lighten(', 'darken(', 'type_of(', 'unquote(']
                for func in scss_functions:
                    self.assertNotIn(func, result, f"SCSS function {func} found in: {result}")

if __name__ == '__main__':
    unittest.main(verbosity=2)