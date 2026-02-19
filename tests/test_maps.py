from sbm.core import maps


def test_find_commontheme_map_imports_handles_missing_extension_and_underscore(
    tmp_path, monkeypatch
):
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
    assert any("lou-fusz/map" in p.get("partial_path", "") for p in results), (
        "Should extract lou-fusz/map partial path"
    )

    # Verify it was found via shortcode handler, not keyword matching
    lou_fusz_result = next(
        p for p in results if "lou-fusz/map" in p.get("partial_path", "")
    )
    assert lou_fusz_result.get("source") == "found_in_shortcode_handler"
    assert lou_fusz_result.get("shortcode") == "full-map"


def test_find_template_parts_in_file_extracts_shortcode_function_partial_path(tmp_path):
    template_file = tmp_path / "template.php"
    template_file.write_text(
        """
        <?php
        function demo_getdirections() {
            if (true) {
                echo 'x';
            }
            get_template_part('partials/homecontent-getdirections');
        }
        """,
        encoding="utf-8",
    )

    partials = maps.find_template_parts_in_file(str(template_file), [])

    shortcode_fn_match = next(
        p for p in partials if p.get("source") == "found_in_shortcode_function"
    )
    assert shortcode_fn_match["partial_path"] == "partials/homecontent-getdirections"


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

    assert result == "copied", "Should copy via fuzzy match"

    # Verify the file was copied to dealer theme
    copied_file = dealer_theme_dir / "partials/dealer-groups/fca/map.php"
    assert copied_file.exists(), "File should be copied to dealer theme"
    assert copied_file.read_text(encoding="utf-8") == "<?php // FCA map partial ?>"


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


# --- AUTO-HEAL TESTS ---


def test_auto_heal_copies_template_partial_for_broken_shortcode(tmp_path, monkeypatch):
    """AC1: When a shortcode partial is missing but a valid template partial exists
    in extra_partials, auto-heal copies the template partial to the shortcode's
    expected destination."""
    # Setup CommonTheme with a valid template partial
    commontheme = tmp_path / "CommonTheme"
    map_dir = commontheme / "map"
    map_dir.mkdir(parents=True)
    section_map = map_dir / "section-map.php"
    section_map.write_text("<?php // section map content ?>", encoding="utf-8")

    # Setup dealer theme dir (no existing file at map/full-map.php)
    dealer_theme = tmp_path / "dealer-themes" / "testdealer"
    dealer_theme.mkdir(parents=True)

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme))
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(dealer_theme))

    # Shortcode partial that will be "skipped_missing" by copy_partial_to_dealer_theme
    shortcode_partial = {
        "template_file": "functions.php (shortcode full-map)",
        "partial_path": "map/full-map",
        "source": "found_in_shortcode_handler",
        "shortcode": "full-map",
        "handler": "fullmap_shortcode_handler",
    }

    # Template partial that exists in CommonTheme
    template_partial = {
        "template_file": "front-page.php",
        "partial_path": "map/section-map",
        "source": "found_in_template",
    }

    success, copied = maps.migrate_map_partials(
        slug="testdealer",
        map_imports=[],
        interactive=False,
        extra_partials=[shortcode_partial, template_partial],
        scan_templates=False,
    )

    # Assert the proxy file was created
    healed_file = dealer_theme / "map" / "full-map.php"
    assert healed_file.exists(), "Auto-healed file should exist at shortcode destination"
    assert healed_file.read_text(encoding="utf-8") == "<?php // section map content ?>"

    # Assert it appears in the copied list
    assert "map/full-map" in copied, "Auto-healed partial should appear in copied list"
    assert success is True


def test_auto_heal_skips_when_no_template_partial_available(tmp_path, monkeypatch, caplog):
    """AC2: When no valid template partial exists in extra_partials, auto-heal is
    skipped and the original skipped_missing status is preserved."""
    commontheme = tmp_path / "CommonTheme"
    commontheme.mkdir(parents=True)

    dealer_theme = tmp_path / "dealer-themes" / "testdealer"
    dealer_theme.mkdir(parents=True)

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme))
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(dealer_theme))

    shortcode_partial = {
        "template_file": "functions.php (shortcode full-map)",
        "partial_path": "map/full-map",
        "source": "found_in_shortcode_handler",
        "shortcode": "full-map",
        "handler": "fullmap_shortcode_handler",
    }

    success, copied = maps.migrate_map_partials(
        slug="testdealer",
        map_imports=[],
        interactive=False,
        extra_partials=[shortcode_partial],
        scan_templates=False,
    )

    # No file should be created
    healed_file = dealer_theme / "map" / "full-map.php"
    assert not healed_file.exists(), "No file should be created when no template partial available"
    assert copied == [], "Copied list should be empty"
    assert success is True  # skipped_missing still counts as success
    assert "Auto-heal skipped for map/full-map" in caplog.text


def test_auto_heal_skips_for_non_shortcode_partials(tmp_path, monkeypatch):
    """Auto-heal logic should NOT trigger for partials with source != found_in_shortcode_handler."""
    commontheme = tmp_path / "CommonTheme"
    map_dir = commontheme / "map"
    map_dir.mkdir(parents=True)
    section_map = map_dir / "section-map.php"
    section_map.write_text("<?php // section map content ?>", encoding="utf-8")

    dealer_theme = tmp_path / "dealer-themes" / "testdealer"
    dealer_theme.mkdir(parents=True)

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme))
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(dealer_theme))

    # A template-sourced partial that points to a non-existent path
    template_partial = {
        "template_file": "front-page.php",
        "partial_path": "map/nonexistent-template",
        "source": "found_in_template",
    }

    # A valid partial that could be used as a proxy source
    valid_partial = {
        "template_file": "front-page.php",
        "partial_path": "map/section-map",
        "source": "found_in_template",
    }

    success, copied = maps.migrate_map_partials(
        slug="testdealer",
        map_imports=[],
        interactive=False,
        extra_partials=[template_partial, valid_partial],
        scan_templates=False,
    )

    # The nonexistent-template should NOT have been auto-healed (it's not a shortcode partial)
    healed_file = dealer_theme / "map" / "nonexistent-template.php"
    assert not healed_file.exists(), "Auto-heal should NOT trigger for non-shortcode partials"
    assert success is True
    assert "map/nonexistent-template" not in copied


def test_auto_heal_handles_filesystem_error_gracefully(tmp_path, monkeypatch):
    """Auto-heal should catch shutil.copy2 errors and not crash the migration."""
    commontheme = tmp_path / "CommonTheme"
    map_dir = commontheme / "map"
    map_dir.mkdir(parents=True)
    section_map = map_dir / "section-map.php"
    section_map.write_text("<?php // content ?>", encoding="utf-8")

    dealer_theme = tmp_path / "dealer-themes" / "testdealer"
    dealer_theme.mkdir(parents=True)

    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme))
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(dealer_theme))

    def mock_copy2(*args, **kwargs):
        raise OSError("Mock filesystem error")

    monkeypatch.setattr(maps.shutil, "copy2", mock_copy2)

    shortcode_partial = {
        "template_file": "functions.php",
        "partial_path": "map/full-map",
        "source": "found_in_shortcode_handler",
        "shortcode": "full-map",
        "handler": "handler",
    }
    template_partial = {
        "template_file": "front-page.php",
        "partial_path": "map/section-map",
        "source": "found_in_template",
    }

    success, copied = maps.migrate_map_partials(
        slug="testdealer",
        map_imports=[],
        interactive=False,
        extra_partials=[shortcode_partial, template_partial],
        scan_templates=False,
    )

    assert success is True
    assert "map/full-map" not in copied
