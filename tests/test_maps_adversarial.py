from pathlib import Path
from sbm.core import maps
from unittest.mock import patch

def test_should_migrate_map_import_sibling_structure(tmp_path, monkeypatch):
    """
    Test the critical flaw: if import is ../../CommonTheme and it resolves on disk,
    should_migrate_map_import might think it's 'local' and SKIP it.
    """
    # Create sibling structure inside dealer-themes
    dealer_themes_root = tmp_path / "dealer-themes"
    dealer_themes_root.mkdir()

    # 1. The "Fake" CommonTheme (reachable via relative path)
    common_theme = dealer_themes_root / "DealerInspireCommonTheme"
    common_theme.mkdir()
    (common_theme / "css").mkdir()
    (common_theme / "css" / "map.scss").write_text("// common content")

    # 2. The Dealer Theme
    dealer_theme = dealer_themes_root / "test-dealer"
    dealer_theme.mkdir()
    (dealer_theme / "css").mkdir()
    (dealer_theme / "css" / "style.scss").write_text("// style")

    # 3. Patch COMMON_THEME_DIR to point to the valid one
    # So that if the local check is correctly bypassed, the CommonTheme check succeeds
    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(common_theme))

    # The import path used in Group A
    # From dealer-theme/css/style.scss to CommonTheme
    # ../../DealerInspireCommonTheme/css/map
    import_path = "../../DealerInspireCommonTheme/css/map"

    # In strict filesystem terms relative to dealer_theme/css:
    # .. -> test-dealer
    # .. -> dealer-themes
    # DealerInspireCommonTheme -> dealer-themes/DealerInspireCommonTheme
    # It exists!

    # The function checks "Local Existence" relative to dealer_theme/css
    # OLD LOGIC: Follows path -> Finds file -> Returns False (Skip).
    # NEW LOGIC: Follows path -> Finds file -> Checks is_relative_to(dealer_theme) -> False -> Ignores.
    #            Then checks CommonTheme -> Finds file -> Returns True.

    should_migrate = maps.should_migrate_map_import(import_path, dealer_theme)

    assert should_migrate == True, "Should migrate external CommonTheme path, but logic thinks it is local!"
