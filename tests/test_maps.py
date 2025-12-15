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
