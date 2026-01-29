from unittest.mock import patch, MagicMock
from pathlib import Path
from sbm.core import maps


def test_map_keywords_includes_section_directions():
    """Test that section-directions is included in MAP_KEYWORDS."""
    assert "section-directions" in maps.MAP_KEYWORDS, "section-directions should be in MAP_KEYWORDS"


def test_should_migrate_map_import_skips_local_file(tmp_path, monkeypatch):
    """Test that it returns False if file exists locally."""
    # Setup dealer theme structure
    dealer_dir = tmp_path / "dealer-theme"
    dealer_dir.mkdir()
    css_dir = dealer_dir / "css"
    css_dir.mkdir()

    # Create a local SCSS file
    (css_dir / "_local-map.scss").write_text("// local content")

    # Import path as it would appear in style.scss (relative to css/)
    import_path = "local-map"

    assert maps.should_migrate_map_import(import_path, dealer_dir) == False


def test_should_migrate_map_import_resolves_broken_path(tmp_path, monkeypatch):
    """Test Group A fix: Resolves ../../DealerInspireCommonTheme/... correctly."""
    dealer_dir = tmp_path / "dealer-theme"
    dealer_dir.mkdir()
    (dealer_dir / "css").mkdir()

    # Setup CommonTheme
    common_theme_dir = tmp_path / "CommonTheme"
    common_theme_dir.mkdir()

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(common_theme_dir))

    # Create target file in CommonTheme
    target_dir = common_theme_dir / "css/dealer-groups/lexus"
    target_dir.mkdir(parents=True)
    (target_dir / "_mapsection.scss").write_text("// common content")

    # Broken path style import (typical in Group A)
    import_path = "../../DealerInspireCommonTheme/css/dealer-groups/lexus/mapsection"

    assert maps.should_migrate_map_import(import_path, dealer_dir) == True


def test_should_migrate_map_import_fails_if_not_found(tmp_path, monkeypatch):
    """Test fallback: returns False if not found anywhere."""
    dealer_dir = tmp_path / "dealer-theme"
    dealer_dir.mkdir()
    (dealer_dir / "css").mkdir()

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(tmp_path / "CommonTheme"))

    import_path = "non-existent-map"

    assert maps.should_migrate_map_import(import_path, dealer_dir) == False


def test_migrate_map_components_group_b_scenario(tmp_path, monkeypatch):
    """
    Test Group B: No explicit imports, dynamic shortcodes (missed by regex),
    but explicit get_template_part in front-page.php.
    Should NOT exit early and SHOULD migrate SCSS for found partial.
    """
    dealer_slug = "lexusofalbuquerque"
    dealer_dir = tmp_path / "dealer-themes" / dealer_slug
    dealer_dir.mkdir(parents=True)

    # Mock mocks
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda s: str(dealer_dir))

    # 1. Empty style.scss
    (dealer_dir / "css").mkdir()
    (dealer_dir / "css" / "style.scss").write_text("// no map imports")
    (dealer_dir / "sb-inside.scss").write_text("// sb-inside")

    # 2. Dynamic functions.php (obfuscated shortcode registration)
    (dealer_dir / "functions.php").write_text("""
        $arr = ['section-directions'];
        foreach($arr as $a) { add_shortcode($a, 'func'); }
    """)

    # 3. front-page.php using the partial directly
    (dealer_dir / "front-page.php").write_text("""
        <?php get_template_part('partials/section-directions'); ?>
    """)

    # 4. Setup CommonTheme with the target SCSS and PHP
    common_theme = tmp_path / "CommonTheme"
    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(common_theme))

    # partials/section-directions.php
    (common_theme / "partials").mkdir(parents=True)
    (common_theme / "partials" / "section-directions.php").write_text("<?php // map partial ?>")

    # css/section-directions.scss
    (common_theme / "css").mkdir(parents=True)
    (common_theme / "css" / "_section-directions.scss").write_text("// map scss")

    # Run migration
    # We mock migrate_map_scss_content to verify it gets called with correct targets
    # OR we just check the file output if we let it run.
    # Let's run it fully but with a mock processor (optional)

    from sbm.oem.default import DefaultHandler

    handler = DefaultHandler(dealer_slug)

    result = maps.migrate_map_components(dealer_slug, oem_handler=handler)

    assert result == True

    # Verify SCSS was migrated (sb-inside.scss created/appended)
    sb_inside = dealer_dir / "sb-inside.scss"
    assert sb_inside.exists(), "sb-inside.scss should be created"
    assert "// map scss" in sb_inside.read_text(), "SCSS content should be migrated"

    # Verify PHP was migrated (Copying is now enabled)
    partial_dest = dealer_dir / "partials" / "section-directions.php"
    assert partial_dest.exists(), "Partial should be copied"


def test_find_commontheme_map_imports_matches_underscore_prefix(tmp_path, monkeypatch):
    """
    Regression test: Verify that imports with underscore-prefixed filenames
    (e.g., _section-directions) are correctly matched by the regex.
    """
    dealer_dir = tmp_path / "dealer-theme"
    dealer_dir.mkdir()
    css_dir = dealer_dir / "css"
    css_dir.mkdir()

    # Create style.scss with underscore-prefixed import
    style_scss = css_dir / "style.scss"
    style_scss.write_text(
        "@import '../../DealerInspireCommonTheme/css/dealer-groups/lexus/lexusoem2/_section-directions';"
    )

    # Setup CommonTheme
    common_theme = tmp_path / "CommonTheme"
    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(common_theme))

    # Create the target file in CommonTheme
    target_dir = common_theme / "css" / "dealer-groups" / "lexus" / "lexusoem2"
    target_dir.mkdir(parents=True)
    (target_dir / "_section-directions.scss").write_text("// map scss content")

    # Run the function
    from sbm.oem.default import DefaultHandler

    handler = DefaultHandler("test-slug")
    imports = maps.find_commontheme_map_imports(style_scss, handler)

    # Should find exactly 1 import
    assert len(imports) == 1, f"Expected 1 import, found {len(imports)}"
    assert "_section-directions" in imports[0]["import_path"], (
        "Should match underscore-prefixed filename"
    )
