import os
from pathlib import Path

from sbm.core import maps


def test_find_commontheme_map_imports_handles_missing_extension_and_underscore(tmp_path, monkeypatch):
    base = tmp_path / "DealerInspireCommonTheme"
    target_dir = base / "css/dealer-groups/lexus/lexusoem3"
    target_dir.mkdir(parents=True)

    target_file = target_dir / "_mapsection3.scss"
    target_file.write_text("// map section content", encoding="utf-8")

    style_scss = tmp_path / "style.scss"
    style_scss.write_text(
        "@import '../../DealerInspireCommonTheme/css/dealer-groups/lexus/lexusoem3/mapsection3';",
        encoding="utf-8",
    )

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(base))

    imports = maps.find_commontheme_map_imports(str(style_scss))
    assert imports, "Should detect map import without explicit .scss extension"
    assert imports[0]["commontheme_absolute"] == str(target_file)


def test_find_map_shortcodes_in_functions_detects_template_part(tmp_path, monkeypatch):
    functions_path = tmp_path / "functions.php"
    functions_path.write_text(
        """
        add_shortcode('full-map', 'render_full_map');
        function render_full_map() {
            get_template_part('partials/dealer-groups/lexus/lexusoem3/mapsection3');
        }
        """,
        encoding="utf-8",
    )

    results = maps.find_map_shortcodes_in_functions(tmp_path)
    assert any("mapsection3" in p.get("partial_path", "") for p in results)


def test_find_map_shortcodes_detects_lou_fusz_map_without_keyword(tmp_path, monkeypatch):
    """Test that full-map shortcode is detected even when path doesn't contain MAP_KEYWORDS."""
    functions_path = tmp_path / "functions.php"
    functions_path.write_text(
        """
        add_shortcode('full-map', 'full_map');
        function full_map() {
            get_template_part('partials/dealer-groups/lou-fusz/map');
        }
        """,
        encoding="utf-8",
    )

    results = maps.find_map_shortcodes_in_functions(tmp_path)

    # Should find the partial even though 'lou-fusz' is not in MAP_KEYWORDS
    assert len(results) > 0, "Should detect full-map shortcode"
    assert any("lou-fusz/map" in p.get("partial_path", "") for p in results), \
        "Should extract lou-fusz/map partial path"

    # Verify it was found via shortcode handler, not keyword matching
    lou_fusz_result = [p for p in results if "lou-fusz/map" in p.get("partial_path", "")][0]
    assert lou_fusz_result.get("source") == "found_in_shortcode_handler"
    assert lou_fusz_result.get("shortcode") == "full-map"


def test_copy_partial_with_fuzzy_matching(tmp_path, monkeypatch):
    """Test that fuzzy matching finds _map-section.php when looking for map.php."""
    # Setup CommonTheme structure - file exists with different name
    commontheme_base = tmp_path / "CommonTheme"
    fca_dir = commontheme_base / "partials/dealer-groups/fca"
    fca_dir.mkdir(parents=True)

    # Create file with variant name (e.g., _map-row-2.php instead of map.php)
    actual_file = fca_dir / "_map-row-2.php"
    actual_file.write_text("<?php // FCA map partial ?>", encoding="utf-8")

    # Setup dealer theme dir
    dealer_theme_dir = tmp_path / "dealer-themes/testdealer"
    dealer_theme_dir.mkdir(parents=True)

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme_base))
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(dealer_theme_dir))

    # Request exact path "fca/map" but file is "_map-row-2.php"
    partial_info = {
        "partial_path": "partials/dealer-groups/fca/map",
        "source": "found_in_shortcode_handler",
    }

    result = maps.copy_partial_to_dealer_theme("testdealer", partial_info)

    assert result == "copied", "Should successfully copy with fuzzy matching"

    # Verify the file was copied to dealer theme
    copied_file = dealer_theme_dir / "partials/dealer-groups/fca/map.php"
    assert copied_file.exists(), "File should be copied to dealer theme"


def test_derive_map_imports_from_partials_resolves_underscore_variant(tmp_path, monkeypatch):
    base = tmp_path / "DealerInspireCommonTheme"
    target_dir = base / "css/dealer-groups/lexus/lexusoem3"
    target_dir.mkdir(parents=True)
    target_file = target_dir / "_mapsection3.scss"
    target_file.write_text("// map section content", encoding="utf-8")

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(base))

    partials = [
        {"partial_path": "partials/dealer-groups/lexus/lexusoem3/mapsection3"},
    ]

    imports = maps.derive_map_imports_from_partials(partials)
    assert imports, "Should derive SCSS path from partial path"
    assert imports[0]["commontheme_absolute"] == str(target_file)
