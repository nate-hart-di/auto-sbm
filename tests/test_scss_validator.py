"""
Tests for the SCSS validator module.
"""

import unittest
import os
import tempfile
from sbm.scss.validator import (
    count_braces, 
    fix_missing_semicolons, 
    fix_unbalanced_braces,
    fix_invalid_css_rules, 
    fix_invalid_media_queries
)


class TestSCSSValidator(unittest.TestCase):
    """Test cases for the SCSS validator module."""
    
    def test_count_braces(self):
        """Test the count_braces function."""
        content = """
        .test {
            color: red;
            .nested {
                background: blue;
            }
        }
        """
        opening, closing = count_braces(content)
        self.assertEqual(opening, 2)
        self.assertEqual(closing, 2)
    
    def test_fix_missing_semicolons(self):
        """Test the fix_missing_semicolons function."""
        content = """
        .test {
            color: red
            background: blue;
        }
        """
        fixed = fix_missing_semicolons(content)
        self.assertIn("color: red;", fixed)
    
    def test_fix_unbalanced_braces(self):
        """Test the fix_unbalanced_braces function."""
        # Test missing closing brace
        content = """
        .test {
            color: red;
            .nested {
                background: blue;
            }
        """
        fixed = fix_unbalanced_braces(content)
        opening, closing = count_braces(fixed)
        self.assertEqual(opening, closing)
        
        # Test extra closing brace
        content = """
        .test {
            color: red;
            .nested {
                background: blue;
            }
        }}
        """
        fixed = fix_unbalanced_braces(content)
        opening, closing = count_braces(fixed)
        self.assertEqual(opening, closing)
    
    def test_fix_invalid_css_rules(self):
        """Test the fix_invalid_css_rules function."""
        content = """
        .test {
            color: ;
            : red;
        }
        """
        fixed = fix_invalid_css_rules(content)
        self.assertIn("color: initial;", fixed)
        self.assertIn("/* Invalid rule", fixed)
    
    def test_fix_invalid_media_queries(self):
        """Test the fix_invalid_media_queries function."""
        content = """
        @media max-width: 768px {
            .test {
                color: red;
            }
        }
        """
        fixed = fix_invalid_media_queries(content)
        self.assertIn("@media screen and (max-width: 768px)", fixed)


if __name__ == "__main__":
    unittest.main() 
