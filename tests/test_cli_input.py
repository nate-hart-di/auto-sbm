import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sbm.cli import _expand_theme_names


class TestCLIInput(unittest.TestCase):
    def test_expand_single_theme(self):
        """Test expansion of a single theme name."""
        input_themes = ("theme1",)
        result = _expand_theme_names(input_themes)
        self.assertEqual(result, ["theme1"])

    def test_expand_multiple_themes(self):
        """Test expansion of multiple theme names passed as arguments."""
        input_themes = ("theme1", "theme2", "theme3")
        result = _expand_theme_names(input_themes)
        self.assertEqual(result, ["theme1", "theme2", "theme3"])

    def test_expand_duplicates(self):
        """Test that duplicates are removed while preserving order."""
        # Using a tuple to match Click's nargs=-1 behavior
        input_themes = ("theme1", "theme2", "theme1", "theme3")
        result = _expand_theme_names(input_themes)
        self.assertEqual(result, ["theme1", "theme2", "theme3"])

    def test_expand_file_input(self):
        """Test expansion of slugs from a file using the @ prefix."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            # Mock the file content with spaces, commas, and inline comments
            file_content = "slug1, slug2 # inline comment\nslug3 slug4\n\nslug5\n"
            with patch("pathlib.Path.open", unittest.mock.mock_open(read_data=file_content)):
                input_themes = ("@slugs.txt", "slug6")
                result = _expand_theme_names(input_themes)
                self.assertEqual(result, ["slug1", "slug2", "slug3", "slug4", "slug5", "slug6"])

    def test_expand_missing_file(self):
        """Test behavior when a theme list file is missing."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            input_themes = ("@nonexistent.txt", "valid_slug")
            # Should skip the missing file and return only the valid slug
            result = _expand_theme_names(input_themes)
            self.assertEqual(result, ["valid_slug"])

    def test_expand_file_fallback(self):
        """Test fallback to REPO_ROOT when file is not in CWD."""
        with patch("pathlib.Path.exists") as mock_exists:
            # First call for Path(file_path_str) -> False (not in CWD)
            # Second call for fallback_path -> True (in REPO_ROOT)
            mock_exists.side_effect = [False, True]

            # Mock the file content
            file_content = "fallback_slug"
            with patch("pathlib.Path.open", unittest.mock.mock_open(read_data=file_content)):
                # Mock REPO_ROOT in sbm.cli
                with patch("sbm.cli.REPO_ROOT", Path("/mock/repo")):
                    input_themes = ("@slugs.txt",)
                    result = _expand_theme_names(input_themes)
                    self.assertEqual(result, ["fallback_slug"])


if __name__ == "__main__":
    unittest.main()
