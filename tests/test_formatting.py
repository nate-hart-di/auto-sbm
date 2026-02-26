from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbm.core.migration import _format_all_scss_with_prettier


@pytest.fixture
def mock_theme_dir(tmp_path):
    """Create a mock theme directory with various SCSS files."""
    theme_dir = tmp_path / "dealer-themes" / "test-dealer"
    theme_dir.mkdir(parents=True)

    # Root Site Builder files (should be formatted)
    (theme_dir / "sb-inside.scss").write_text(".test { color: red; }")
    (theme_dir / "sb-home.scss").write_text(".test { margin: 0; }")

    # Original theme files (should NOT be formatted)
    css_dir = theme_dir / "css"
    css_dir.mkdir()
    (css_dir / "style.scss").write_text(".old { display: block; }")

    # Map partials in subdirectories (should NOT be formatted)
    partials_dir = theme_dir / "partials"
    partials_dir.mkdir()
    (partials_dir / "sb-map-test.scss").write_text(".map { padding: 10px; }")

    return theme_dir


@patch("sbm.utils.path.get_dealer_theme_dir")
@patch("subprocess.run")
def test_format_all_scss_with_prettier_scope(mock_run, mock_get_theme_dir, mock_theme_dir):
    """Test that only root sb-*.scss files are targeted by prettier."""
    mock_get_theme_dir.return_value = str(mock_theme_dir)
    mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

    # Run the formatting function
    result = _format_all_scss_with_prettier("test-dealer")

    assert result is True

    # Verify subprocess.run was called with only the root sb-*.scss files
    args, kwargs = mock_run.call_args
    command = args[0]

    # Command should contain prettier and the files
    assert any("prettier" in arg for arg in command)

    # Filter for root sb-*.scss files in the command
    sb_files_in_cmd = [arg for arg in command if "sb-" in arg and ".scss" in arg]

    # Should only find the 2 root files
    assert len(sb_files_in_cmd) == 2
    assert any("sb-inside.scss" in f for f in sb_files_in_cmd)
    assert any("sb-home.scss" in f for f in sb_files_in_cmd)

    # Should NOT find the file in the partials directory
    assert not any("partials" in f for f in sb_files_in_cmd)
    # Should NOT find the original theme file
    assert not any("style.scss" in f for f in sb_files_in_cmd)


@patch("sbm.utils.path.get_dealer_theme_dir")
@patch("sbm.core.migration.Path.exists")
def test_format_all_scss_no_files(mock_exists, mock_get_theme_dir, tmp_path):
    """Test behavior when no matching files are found."""
    mock_get_theme_dir.return_value = str(tmp_path)
    mock_exists.return_value = True

    # Mock glob to return empty list
    with patch.object(Path, "glob", return_value=[]):
        result = _format_all_scss_with_prettier("test-dealer")
        assert result is False


@patch("sbm.utils.path.get_dealer_theme_dir")
@patch("subprocess.run")
def test_format_all_scss_failure(mock_run, mock_get_theme_dir, mock_theme_dir):
    """Test behavior when prettier returns an error code."""
    mock_get_theme_dir.return_value = str(mock_theme_dir)
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

    result = _format_all_scss_with_prettier("test-dealer")
    assert result is False
