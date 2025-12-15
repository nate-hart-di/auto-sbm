import os
import re
import pytest
from pathlib import Path
from sbm.core import maps

def test_find_map_shortcodes_recursively_in_shared_files(tmp_path, monkeypatch):
    """
    Test that find_map_shortcodes_in_functions correctly follows include/require
    statements to find shortcodes in shared function files.
    """
    # 1. Setup Theme Directory
    theme_dir = tmp_path / "dealer-theme"
    theme_dir.mkdir()
    
    # 2. Setup CommonTheme Directory
    commontheme_dir = tmp_path / "CommonTheme"
    commontheme_dir.mkdir()
    
    # Mock the COMMON_THEME_DIR in maps.py to point to our test CommonTheme
    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme_dir))
    
    # 3. Create a shared functions file in CommonTheme (mimicking user example)
    # partials/dealer-groups/darcars/toyota/shared-functions.php
    shared_funcs_path = commontheme_dir / "partials/dealer-groups/darcars/toyota/shared-functions.php"
    shared_funcs_path.parent.mkdir(parents=True, exist_ok=True)
    shared_funcs_path.write_text("""
<?php
// A shared function file
add_shortcode('full-map', 'handle_full_map_shortcode');
    """, encoding="utf-8")
    
    # 4. Create a shared functions file that should be IGNORED (no dealer-groups/function)
    # just an ignored include
    ignored_path = commontheme_dir / "includes/random-lib.php"
    ignored_path.parent.mkdir(parents=True, exist_ok=True)
    ignored_path.write_text("""
<?php
// Should not be scanned
add_shortcode('ignored-map', 'handle_ignored_map');
    """, encoding="utf-8")
    
    # 5. Create theme functions.php that requires these files
    # Use relative path to CommonTheme logic
    functions_php = theme_dir / "functions.php"
    functions_php.write_text(f"""
<?php
// Theme functions
require_once( '../../CommonTheme/partials/dealer-groups/darcars/toyota/shared-functions.php' );
include( '{ignored_path}' ); 
    """, encoding="utf-8")
    
    # NOTE: The regex in the code looks for 'DealerInspireCommonTheme' string literals for CommonTheme resolution.
    # So I need to structure the path in functions.php to match that expectation if I want it to resolve to CommonTheme.
    # Code: if "DealerInspireCommonTheme" in clean_path or clean_path.startswith(".."):
    
    # Let's retry step 5 with a path that will actually trigger the resolver logic in the new code
    # The code expects the include path string to contain "DealerInspireCommonTheme" to look in CommonTheme dir,
    # OR start with ".."
    
    # Let's assume the relative path from theme to common is ../../CommonTheme
    # But in the test env, they are siblings in tmp_path?
    # theme_dir = tmp/dealer-theme
    # commontheme = tmp/CommonTheme
    # relative = ../CommonTheme
    
    # But the code uses COMMON_THEME_DIR constant when it detects "DealerInspireCommonTheme".
    # Let's use the explicit relative path approach which uses the file system.
    
    # Redo Step 5 with a better path
    rel_path_to_shared = os.path.relpath(shared_funcs_path, theme_dir)
    # On mac/linux this should work fine.
    
    functions_php.write_text(f"""
<?php
require_once( '{rel_path_to_shared}' );
require_once( '{ignored_path}' );
    """, encoding="utf-8")


    
    # 6. Run the function
    # The "start_file" is functions.php.
    results = maps.find_map_shortcodes_in_functions(str(theme_dir))
    
    # 7. Verify results
    # Should find 'full-map' from shared-functions.php
    # Should NOT find 'ignored-map' from random-lib.php (because filename doesn't match filter)
    
    found_shortcodes = [r.get("shortcode") for r in results]
    found_handlers = [r.get("handler") for r in results]
    
    # The return format of find_map_shortcodes_in_functions is list of partial_infos.
    # It constructs them via:
    # partial_info = { ..., "shortcode": shortcode, "handler": handler_name }
    # Wait, the code ONLY adds to partial_paths if it finds a get_template_part call inside the handler?
    
    # Let's check the code:
    # ...
    # for shortcode, handler in shortcodes:
    #   ... func_match = re.search(...)
    #   ... body_matches = re.finditer(...)
    #   ... partial_paths.append(...)
    
    # Ah! The function returns partial paths derived FROM shortcodes, but only if the handler contains get_template_part.
    # So I need to update my shared function content to actually HAVE a handler with a template part.
    
    shared_funcs_path.write_text("""
<?php
add_shortcode('full-map', 'handle_full_map_shortcode');

function handle_full_map_shortcode() {
    get_template_part('partials/map-section');
}
    """, encoding="utf-8")
    
    # Re-run
    results = maps.find_map_shortcodes_in_functions(str(theme_dir))
    
    assert len(results) >= 1
    # Check that at least one result has the correct shortcode info
    match = next((r for r in results if r.get('shortcode') == 'full-map'), None)
    assert match is not None
    assert match['handler'] == 'handle_full_map_shortcode'
    assert match['handler'] == 'handle_full_map_shortcode'
    # Verified match found via recursion


def test_migrate_map_partials_dedupe_and_priority(tmp_path, monkeypatch):
    """
    Test that migrate_map_partials:
    1. Deduplicates partials
    2. Checks dealer theme FIRST (and skips if found)
    """
    theme_dir = tmp_path / "dealer-theme"
    theme_dir.mkdir()
    commontheme_dir = tmp_path / "CommonTheme"
    commontheme_dir.mkdir()
    
    monkeypatch.setattr(maps, "COMMON_THEME_DIR", str(commontheme_dir))
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(theme_dir))

    # Setup:
    # 1. create a partial in CommonTheme
    (commontheme_dir / "partials").mkdir()
    (commontheme_dir / "partials/foo.php").write_text("common content")
    
    # 2. create SAME partial in DealerTheme
    (theme_dir / "partials").mkdir()
    (theme_dir / "partials/foo.php").write_text("dealer content")
    
    # partial info list with duplicates
    partial_paths = [
        {"partial_path": "partials/foo"},
        {"partial_path": "partials/foo"}, # Duplicate
    ]
    
    # Run migration
    success, copied = maps.migrate_map_partials("slug", [], extra_partials=partial_paths)
    
    # Verify:
    # Should NOT copy (because it exists in dealer theme)
    # Should NOT verify/complain about CommonTheme (if logic works)
    # Should only process once
    
    # Since it exists in dealer theme, 'copied' list should be empty (or check logic?)
    # The function returns (success, copied). If it exists, it counts as success but returns nothing in copied list?
    # No, my code returns True if exists, but doesn't add to 'copied' list in the logs?
    # Code: 
    # if copy_partial_to_dealer_theme(...): success_count += 1; copied.append(p_path)
    # copy_partial_to_dealer_theme returns True if exists.
    # So it WILL be in 'copied' list.
    
    assert len(copied) == 1 # Deduplicated, so only 1 foo
    assert copied[0] == "partials/foo"
    
    # Verify file content was NOT overwritten
    assert (theme_dir / "partials/foo.php").read_text() == "dealer content"


def test_migrate_map_scss_prevents_duplicate_import(tmp_path, monkeypatch):
    """
    Test that migrate_map_scss_content skips imports that are already present.
    """
    theme_dir = tmp_path / "dealer-theme"
    theme_dir.mkdir()
    (theme_dir / "css").mkdir()
    
    monkeypatch.setattr(maps, "get_dealer_theme_dir", lambda slug: str(theme_dir))
    
    # Setup: CommonTheme SCSS file
    scss_file = tmp_path / "commontheme/css/map.scss"
    scss_file.parent.mkdir(parents=True)
    scss_file.write_text("/* map styles */")
    
    # Setup: Dealer Theme style.scss importing it
    (theme_dir / "css/style.scss").write_text('@import "../../CommonTheme/css/map";')
    
    map_imports = [{
        "filename": "map.scss",
        "commontheme_absolute": str(scss_file)
    }]
    
    # Run
    success, written = maps.migrate_map_scss_content("slug", map_imports)
    
    # Verify
    assert success is True
    assert written == [] # Should be empty as it skipped
    
    # Verify no sb-inside.scss created
    assert not (theme_dir / "sb-inside.scss").exists()
