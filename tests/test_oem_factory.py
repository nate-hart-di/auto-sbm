"""
Tests for the OEM Factory module.

This module contains unit tests for the OEM Factory and OEM Handlers.
"""

import unittest
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from sbm.oem.factory import OEMFactory
from sbm.oem.base import BaseOEMHandler
from sbm.oem.stellantis import StellantisHandler
from sbm.oem.default import DefaultHandler


class TestOEMFactory(unittest.TestCase):
    """Test cases for the OEM Factory."""
    
    def test_create_handler_with_brand(self):
        """Test creating a handler based on brand information."""
        # Test Stellantis brands
        for brand in ['chrysler', 'dodge', 'jeep', 'ram', 'fiat', 'cdjr']:
            handler = OEMFactory.create_handler('test-slug', {'brand': brand})
            self.assertIsInstance(handler, StellantisHandler)
            self.assertEqual(handler.slug, 'test-slug')
    
    def test_create_handler_with_slug(self):
        """Test creating a handler based on slug."""
        # Test Stellantis slug patterns
        for slug in ['chrysler-dealer', 'jeep-ram-dealer', 'fca-auto']:
            handler = OEMFactory.create_handler(slug)
            self.assertIsInstance(handler, StellantisHandler)
            self.assertEqual(handler.slug, slug)
    
    def test_default_handler_fallback(self):
        """Test fallback to DefaultHandler for unknown brands."""
        handler = OEMFactory.create_handler('unknown-dealer')
        self.assertIsInstance(handler, DefaultHandler)
        self.assertEqual(handler.slug, 'unknown-dealer')
        
        handler = OEMFactory.create_handler('test-slug', {'brand': 'unknown'})
        self.assertIsInstance(handler, DefaultHandler)
        self.assertEqual(handler.slug, 'test-slug')


class TestStellantisHandler(unittest.TestCase):
    """Test cases for the Stellantis Handler."""
    
    def setUp(self):
        self.handler = StellantisHandler('test-slug')
    
    def test_get_brand_match_patterns(self):
        """Test that brand match patterns are correct."""
        patterns = self.handler.get_brand_match_patterns()
        self.assertIsInstance(patterns, list)
        self.assertIn('chrysler', patterns)
        self.assertIn('dodge', patterns)
        self.assertIn('jeep', patterns)
        self.assertIn('ram', patterns)
        self.assertIn('fiat', patterns)
    
    def test_get_map_partial_patterns(self):
        """Test that map partial patterns are correct."""
        patterns = self.handler.get_map_partial_patterns()
        self.assertIsInstance(patterns, list)
        # Should include Stellantis-specific patterns
        self.assertTrue(any('fca' in pattern for pattern in patterns))
        self.assertTrue(any('cdjr' in pattern for pattern in patterns))
        self.assertTrue(any('stellantis' in pattern for pattern in patterns))


class TestDefaultHandler(unittest.TestCase):
    """Test cases for the Default Handler."""
    
    def setUp(self):
        self.handler = DefaultHandler('test-slug')
    
    def test_get_brand_match_patterns(self):
        """Test that default handler has no brand match patterns."""
        patterns = self.handler.get_brand_match_patterns()
        self.assertEqual(patterns, [])
    
    def test_get_map_styles(self):
        """Test that default handler provides map styles."""
        styles = self.handler.get_map_styles()
        self.assertIsInstance(styles, str)
        self.assertIn('#mapRow', styles)
        self.assertIn('#map-canvas', styles)


if __name__ == '__main__':
    unittest.main()
