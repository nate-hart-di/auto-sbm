from unittest.mock import MagicMock, patch

from sbm.config import Config
from sbm.core.git import GitOperations
from sbm.oem.landrover import LandRoverHandler


def _mock_completed(stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = 0
    return m


@patch("sbm.core.git.get_dealer_theme_dir", return_value="/fake/platform/dealer-themes/landroverreno")
@patch("sbm.core.git.get_platform_dir", return_value="/fake/platform")
@patch("subprocess.run")
@patch("sbm.oem.factory.OEMFactory.detect_from_theme")
def test_analyze_migration_changes_includes_appended_style_notes_when_added(
    mock_detect_handler,
    mock_run,
    _mock_platform_dir,
    _mock_theme_dir,
):
    git_ops = GitOperations(Config({}))
    mock_detect_handler.return_value = LandRoverHandler("landroverreno")

    # 1) name-status diff, 2) sb-inside added-lines diff
    mock_run.side_effect = [
        _mock_completed(
            "A\tdealer-themes/landroverreno/sb-inside.scss\n"
            "A\tdealer-themes/landroverreno/sb-vdp.scss\n"
        ),
        _mock_completed(
            "+/* Land Rover Inside Pages Styles */\n"
            "+/* Land Rover National Offers Styles */\n"
        ),
    ]

    items = git_ops._analyze_migration_changes(slug="landroverreno")

    assert "- Added Land Rover Inside Pages Styles to sb-inside.scss" in items
    assert "- Added Land Rover National Offers Styles to sb-inside.scss" in items


@patch("sbm.core.git.get_dealer_theme_dir", return_value="/fake/platform/dealer-themes/landroverreno")
@patch("sbm.core.git.get_platform_dir", return_value="/fake/platform")
@patch("subprocess.run")
@patch("sbm.oem.factory.OEMFactory.detect_from_theme")
def test_analyze_migration_changes_omits_appended_style_notes_when_not_added(
    mock_detect_handler,
    mock_run,
    _mock_platform_dir,
    _mock_theme_dir,
):
    git_ops = GitOperations(Config({}))
    mock_detect_handler.return_value = LandRoverHandler("landroverreno")

    # 1) name-status diff, 2) sb-inside diff without marker comments
    mock_run.side_effect = [
        _mock_completed("A\tdealer-themes/landroverreno/sb-inside.scss\n"),
        _mock_completed("+.some-other-selector { color: red; }\n"),
    ]

    items = git_ops._analyze_migration_changes(slug="landroverreno")

    assert "- Added Land Rover Inside Pages Styles to sb-inside.scss" not in items
    assert "- Added Land Rover National Offers Styles to sb-inside.scss" not in items
