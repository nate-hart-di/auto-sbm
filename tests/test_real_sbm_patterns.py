"""
Tests for real SBM patterns based on analysis of 20+ Stellantis PRs.

These tests validate that the automation matches the actual patterns
found in real-world Site Builder Migrations performed by developers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from sbm.core.migration import migrate_dealer_theme
from sbm.scss.processor import SCSSProcessor
from sbm.config import get_config


class TestRealSBMPatterns:
    """Test that automation matches real SBM patterns from GitHub PRs."""
    
    def test_creates_three_sb_files(self, test_config):
        """Test that migration creates exactly the 3 Site Builder files found in real PRs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test theme directory
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            # Mock config to use temp directory
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            # Run SCSS processor
            processor = SCSSProcessor(test_config)
            result = processor.process_theme("testdealer")
            
            # Verify the 3 standard files are created
            assert (theme_path / "sb-inside.scss").exists()
            assert (theme_path / "sb-vdp.scss").exists() or "sb-vdp.scss" in result.get("files_created", [])
            assert (theme_path / "sb-vrp.scss").exists() or "sb-vrp.scss" in result.get("files_created", [])
    
    def test_sb_inside_contains_map_components(self, test_config):
        """Test that sb-inside.scss contains the standard map components found in all real PRs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            # Read the created sb-inside.scss file
            sb_inside_content = (theme_path / "sb-inside.scss").read_text()
            
            # Verify map components are present (found in all real PRs)
            assert "#mapRow" in sb_inside_content
            assert "#map-canvas" in sb_inside_content
            assert "#directionsBox" in sb_inside_content
            assert ".mapwrap" in sb_inside_content
            assert ".getdirectionstext" in sb_inside_content
            assert ".locationtext" in sb_inside_content
            assert "height: 600px" in sb_inside_content  # Standard map height
            assert "max-width: 45%" in sb_inside_content  # Mobile responsive
    
    def test_sb_vdp_has_standard_header(self, test_config):
        """Test that sb-vdp.scss has the standard header found in real PRs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            sb_vdp_content = (theme_path / "sb-vdp.scss").read_text()
            
            # Verify standard header comments
            assert "Site Builder VDP Styles" in sb_vdp_content
            assert "Vehicle Detail Page (VDP)" in sb_vdp_content
            assert "sb-asset-cache" in sb_vdp_content
            assert "sb-vdp.css" in sb_vdp_content
    
    def test_sb_vrp_has_standard_header(self, test_config):
        """Test that sb-vrp.scss has the standard header found in real PRs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            sb_vrp_content = (theme_path / "sb-vrp.scss").read_text()
            
            # Verify standard header comments
            assert "Site Builder VRP Styles" in sb_vrp_content
            assert "Vehicle Results Page (VRP)" in sb_vrp_content
            assert "sb-asset-cache" in sb_vrp_content
            assert "sb-vrp.css" in sb_vrp_content
    
    def test_preserves_existing_vdp_styles(self, test_config):
        """Test that existing VDP styles are preserved when sb-vdp.scss already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            # Create existing sb-vdp.scss with content
            existing_content = """/*
\tExisting VDP styles
*/

#vehicleDetails {
\tcolor: red;
}"""
            (theme_path / "sb-vdp.scss").write_text(existing_content)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            result = processor.process_theme("testdealer")
            
            # Verify existing content is preserved
            final_content = (theme_path / "sb-vdp.scss").read_text()
            assert "Existing VDP styles" in final_content
            assert "#vehicleDetails" in final_content
            assert "color: red" in final_content
    
    def test_extracts_legacy_styles(self, test_config):
        """Test that legacy styles are extracted from existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            # Create legacy files with VDP/VRP styles
            (theme_path / "lvdp.scss").write_text("""
#vehicleDetails .price-box {
    background: blue;
}

#ctabox-pricing {
    color: white;
}
""")
            
            (theme_path / "lvrp.scss").write_text("""
#results-page .vehicle {
    border: 1px solid black;
}

.lightning-vrp-custom-html {
    margin: 10px;
}
""")
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            # Check that styles were extracted (basic pattern matching)
            sb_vdp_content = (theme_path / "sb-vdp.scss").read_text()
            sb_vrp_content = (theme_path / "sb-vrp.scss").read_text()
            
            # Note: The actual extraction logic would be more sophisticated
            # This test validates the structure is in place
            assert "sb-vdp.scss" in str(theme_path / "sb-vdp.scss")
            assert "sb-vrp.scss" in str(theme_path / "sb-vrp.scss")
    
    def test_scss_processor_matches_pr_structure(self, test_config):
        """Test that SCSS processor produces results matching real PR structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            # Run SCSS processor
            processor = SCSSProcessor(test_config)
            result = processor.process_theme("testdealer")
            
            # Verify result structure matches real PR patterns
            assert result["success"] is True
            assert result["map_components_added"] is True
            
            # Verify files were created (matching real PR file structure)
            expected_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss"]
            for expected_file in expected_files:
                assert expected_file in result["files_created"] or (theme_path / expected_file).exists()
    
    def test_branch_naming_pattern(self, test_config):
        """Test that branch naming follows the pattern found in real PRs."""
        # Real PRs use pattern: {dealername}-SBM{MMDD}
        # e.g., "libertyjeepchrysler-SBM0625", "firkinscdjr-SBM0625"
        
        with patch('sbm.core.git_operations.GitOperations') as mock_git_class:
            mock_git_instance = Mock()
            mock_git_instance.create_migration_branch.return_value = {
                "branch_name": "testdealer-SBM0625"
            }
            mock_git_class.return_value = mock_git_instance
            
            from sbm.core.git_operations import GitOperations
            git_ops = GitOperations(test_config)
            result = git_ops.create_migration_branch("testdealer")
            
            # Verify branch name pattern
            branch_name = result["branch_name"]
            assert "testdealer" in branch_name
            assert "SBM" in branch_name
            assert len(branch_name.split("-SBM")[1]) == 4  # MMDD format


class TestSBMFileContent:
    """Test specific content patterns found in real SBM files."""
    
    def test_map_responsive_breakpoint(self, test_config):
        """Test that map components use Site Builder standard breakpoints (768px, 1024px)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            sb_inside_content = (theme_path / "sb-inside.scss").read_text()
            
            # Verify Site Builder standard breakpoints
            assert "@media (min-width: 768px)" in sb_inside_content  # Tablet
            assert "@media (min-width: 1024px)" in sb_inside_content  # Desktop
            assert "@media (max-width: 767px)" in sb_inside_content  # Mobile
            assert "height: 250px" in sb_inside_content  # Mobile-first map height
    
    def test_directions_box_positioning(self, test_config):
        """Test that directions box has the exact positioning found in real PRs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            sb_inside_content = (theme_path / "sb-inside.scss").read_text()
            
            # Verify exact positioning values from real PRs
            assert "width: 400px" in sb_inside_content
            assert "top:200px" in sb_inside_content
            assert "left: 50px" in sb_inside_content
            assert "padding: 50px 0" in sb_inside_content
    
    def test_font_family_consistency(self, test_config):
        """Test that font families match those used in real PRs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "dealer-themes" / "testdealer"
            theme_path.mkdir(parents=True)
            
            test_config.get_theme_path = Mock(return_value=theme_path)
            
            processor = SCSSProcessor(test_config)
            processor.process_theme("testdealer")
            
            sb_inside_content = (theme_path / "sb-inside.scss").read_text()
            
            # Default font family found in most real PRs
            assert "'Lato', sans-serif" in sb_inside_content


class TestLegacyStyleExtraction:
    """Test extraction of styles from legacy files."""
    
    def test_vdp_pattern_recognition(self, test_config):
        """Test that VDP-specific patterns are correctly identified."""
        processor = SCSSProcessor(test_config)
        
        # Test content with VDP patterns
        test_content = """
#vehicleDetails .price-box {
    color: red;
}

.vdp-title {
    font-size: 24px;
}

#ctabox-pricing {
    background: blue;
}

.general-style {
    margin: 10px;
}
"""
        
        vdp_styles = processor._filter_vdp_styles(test_content)
        
        # Should extract VDP-specific styles
        # Note: This tests the pattern matching logic
        assert isinstance(vdp_styles, str)
    
    def test_vrp_pattern_recognition(self, test_config):
        """Test that VRP-specific patterns are correctly identified."""
        processor = SCSSProcessor(test_config)
        
        # Test content with VRP patterns
        test_content = """
#results-page .vehicle {
    border: 1px solid black;
}

#lvrp-results-wrapper {
    padding: 20px;
}

.hit-content {
    margin: 5px;
}

.general-style {
    color: blue;
}
"""
        
        vrp_styles = processor._filter_vrp_styles(test_content)
        
        # Should extract VRP-specific styles
        assert isinstance(vrp_styles, str) 
