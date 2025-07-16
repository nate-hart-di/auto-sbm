#!/usr/bin/env python3
"""
Test SCSS function handling and conversion
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbm.scss.processor import SCSSProcessor
from sbm.utils.helpers import lighten_hex, darken_hex, hex_to_rgb, rgb_to_hex

class TestSCSSFunctions(unittest.TestCase):
    
    def setUp(self):
        """Setup test fixtures"""
        self.processor = SCSSProcessor("test-dealer")
    
    def test_lighten_hex_function(self):
        """Test lighten_hex utility function"""
        test_cases = [
            ("#252525", 10, "#2c2c2c"),
            ("#000000", 20, "#333333"),
            ("#ffffff", 10, "#ffffff"),  # Already white
            ("#ff0000", 50, "#ff8080"),  # Red lightened
        ]
        
        for hex_color, percentage, expected in test_cases:
            with self.subTest(hex_color=hex_color, percentage=percentage):
                result = lighten_hex(hex_color, percentage)
                self.assertEqual(result, expected, 
                    f"lighten_hex({hex_color}, {percentage}) = {result}, expected {expected}")
    
    def test_darken_hex_function(self):
        """Test darken_hex utility function"""
        test_cases = [
            ("#ffffff", 10, "#e6e6e6"),
            ("#00ccfe", 10, "#00b7e4"),  # From actual test case
            ("#ff0000", 50, "#800000"),  # Red darkened
            ("#000000", 20, "#000000"),  # Already black
        ]
        
        for hex_color, percentage, expected in test_cases:
            with self.subTest(hex_color=hex_color, percentage=percentage):
                result = darken_hex(hex_color, percentage)
                self.assertEqual(result, expected,
                    f"darken_hex({hex_color}, {percentage}) = {result}, expected {expected}")
    
    def test_hex_to_rgb_conversion(self):
        """Test hex to RGB conversion"""
        test_cases = [
            ("#252525", (37, 37, 37)),
            ("#ff0000", (255, 0, 0)),
            ("#00ff00", (0, 255, 0)),
            ("#0000ff", (0, 0, 255)),
            ("#fff", (255, 255, 255)),  # Short form
            ("252525", (37, 37, 37)),   # No hash
        ]
        
        for hex_color, expected in test_cases:
            with self.subTest(hex_color=hex_color):
                result = hex_to_rgb(hex_color)
                self.assertEqual(result, expected)
    
    def test_rgb_to_hex_conversion(self):
        """Test RGB to hex conversion"""
        test_cases = [
            ((37, 37, 37), "#252525"),
            ((255, 0, 0), "#ff0000"),
            ((0, 255, 0), "#00ff00"),
            ((0, 0, 255), "#0000ff"),
            ((255, 255, 255), "#ffffff"),
        ]
        
        for rgb, expected in test_cases:
            with self.subTest(rgb=rgb):
                result = rgb_to_hex(*rgb)
                self.assertEqual(result, expected)
    
    def test_scss_function_conversion_hardcoded_colors(self):
        """Test SCSS function conversion with hardcoded colors"""
        test_cases = [
            # Lighten functions
            ("color: lighten(#252525, 10%);", "color: #2c2c2c;"),
            ("background: lighten(#ff0000, 20%);", "background: #ff6666;"),
            
            # Darken functions  
            ("color: darken(#ffffff, 10%);", "color: #e6e6e6;"),
            ("background-color: darken(#00ccfe, 10%);", "background-color: #00b7e4;"),
        ]
        
        for input_scss, expected in test_cases:
            with self.subTest(input_scss=input_scss):
                result = self.processor._convert_scss_functions(input_scss)
                self.assertIn(expected, result)
                
                # Should not contain SCSS functions
                self.assertNotIn('lighten(', result)
                self.assertNotIn('darken(', result)
    
    def test_scss_function_with_css_variables_warning(self):
        """Test that SCSS functions with CSS variables are logged as warnings"""
        test_cases = [
            "color: lighten(var(--primary), 20%);",
            "background: darken(var(--secondary), 10%);",
        ]
        
        for input_scss in test_cases:
            with self.subTest(input_scss=input_scss):
                # Should log warning but not crash
                result = self.processor._convert_scss_functions(input_scss)
                self.assertIsInstance(result, str)
    
    def test_malformed_css_fixes(self):
        """Test fixing malformed CSS patterns"""
        test_cases = [
            # Font-family with weight concatenated
            ("font-family: var(--weight): 300;", 
             "font-family: var(--weight);\nfont-weight: 300;"),
            
            # Commented out broken code removal
            ("// background: rgba(var(--primary), 0.5);", ""),
        ]
        
        for input_css, expected in test_cases:
            with self.subTest(input_css=input_css):
                result = self.processor._convert_scss_functions(input_css)
                
                if expected:
                    self.assertIn(expected, result)
                else:
                    # Should be removed
                    self.assertNotIn("rgba(var(--", result)
    
    def test_edge_cases_invalid_colors(self):
        """Test edge cases with invalid color values"""
        test_cases = [
            # Invalid hex values should return original
            ("invalidhex", "invalidhex"),
            ("#gg0000", "#gg0000"),
            ("", ""),
            ("#12", "#12"),  # Too short
            ("#1234567", "#1234567"),  # Too long
        ]
        
        for invalid_hex, expected in test_cases:
            with self.subTest(invalid_hex=invalid_hex):
                result = lighten_hex(invalid_hex, 10)
                self.assertEqual(result, expected)
                
                result = darken_hex(invalid_hex, 10)
                self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main(verbosity=2)