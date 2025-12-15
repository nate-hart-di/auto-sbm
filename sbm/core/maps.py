"""
Enhanced map components migration for the SBM tool.

This module handles the migration of map components from CommonTheme to DealerTheme
by scanning for CommonTheme @import statements and copying both SCSS and PHP partials.
"""

import os
import re
import shutil
from glob import glob
from pathlib import Path
from typing import Optional

import click

from sbm.utils.logger import logger
from sbm.utils.path import get_dealer_theme_dir

# CommonTheme directory path
COMMON_THEME_DIR = "/Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme"

# Map-related keywords pulled from CommonTheme usage (shortcodes and template parts)
MAP_KEYWORDS = [
    "map",
    "maps",
    "mapsection",
    "section-map",
    "map-row",
    "maprow",
    "map_rt",
    "mapbox",
    "mapboxdirections",
    "full-map",
    "get-directions",
    "getdirections",
    "directions",
]

_MAP_MIGRATION_REPORT = {}


def _set_map_report(slug: str, report: dict) -> None:
    """Persist map migration details for later PR/SF messaging."""
    _MAP_MIGRATION_REPORT[slug] = report


def get_map_report(slug: str) -> Optional[dict]:
    """Get map migration details for a slug."""
    return _MAP_MIGRATION_REPORT.get(slug)


def migrate_map_components(slug, oem_handler=None, interactive=False) -> Optional[bool]:
    """
    Enhanced map components migration that scans for CommonTheme @import statements
    and migrates both SCSS content and PHP partials.

    Args:
        slug (str): Dealer theme slug
        oem_handler (BaseOEMHandler, optional): OEM handler for the dealer
        interactive (bool): Whether to prompt for user confirmation (default: False)

    Returns:
        bool: True if migration was successful, False otherwise
    """
    logger.debug(f"Starting enhanced map components migration for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)
        style_scss_path = os.path.join(theme_dir, "css", "style.scss")

        if not os.path.exists(style_scss_path):
            logger.warning(f"style.scss not found at {style_scss_path}")
            return True  # Not an error, just no style.scss to process

        # Step 1: Find CommonTheme map imports in style.scss
        map_imports = find_commontheme_map_imports(style_scss_path)

        # Step 1b: Discover map shortcodes/partials in functions.php (fallback path)
        shortcode_partials = find_map_shortcodes_in_functions(theme_dir)
        shortcode_map_imports = derive_map_imports_from_partials(shortcode_partials)
        if shortcode_map_imports:
            map_imports.extend(shortcode_map_imports)
            map_imports = dedupe_map_imports(map_imports)

        if not shortcode_partials:
            if map_imports:
                logger.info(
                    "Map SCSS references found but no map shortcodes/template usage detected; "
                    "skipping map migration."
                )
                click.echo("ℹ️ Map SCSS references found but no map shortcodes/template usage detected; skipping map migration.")
                _set_map_report(
                    slug,
                    {
                        "shortcodes_found": False,
                        "imports_found": bool(map_imports),
                        "scss_targets": [],
                        "partials_copied": [],
                        "skipped_reason": "imports_without_shortcodes",
                    },
                )
            else:
                logger.info("No map shortcodes or map SCSS references found; skipping map migration.")
                click.echo("ℹ️ No map shortcodes or map SCSS references found; skipping map migration.")
                _set_map_report(
                    slug,
                    {
                        "shortcodes_found": False,
                        "imports_found": False,
                        "scss_targets": [],
                        "partials_copied": [],
                        "skipped_reason": "none_found",
                    },
                )
            return True

        if not map_imports:
            logger.info("No CommonTheme map imports found; skipping map migration.")
            click.echo("ℹ️ Map shortcodes detected but no CommonTheme map assets found; skipping map migration.")
            _set_map_report(
                slug,
                {
                    "shortcodes_found": True,
                    "imports_found": False,
                    "scss_targets": [],
                    "partials_copied": [],
                    "skipped_reason": "shortcodes_without_assets",
                },
            )
            return True

        # Step 2: Migrate SCSS content to sb-inside.scss and sb-home.scss
        scss_success, scss_targets = migrate_map_scss_content(slug, map_imports)

        # Step 3: Find and migrate corresponding PHP partials
        partials_success, copied_partials = migrate_map_partials(
            slug, map_imports, interactive=interactive, extra_partials=shortcode_partials
        )

        if scss_targets or copied_partials:
            summary = []
            if scss_targets:
                summary.append(f"SCSS appended to: {', '.join(sorted(scss_targets))}")
            if copied_partials:
                summary.append(f"Partials copied: {', '.join(sorted(set(copied_partials)))}")
            message = " | ".join(summary)
            logger.info(f"Map migration summary for {slug}: {message}")
            click.echo(f"📍 Map migration summary: {message}")
            _set_map_report(
                slug,
                {
                    "shortcodes_found": True,
                    "imports_found": True,
                    "scss_targets": scss_targets,
                    "partials_copied": [c for c in copied_partials if c],
                    "skipped_reason": None,
                },
            )
        else:
            _set_map_report(
                slug,
                {
                    "shortcodes_found": True,
                    "imports_found": True,
                    "scss_targets": scss_targets,
                    "partials_copied": [c for c in copied_partials if c],
                    "skipped_reason": "migration_issue",
                },
            )

        if scss_success and partials_success:
            logger.info(f"✅ Enhanced map migration completed successfully for {slug}")
            return True
        logger.warning(f"⚠️ Map migration completed with some issues for {slug}")
        return True  # Don't fail the entire migration for map issues

    except Exception as e:
        logger.error(f"Error during enhanced map migration for {slug}: {e}")
        return False


def find_commontheme_map_imports(style_scss_path):
    """
    Find CommonTheme @import statements that contain "map" in the filename.

    Args:
        style_scss_path (str): Path to style.scss file

    Returns:
        list: List of dictionaries containing import information
    """
    logger.info("Scanning style.scss for CommonTheme map imports...")

    try:
        with open(style_scss_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        map_imports = []

        # Look for @import statements with CommonTheme paths containing map-like keywords
        keyword_pattern = "|".join([re.escape(k) for k in MAP_KEYWORDS])
        import_pattern = (
            r"@import\s+['\"]([^'\"]*DealerInspireCommonTheme[^'\"]*(?:"
            + keyword_pattern
            + r")[^'\"]*)['\"]"
        )
        matches = re.finditer(import_pattern, content, re.IGNORECASE)

        for match in matches:
            import_path = match.group(1)

            # Convert relative path to absolute CommonTheme path
            # Remove leading ../../DealerInspireCommonTheme/ to get relative path within CommonTheme
            commontheme_relative = re.sub(r"^.*?DealerInspireCommonTheme/", "", import_path)
            commontheme_absolute = os.path.join(COMMON_THEME_DIR, commontheme_relative)

            map_import = {
                "original_import": match.group(0),
                "import_path": import_path,
                "commontheme_relative": commontheme_relative,
                "commontheme_absolute": commontheme_absolute,
                "filename": os.path.basename(import_path),
            }

            # Verify the file exists in CommonTheme with several fallbacks:
            # - exact match
            # - underscore prefix
            # - add .scss extension (with and without underscore)
            candidate_paths = [commontheme_absolute]

            filename = os.path.basename(commontheme_absolute)
            directory = os.path.dirname(commontheme_absolute)

            # Underscore prefix
            if not filename.startswith("_"):
                candidate_paths.append(os.path.join(directory, f"_{filename}"))

            # Add .scss if missing
            if not filename.lower().endswith(".scss"):
                candidate_paths.append(f"{commontheme_absolute}.scss")
                if not filename.startswith("_"):
                    candidate_paths.append(os.path.join(directory, f"_{filename}.scss"))

            actual_file_path = next((p for p in candidate_paths if os.path.exists(p)), None)

            if actual_file_path:
                map_import["commontheme_absolute"] = actual_file_path  # Update with actual path
                map_imports.append(map_import)
                logger.info(f"Found map import: {map_import['filename']} at {actual_file_path}")
            else:
                logger.debug(f"CommonTheme file not found (skipping): {commontheme_absolute}")

        if map_imports:
            logger.info(f"Found {len(map_imports)} CommonTheme map imports")
        else:
            logger.info("No CommonTheme map imports found")

        return map_imports

    except Exception as e:
        logger.error(f"Error scanning style.scss for map imports: {e}")
        return []


def dedupe_map_imports(map_imports):
    """Deduplicate map imports by their CommonTheme absolute path."""
    seen = set()
    deduped = []
    for m in map_imports:
        key = m.get("commontheme_absolute")
        if key and key not in seen:
            seen.add(key)
            deduped.append(m)
    return deduped


def find_map_shortcodes_in_functions(theme_dir):
    """
    Scan functions.php AND included shared function files for map/directions shortcodes
    and template parts used within.

    Recursively follows 'require', 'include', 'require_once', 'include_once' statements
    if the referenced file looks like a shared function file (e.g. contains 'dealer-groups'
    or 'function').

    Returns:
        list of partial path dictionaries derived from shortcode handlers.
    """
    start_file = Path(theme_dir) / "functions.php"
    if not start_file.exists():
        logger.info("functions.php not found; skipping shortcode scan")
        return []

    # Queue of files to scan: (Path object, source_context_string)
    files_to_scan = [(start_file, "functions.php")]
    seen_files = {str(start_file.resolve())}
    
    partial_paths = []
    
    # regex for finding include/require statements
    # Matches: require_once( get_template_directory() . '/path/to/file.php' );
    # Matches: include 'path/to/file.php';
    # Matches: require_once( dirname(__FILE__) . '/path/to/file.php' );
    # Matches: require_once( '../../DealerInspireCommonTheme/path/to/file.php' );
    # regex for finding include/require statements
    # Matches: require_once( get_template_directory() . '/path/to/file.php' );
    # Matches: include 'path/to/file.php';
    # Matches: require_once( dirname(__FILE__) . '/path/to/file.php' );
    # Matches: require_once( '../../DealerInspireCommonTheme/path/to/file.php' );
    include_pattern = re.compile(
        r"(?:require_once|include_once|require|include)\s*\(?\s*(.*?)\s*\)?\s*;", 
        re.IGNORECASE
    )

    keyword_pattern = "|".join([re.escape(k) for k in MAP_KEYWORDS])
    shortcode_pattern = (
        r"add_shortcode\s*\(\s*['\"]([^'\"]*(?:" + keyword_pattern + r")[^'\"]*)['\"]\s*,\s*([^\)\s]+)"
    )

    while files_to_scan:
        current_file_path, context = files_to_scan.pop(0)
        
        try:
            content = current_file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Could not read {context}: {e}")
            continue

        logger.debug(f"Scanning {current_file_path.name} for map shortcodes...")

        # 1. Find shortcode registrations in this file
        shortcodes = []
        for match in re.finditer(shortcode_pattern, content, re.IGNORECASE):
            shortcode = match.group(1)
            handler = match.group(2).strip().strip(",")
            shortcodes.append((shortcode, handler))
            logger.info(f"Found shortcode registration in {current_file_path.name}: {shortcode} -> {handler}")

        # 2. Find get_template_part calls in this file (top-level)
        partial_paths.extend(find_template_parts_in_file(str(current_file_path), []))

        # 3. Look inside handler functions for template parts
        for shortcode, handler in shortcodes:
            handler_name = handler.strip("'\"")
            if not handler_name:
                continue

            # Basic function body match for the handler
            function_pattern = (
                r"function\s+"
                + re.escape(handler_name)
                + r"\s*\([^)]*\)\s*\{(?P<body>.*?)\}"
            )
            func_match = re.search(function_pattern, content, re.IGNORECASE | re.DOTALL)
            if not func_match:
                continue

            body = func_match.group("body")
            # Reuse the template-part detection within the function body
            body_matches = re.finditer(
                r"get_template_part\s*\(\s*['\"]([^'\"]*(?:"
                + keyword_pattern
                + r")[^'\"]*)['\"]",
                body,
                re.IGNORECASE,
            )
            for bm in body_matches:
                partial_path = bm.group(1)
                partial_info = {
                    "template_file": f"{current_file_path.name} (shortcode {shortcode})",
                    "partial_path": partial_path,
                    "source": "found_in_shortcode_handler",
                    "shortcode": shortcode,
                    "handler": handler_name,
                }
                logger.info(
                    f"Found map template part via shortcode {shortcode}: {partial_path} (handler {handler_name})"
                )
                partial_paths.append(partial_info)

        # 4. Find included files to recurse into
        # Only relevant for the main functions.php or other shared function files
        # We generally only want to follow paths that look like they might contain shared logic
        include_matches = include_pattern.finditer(content)
        for match in include_matches:
            raw_path_statement = match.group(1)
            
            # Simple heuristic cleaning of PHP string concatenation
            # Remove get_template_directory(), dirname(__FILE__), quotes, dots, parens
            clean_path = raw_path_statement
            clean_path = clean_path.replace("get_template_directory()", "")
            clean_path = clean_path.replace("dirname(__FILE__)", "")
            clean_path = clean_path.replace("__DIR__", "")
            clean_path = clean_path.replace(" . ", "")
            clean_path = clean_path.replace("'", "").replace('"', "")
            clean_path = clean_path.strip().strip("/")

            # Resolve the path
            resolved_path = None
            
            # Case A: Relative to theme (often starts with slash after removal of get_template_directory)
            candidate_theme = Path(theme_dir) / clean_path
            
            # Case B: Relative to CommonTheme (explicit relative path ../..)
            # Only if clean_path starts with ../ or includes DealerInspireCommonTheme
            candidate_common = None
            if "DealerInspireCommonTheme" in clean_path or clean_path.startswith(".."):
                # Try to resolve relative to current file's directory first
                candidate_common = (current_file_path.parent / clean_path).resolve()
            
            if candidate_theme.exists() and candidate_theme.is_file():
                resolved_path = candidate_theme
            elif candidate_common and candidate_common.exists() and candidate_common.is_file():
                resolved_path = candidate_common
            
            # If we found a file, check if we should scan it
            if resolved_path:
                resolved_str = str(resolved_path.resolve())
                if resolved_str in seen_files:
                    continue
                
                # Filter: Only scan if it looks like a shared function/dealer-group file
                # The user specifically mentioned "dealer-groups" and "function" (filename/path)
                # Loose check: "dealer-groups" in path OR "function" in filename
                tags = ["dealer-groups", "shared-functions", "functions"]
                
                # Check 1: Is it in a 'dealer-groups' directory?
                is_dealer_group = "dealer-groups" in str(resolved_path)
                
                # Check 2: Does filename have 'functions' in it?
                has_function_name = "function" in resolved_path.name.lower()
                
                if is_dealer_group or has_function_name:
                    logger.debug(f"Queuing shared function file for scan: {resolved_path.name}")
                    seen_files.add(resolved_str)
                    files_to_scan.append((resolved_path, f"included from {current_file_path.name}"))
        
        # Safety break to prevent infinite loops if something goes wrong with path resolution
        if len(seen_files) > 100:
            logger.warning("Scanned more than 100 function files, stopping recursion for safety.")
            break

    return partial_paths


def derive_map_imports_from_partials(partial_paths):
    """
    Derive CommonTheme SCSS paths from partial paths when no explicit @import is present.
    """
    imports = []
    for partial in partial_paths:
        partial_path = partial.get("partial_path", "")
        if not partial_path:
            continue

        # Normalize and construct a likely SCSS path in CommonTheme
        normalized = partial_path.lstrip("/")
        if normalized.startswith("partials/"):
            normalized = normalized[len("partials/") :]

        scss_relative = f"css/{normalized}"
        if not scss_relative.lower().endswith(".scss"):
            scss_relative = f"{scss_relative}.scss"

        commontheme_absolute = os.path.join(COMMON_THEME_DIR, scss_relative)

        # Try common variants (underscore prefix, already handled via find_commontheme_map_imports logic)
        filename = os.path.basename(commontheme_absolute)
        directory = os.path.dirname(commontheme_absolute)

        candidates = [commontheme_absolute]
        if not filename.startswith("_"):
            candidates.append(os.path.join(directory, f"_{filename}"))

        actual_path = next((p for p in candidates if os.path.exists(p)), None)
        if not actual_path:
            logger.debug(f"Could not resolve SCSS for partial-derived path: {scss_relative}")
            continue

        imports.append(
            {
                "original_import": f"derived_from_partial:{partial_path}",
                "import_path": scss_relative,
                "commontheme_relative": scss_relative,
                "commontheme_absolute": actual_path,
                "filename": os.path.basename(actual_path),
            }
        )

    return imports


def migrate_map_scss_content(slug, map_imports):
    """
    Migrate SCSS content from CommonTheme map files to sb-inside.scss and sb-home.scss.

    Args:
        slug (str): Dealer theme slug
        map_imports (list): List of map import dictionaries

    Returns:
        bool: True if successful, False otherwise
    """
    if not map_imports:
        return True, []

    logger.info(f"Migrating map SCSS content for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)
        sb_inside_path = os.path.join(theme_dir, "sb-inside.scss")
        sb_home_path = os.path.join(theme_dir, "sb-home.scss")
        targets_written = []

        # 1. Pre-scan existing SCSS files for imports
        existing_imports = set()
        # candidate files to check for existing imports
        check_files = [
            sb_inside_path, 
            sb_home_path,
            os.path.join(theme_dir, "css", "style.scss"),
            os.path.join(theme_dir, "css", "inside.scss"),
            os.path.join(theme_dir, "style.scss")
        ]

        for check_path in check_files:
            if os.path.exists(check_path):
                try:
                    with open(check_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Find @import statements
                        # Match: @import "..." or @import '...'
                        # We just want to grab the filename part of the import path
                        import_matches = re.findall(r"@import\s*['\"]([^'\"]+)['\"]", content)
                        for imp in import_matches:
                            # Extract basename without extension or underscore
                            base = os.path.basename(imp)
                            base = base.replace(".scss", "").replace(".css", "")
                            if base.startswith("_"):
                                base = base[1:]
                            existing_imports.add(base)
                except Exception as e:
                    logger.warning(f"Error scanning {check_path} for imports: {e}")

        # 2. Filter imports to migrate
        filtered_imports = []
        for map_import in map_imports:
            # Check if this import is already present
            filename = map_import.get("filename", "") 
            # filename is like "map-row-2.scss" or "_map-row-2.scss"
            base = filename.replace(".scss", "")
            if base.startswith("_"):
                base = base[1:]
            
            if base in existing_imports:
                logger.info(f"Skipping SCSS migration for {base} (already imported)")
                continue
            
            filtered_imports.append(map_import)

        if not filtered_imports:
            logger.info("All map SCSS already present in dealer theme.")
            return True, []

        # Collect all map SCSS content
        all_map_content = []

        for map_import in filtered_imports:
            try:
                with open(
                    map_import["commontheme_absolute"], encoding="utf-8", errors="ignore"
                ) as f:
                    scss_content = f.read()
                
                # Add header comment
                map_section = f"""
/* {map_import["filename"]} - Migrated from CommonTheme */
{scss_content}
"""
                all_map_content.append(map_section)
                logger.info(f"Read SCSS content from {map_import['filename']}")

            except Exception as e:
                logger.warning(
                    f"Could not read SCSS content from {map_import['commontheme_absolute']}: {e}"
                )

        if not all_map_content:
            logger.warning("No SCSS content to migrate")
            return True, []

        # Combine all map content
        combined_content = "\n".join(all_map_content)

        # Add to sb-inside.scss
        if os.path.exists(sb_inside_path):
            with open(sb_inside_path, "a", encoding="utf-8") as f:
                f.write("\n\n/* === MAP COMPONENTS === */")
                f.write(combined_content)
            logger.info("Added map SCSS content to sb-inside.scss")
            targets_written.append("sb-inside.scss")
        else:
            logger.warning("sb-inside.scss not found")

        # Add to sb-home.scss
        if os.path.exists(sb_home_path):
            with open(sb_home_path, "a", encoding="utf-8") as f:
                f.write("\n\n/* === MAP COMPONENTS === */")
                f.write(combined_content)
            logger.info("Added map SCSS content to sb-home.scss")
            targets_written.append("sb-home.scss")
        else:
            logger.warning("sb-home.scss not found")

        return True, targets_written

    except Exception as e:
        logger.error(f"Error migrating map SCSS content: {e}")
        return False, []


def migrate_map_partials(slug, map_imports, interactive=False, extra_partials=None):
    """
    Find and migrate corresponding PHP partials for map components.

    Args:
        slug (str): Dealer theme slug
        map_imports (list): List of map import dictionaries
        interactive (bool): Whether to prompt for user confirmation (default: False)

    Returns:
        bool: True if successful, False otherwise
    """
    if not map_imports and not extra_partials:
        return True, []

    logger.info(f"Migrating map PHP partials for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)

        # Look for PHP partials in front-page.php and other template files
        template_files = [
            os.path.join(theme_dir, "front-page.php"),
            os.path.join(theme_dir, "index.php"),
            os.path.join(theme_dir, "page.php"),
            os.path.join(theme_dir, "home.php"),
            os.path.join(theme_dir, "functions.php"),  # Add functions.php for shortcode functions
        ]

        # Also check partials directory
        partials_dir = os.path.join(theme_dir, "partials")
        if os.path.exists(partials_dir):
            template_files.extend(glob(os.path.join(partials_dir, "**/*.php"), recursive=True))

        partial_paths = []

        # Scan template files for get_template_part calls
        for template_file in template_files:
            if os.path.exists(template_file):
                partial_paths.extend(find_template_parts_in_file(template_file, map_imports))

        if not partial_paths:
            # If no partials found in templates, try to guess based on SCSS paths
            partial_paths = guess_partial_paths_from_scss(map_imports)

        # Include any extra partials discovered via shortcodes/functions
        if extra_partials:
            partial_paths.extend(extra_partials)

        # Copy partials from CommonTheme to DealerTheme
        success_count = 0
        copied = []
        processed_paths = set()

        for partial_info in partial_paths:
            p_path = partial_info.get("partial_path")
            if p_path in processed_paths:
                continue
            processed_paths.add(p_path)

            if copy_partial_to_dealer_theme(slug, partial_info, interactive=interactive):
                success_count += 1
                copied.append(p_path)

        logger.info(f"Successfully migrated {success_count}/{len(partial_paths)} map partials")
        return (success_count > 0 or len(partial_paths) == 0), copied

    except Exception as e:
        logger.error(f"Error migrating map partials: {e}")
        return False, []


def find_template_parts_in_file(template_file, map_imports):
    """
    Find get_template_part calls and custom map functions that might correspond to map imports.

    Args:
        template_file (str): Path to template file
        map_imports (list): List of map import dictionaries

    Returns:
        list: List of partial path dictionaries
    """
    try:
        with open(template_file, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        partial_paths = []

        keyword_pattern = "|".join([re.escape(k) for k in MAP_KEYWORDS])

        # 1. Look for get_template_part calls that contain map keywords
        template_part_pattern = (
            r"get_template_part\s*\(\s*['\"]([^'\"]*(?:"
            + keyword_pattern
            + r")[^'\"]*)['\"]"
        )
        matches = re.finditer(template_part_pattern, content, re.IGNORECASE)

        for match in matches:
            partial_path = match.group(1)

            partial_info = {
                "template_file": template_file,
                "partial_path": partial_path,
                "source": "found_in_template",
            }

            logger.info(
                f"Found map template part: {partial_path} in {os.path.basename(template_file)}"
            )
            partial_paths.append(partial_info)

        # 2. Look for get_template_part calls with "directions" or "getdirections"
        directions_pattern = (
            r"get_template_part\s*\(\s*['\"]([^'\"]*(?:"
            + keyword_pattern
            + r")[^'\"]*)['\"]"
        )
        matches = re.finditer(directions_pattern, content, re.IGNORECASE)

        for match in matches:
            partial_path = match.group(1)

            partial_info = {
                "template_file": template_file,
                "partial_path": partial_path,
                "source": "found_directions_partial",
            }

            logger.info(
                f"Found directions template part: {partial_path} in {os.path.basename(template_file)}"
            )
            partial_paths.append(partial_info)

        # 3. Look for custom shortcode functions that call directions partials
        # Pattern: function xyz_map() { ... get_template_part('...directions...') ... }
        # More flexible pattern to match your full_map() function
        shortcode_function_pattern = r"function\s+(\w*(?:map|directions)\w*)\s*\([^)]*\)\s*\{[^}]*get_template_part\s*\(\s*['\"]([^'\"]*(?:directions|getdirections|map)[^'\"]*)['\"]"
        matches = re.finditer(shortcode_function_pattern, content, re.IGNORECASE | re.DOTALL)

        for match in matches:
            function_name = match.group(1)
            partial_path = match.group(2)

            partial_info = {
                "template_file": template_file,
                "partial_path": partial_path,
                "source": "found_in_shortcode_function",
                "function_name": function_name,
            }

            logger.info(
                f"Found map shortcode function: {function_name}() calling {partial_path} in {os.path.basename(template_file)}"
            )
            partial_paths.append(partial_info)

        # 4. Specifically look for homecontent-getdirections pattern
        homecontent_pattern = r"get_template_part\s*\(\s*['\"]([^'\"]*homecontent[^'\"]*directions[^'\"]*)['\"]"
        matches = re.finditer(homecontent_pattern, content, re.IGNORECASE)

        for match in matches:
            partial_path = match.group(1)

            partial_info = {
                "template_file": template_file,
                "partial_path": partial_path,
                "source": "found_homecontent_directions",
            }

            logger.info(
                f"Found homecontent-getdirections partial: {partial_path} in {os.path.basename(template_file)}"
            )
            partial_paths.append(partial_info)

        return partial_paths

    except Exception as e:
        logger.warning(f"Error scanning template file {template_file}: {e}")
        return []


def guess_partial_paths_from_scss(map_imports):
    """
    Guess partial paths based on SCSS import paths when not found in templates.

    Args:
        map_imports (list): List of map import dictionaries

    Returns:
        list: List of guessed partial path dictionaries
    """
    partial_paths = []

    for map_import in map_imports:
        # Convert SCSS path to potential partial path
        # Example: css/dealer-groups/maserati/maseratioem3/section-map.scss
        # Becomes: partials/dealer-groups/maserati/maseratioem3/section-map

        scss_path = map_import["commontheme_relative"]

        # Remove css/ prefix and .scss suffix
        partial_path = scss_path.replace("css/", "").replace(".scss", "")

        # Add partials/ prefix if not already present
        if not partial_path.startswith("partials/"):
            partial_path = f"partials/{partial_path}"

        partial_info = {
            "partial_path": partial_path,
            "template_file": "guessed_from_scss",
            "related_scss": map_import["filename"],
            "is_guess": True,
        }

        partial_paths.append(partial_info)
        logger.info(f"Guessed partial path: {partial_path}")

    return partial_paths


def copy_partial_to_dealer_theme(slug, partial_info, interactive=False) -> Optional[bool]:
    """
    Copy a PHP partial from CommonTheme to DealerTheme with proper directory structure.

    Args:
        slug (str): Dealer theme slug
        partial_info (dict): Partial information dictionary
        interactive (bool): Whether to prompt for user confirmation (default: False)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        theme_dir = get_dealer_theme_dir(slug)
        partial_path = partial_info["partial_path"]
        
        # Use the exact path from template part call for CommonTheme
        commontheme_partial_path = partial_path.lstrip("/")
        
        # 1. Check if file already exists in Dealer Theme FIRST
        dealer_dest_file = os.path.join(theme_dir, f"{commontheme_partial_path}.php")
        dealer_dest_dir = os.path.dirname(dealer_dest_file)

        if os.path.exists(dealer_dest_file):
            logger.info(
                f"✅ Partial already exists in dealer theme: {os.path.relpath(dealer_dest_file, theme_dir)}"
            )
            return True

        # 2. If not in dealer theme, THEN check CommonTheme
        commontheme_source = os.path.join(COMMON_THEME_DIR, f"{commontheme_partial_path}.php")

        # Verify source exists
        if not os.path.exists(commontheme_source):
            logger.warning(f"CommonTheme partial not found: {commontheme_source}")

            # If it's a guess, ask user for confirmation (only in interactive mode)
            if partial_info.get("is_guess"):
                if interactive:
                    click.echo(f"\n🤔 Guessed partial not found: {commontheme_partial_path}.php")
                    click.echo(f"Related SCSS: {partial_info['related_scss']}")

                    # Try to find similar files
                    similar_files = find_similar_partials(commontheme_partial_path)
                    if similar_files:
                        click.echo("Similar files found:")
                        for similar_file in similar_files[:3]:  # Show top 3
                            click.echo(f"  - {similar_file}")

                    return click.confirm("Skip this partial?", default=True)
                # In non-interactive mode, automatically skip missing guessed partials
                logger.warning(f"Skipping missing guessed partial: {commontheme_partial_path}.php")
                return True

            return False

        # Create directory structure only if it doesn't exist
        os.makedirs(dealer_dest_dir, exist_ok=True)

        # Copy the file
        shutil.copy2(commontheme_source, dealer_dest_file)

        logger.info(f"✅ Copied partial: {os.path.basename(commontheme_partial_path)}.php")
        logger.info(f"   From: {commontheme_source}")
        logger.info(f"   To: {dealer_dest_file}")

        return True

    except Exception as e:
        logger.error(f"Error copying partial {partial_info['partial_path']}: {e}")
        return False


def find_similar_partials(partial_path):
    """
    Find similar partial files in CommonTheme when exact match is not found.

    Args:
        partial_path (str): The partial path we're looking for

    Returns:
        list: List of similar partial paths
    """
    try:
        # Extract key components from the path
        path_parts = partial_path.split("/")
        search_terms = [part for part in path_parts if "map" in part.lower() or len(part) > 3]

        # Search in CommonTheme partials directory
        search_base = os.path.join(COMMON_THEME_DIR, "partials")
        if not os.path.exists(search_base):
            return []

        similar_files = []

        # Walk through CommonTheme partials
        for root, _dirs, files in os.walk(search_base):
            for file in files:
                if file.endswith(".php"):
                    relative_path = os.path.relpath(os.path.join(root, file), search_base)

                    # Check if any search terms match
                    if any(term.lower() in relative_path.lower() for term in search_terms):
                        similar_files.append(relative_path.replace(".php", ""))

        return similar_files[:5]  # Return top 5 matches

    except Exception as e:
        logger.warning(f"Error finding similar partials: {e}")
        return []


# Legacy functions kept for backward compatibility
def find_map_shortcodes(slug, shortcode_patterns=None):
    """Legacy function - kept for backward compatibility."""
    logger.info("Using legacy map shortcode detection")
    return []


def identify_map_partials(slug, oem_handler=None):
    """Legacy function - kept for backward compatibility."""
    logger.info("Using legacy map partial identification")
    return []


def copy_map_partials(slug, map_partials) -> bool:
    """Legacy function - kept for backward compatibility."""
    logger.info("Using legacy map partial copying")
    return True


def migrate_map_styles(slug, oem_handler=None) -> bool:
    """Legacy function - kept for backward compatibility."""
    logger.info("Using legacy map styles migration")
    return True
