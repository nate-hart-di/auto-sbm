"""
Enhanced map components migration for the SBM tool.

This module handles the migration of map components from CommonTheme to DealerTheme
by scanning for CommonTheme @import statements and copying both SCSS and PHP partials.
"""

import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

import click

from sbm.ui.console import SBMConsole
from sbm.utils.logger import logger
from sbm.utils.path import get_dealer_theme_dir
from typing import Any

# CommonTheme directory path
COMMON_THEME_DIR = "/Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme"

# Map-related keywords pulled from CommonTheme usage (shortcodes and template parts)
# We use more specific patterns to avoid false positives like "sitemap" or "map-link"
MAP_KEYWORDS = [
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
]

# Shared regex for map shortcodes and template parts
MAP_REGEX_PATTERN = r"(?i)\W(?:mapsection|section-map|map-row|maprow|map_rt|mapbox|mapboxdirections|full-map|get-directions|getdirections)\W"


def remove_php_comments(content: str) -> str:
    """Remove PHP comments (/* */, //, #) from content."""
    # Remove block comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove single line comments (// and #)
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
    return content


def remove_scss_comments(content: str) -> str:
    """Remove SCSS comments (/* */, //) from content."""
    # Remove block comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove single line comments (//)
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    return content


_MAP_MIGRATION_REPORT: Dict[str, dict] = {}


def _set_map_report(slug: str, report: dict) -> None:
    """Persist map migration details for later PR/SF messaging."""
    _MAP_MIGRATION_REPORT[slug] = report


def get_map_report(slug: str) -> Optional[dict]:
    """Get map migration details for a slug."""
    return _MAP_MIGRATION_REPORT.get(slug)


def migrate_map_components(
    slug: str,
    oem_handler: Optional[Union[dict, object]] = None,
    interactive: bool = False,
    console: Optional[SBMConsole] = None,
    processor: Optional[Any] = None,
) -> bool:
    """
    Enhanced map components migration that scans for CommonTheme @import statements
    and migrates both SCSS content and PHP partials.

    Args:
        slug: Dealer theme slug
        oem_handler: OEM handler for the dealer
        interactive: Whether to prompt for user confirmation (default: False)
        console: Optional console instance for unified UI.
        processor: Optional SCSSProcessor instance for content transformation.

    Returns:
        bool: True if migration was successful, False otherwise
    """
    logger.debug(f"Starting enhanced map components migration for {slug}")

    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        style_scss_path = theme_dir / "css" / "style.scss"

        if not style_scss_path.exists():
            logger.warning(f"style.scss not found at {style_scss_path}")
            return True  # Not an error, just no style.scss to process

        # Step 1: Find CommonTheme map imports in style.scss
        map_imports = find_commontheme_map_imports(style_scss_path, oem_handler)

        # Step 1b: Discover map shortcodes/partials in functions.php (fallback path)
        shortcode_partials = find_map_shortcodes_in_functions(str(theme_dir), oem_handler)
        shortcode_map_imports = derive_map_imports_from_partials(shortcode_partials)
        if shortcode_map_imports:
            map_imports.extend(shortcode_map_imports)
            map_imports = dedupe_map_imports(map_imports)

        if not shortcode_partials and not map_imports:
            # Only skip if NEITHER shortcodes nor imports are found.
            if console:
                console.print_info("i No map components detected; skipping map migration.")
            else:
                click.echo("i No map components detected; skipping map migration.")
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

        if not map_imports and not shortcode_map_imports:
            # Case: Shortcodes found, but no assets found in CommonTheme to migrate
            # logic handled below...
            pass

        if not map_imports:
            logger.info(
                "No CommonTheme map imports found, but shortcodes detected. Proceeding with partial migration."
            )
            if console:
                console.print_info(
                    "i Map shortcodes detected but no CommonTheme map assets found; checking for partials..."
                )
            else:
                click.echo(
                    "i Map shortcodes detected but no CommonTheme map assets found; checking for partials..."
                )

        # Step 2: Migrate SCSS content to sb-inside.scss and sb-home.scss
        scss_success, scss_targets = migrate_map_scss_content(
            slug, map_imports, processor=processor
        )

        # Step 3: Find and migrate corresponding PHP partials
        partials_success, copied_partials = migrate_map_partials(
            slug,
            map_imports,
            interactive=interactive,
            extra_partials=shortcode_partials,
            oem_handler=oem_handler,
        )

        if scss_targets or copied_partials:
            summary = []

            from sbm.oem.default import DefaultHandler

            is_oem = oem_handler and not isinstance(oem_handler, DefaultHandler)
            # Use name from handler class or instance
            oem_name = getattr(oem_handler, "name", "OEM") if is_oem else ""
            prefix = f"[{oem_name}] " if is_oem else ""

            if scss_targets:
                summary.append(f"SCSS appended to: {', '.join(sorted(scss_targets))}")
            if copied_partials:
                summary.append(f"Partials copied: {', '.join(sorted(set(copied_partials)))}")

            message = " | ".join(summary)
            logger.info(f"Map migration summary for {slug}: {message}")
            if console:
                console.print_info(f"📍 {prefix}Map migration summary: {message}")
            else:
                click.echo(f"📍 {prefix}Map migration summary: {message}")
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
            # If arrays are empty but success is True, it means everything was already there.
            if scss_success and partials_success:
                reason = "already_present"
                logger.info("Map components already present in dealer theme; no changes needed.")
            else:
                reason = "migration_issue"

            _set_map_report(
                slug,
                {
                    "shortcodes_found": True,
                    "imports_found": True,
                    "scss_targets": scss_targets,
                    "partials_copied": [c for c in copied_partials if c],
                    "skipped_reason": reason,
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


def find_commontheme_map_imports(
    style_scss_path: Union[str, Path], oem_handler: Optional[object] = None
) -> List[dict]:
    """
    Find CommonTheme @import statements that contain "map" in the filename.

    Args:
        style_scss_path: Path to style.scss file
        oem_handler: Optional OEM handler to use for specific patterns

    Returns:
        list: List of dictionaries containing import information
    """
    logger.info("Scanning style.scss for CommonTheme map imports...")

    try:
        path_style_scss = Path(style_scss_path)
        raw_content = path_style_scss.read_text(encoding="utf-8", errors="ignore")
        content = remove_scss_comments(raw_content)

        map_imports = []

        # Determine patterns to search for
        from sbm.oem.default import DefaultHandler

        is_oem = oem_handler and not isinstance(oem_handler, DefaultHandler)

        if is_oem and hasattr(oem_handler, "get_map_partial_patterns"):
            search_patterns = oem_handler.get_map_partial_patterns()
            logger.info(f"Using {len(search_patterns)} OEM-specific map patterns")
        else:
            # Default mode: Use generic keywords with start-of-segment boundary
            keyword_list = "|".join([re.escape(k) for k in MAP_KEYWORDS])
            search_patterns = [f"DealerInspireCommonTheme[^'\"]*(?:/|_)\\b(?:{keyword_list})"]
            logger.info("Using generic map keyword patterns with segment boundary")

        for pattern in search_patterns:
            import_pattern = r"@import\s+['\"]([^'\"]*" + pattern + r"[^'\"]*)['\"]"
            matches = re.finditer(import_pattern, content, re.IGNORECASE)

            for match in matches:
                import_path = match.group(1)

                # Convert relative path to absolute CommonTheme path
                # Remove leading ../../DealerInspireCommonTheme/ to get relative path within CommonTheme
                commontheme_relative = re.sub(r"^.*?DealerInspireCommonTheme/", "", import_path)
                commontheme_absolute = Path(COMMON_THEME_DIR) / commontheme_relative

                map_import = {
                    "original_import": match.group(0),
                    "import_path": import_path,
                    "commontheme_relative": commontheme_relative,
                    "commontheme_absolute": str(commontheme_absolute),
                    "filename": commontheme_absolute.name,
                }

                # Verify the file exists in CommonTheme with several fallbacks
                filename = commontheme_absolute.name
                directory = commontheme_absolute.parent

                candidate_paths = [commontheme_absolute]

                # Underscore prefix
                if not filename.startswith("_"):
                    candidate_paths.append(directory / f"_{filename}")

                # Add .scss if missing
                if not filename.lower().endswith(".scss"):
                    candidate_paths.append(commontheme_absolute.with_suffix(".scss"))
                    if not filename.startswith("_"):
                        candidate_paths.append(directory / f"_{filename}.scss")

                actual_file_path = next((p for p in candidate_paths if p.exists()), None)

                if actual_file_path:
                    map_import["commontheme_absolute"] = str(actual_file_path)
                    map_imports.append(map_import)
                    logger.debug(
                        f"Found map import: {map_import['filename']} at {actual_file_path}"
                    )
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


def dedupe_map_imports(map_imports: List[dict]) -> List[dict]:
    """Deduplicate map imports by their CommonTheme absolute path."""
    seen = set()
    deduped = []
    for m in map_imports:
        key = m.get("commontheme_absolute")
        if key and key not in seen:
            seen.add(key)
            deduped.append(m)
    return deduped


def find_map_shortcodes_in_functions(
    theme_dir: str, oem_handler: Optional[object] = None
) -> List[dict]:
    """
    Scan functions.php AND included shared function files for map/directions shortcodes
    and template parts used within.

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
        r"(?:require_once|include_once|require|include)\s*\(?\s*(.*?)\s*\)?\s*;", re.IGNORECASE
    )

    keyword_pattern = "|".join([re.escape(k) for k in MAP_KEYWORDS])
    # Search specifically for 'full-map' shortcode (AC1: Fix map detection)
    shortcode_pattern = r"add_shortcode\s*\(\s*['\"]full-map['\"]\s*,\s*([^\)\s]+)"

    while files_to_scan:
        current_file_path, context = files_to_scan.pop(0)

        try:
            raw_content = current_file_path.read_text(encoding="utf-8", errors="ignore")
            content = remove_php_comments(raw_content)
        except Exception as e:
            logger.warning(f"Could not read {context}: {e}")
            continue

        logger.debug(f"Scanning {current_file_path.name} for map shortcodes...")

        # 1. Find shortcode registrations in this file
        shortcodes = []
        for match in re.finditer(shortcode_pattern, content, re.IGNORECASE):
            # Pattern now matches 'full-map' specifically, so shortcode is always 'full-map'
            shortcode = "full-map"
            handler = match.group(1).strip().strip(",")
            shortcodes.append((shortcode, handler))
            logger.info(
                f"Found shortcode registration in {current_file_path.name}: {shortcode} -> {handler}"
            )

        # 2. Find get_template_part calls in this file (top-level)
        partial_paths.extend(find_template_parts_in_file(str(current_file_path), [], oem_handler))

        # 3. Look inside handler functions for template parts
        for shortcode, handler in shortcodes:
            handler_name = handler.strip("'\"")
            if not handler_name:
                continue

            # Basic function body match for the handler
            function_pattern = (
                r"function\s+" + re.escape(handler_name) + r"\s*\([^)]*\)\s*\{(?P<body>.*?)\}"
            )
            func_match = re.search(function_pattern, content, re.IGNORECASE | re.DOTALL)
            if not func_match:
                continue

            body = func_match.group("body")
            # Extract ANY get_template_part() path (AC2: Remove keyword filtering)
            body_matches = re.finditer(
                r"get_template_part\s*\(\s*['\"]([^'\"]+)['\"]",
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

    # FALLBACK removed: Detection is now strict. We only scan what is referenced in functions.php.

    return partial_paths


def derive_map_imports_from_partials(partial_paths: List[dict]) -> List[dict]:
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

        scss_relative = f"css/{normalized}"
        if not scss_relative.lower().endswith(".scss"):
            scss_relative = f"{scss_relative}.scss"

        commontheme_absolute = Path(COMMON_THEME_DIR) / scss_relative

        # Try common variants
        filename = commontheme_absolute.name
        directory = commontheme_absolute.parent

        candidates = [commontheme_absolute]
        if not filename.startswith("_"):
            candidates.append(directory / f"_{filename}")

        actual_path = next((p for p in candidates if p.exists()), None)
        if not actual_path:
            logger.debug(f"Could not resolve SCSS for partial-derived path: {scss_relative}")
            continue

        imports.append(
            {
                "original_import": f"derived_from_partial:{partial_path}",
                "import_path": scss_relative,
                "commontheme_relative": scss_relative,
                "commontheme_absolute": str(actual_path),
                "filename": actual_path.name,
            }
        )

    return imports


def migrate_map_scss_content(
    slug: str, map_imports: List[dict], processor: Optional[Any] = None
) -> tuple[bool, List[str]]:
    """
    Migrate SCSS content from CommonTheme map files to sb-inside.scss and sb-home.scss.

    Args:
        slug: Dealer theme slug
        map_imports: List of map import dictionaries
        processor: Optional SCSSProcessor instance for content transformation.

    Returns:
        tuple[bool, list]: (success, list of modified files)
    """
    if not map_imports:
        return True, []

    logger.info(f"Migrating map SCSS content for {slug}")

    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        sb_inside_path = theme_dir / "sb-inside.scss"
        sb_home_path = theme_dir / "sb-home.scss"
        targets_written = []

        # 1. Pre-scan existing SCSS files for imports
        existing_imports = set()
        # candidate files to check for existing imports
        check_files = [
            sb_inside_path,
            sb_home_path,
            theme_dir / "css" / "style.scss",
            theme_dir / "css" / "inside.scss",
            theme_dir / "style.scss",
        ]

        for check_path in check_files:
            if check_path.exists():
                try:
                    content = check_path.read_text(encoding="utf-8", errors="ignore")
                    # Find @import statements
                    import_matches = re.findall(r"@import\s*['\"]([^'\"]+)['\"]", content)
                    for imp in import_matches:
                        if "CommonTheme" in imp or imp.startswith("../../"):
                            continue

                        # Extract basename without extension or underscore
                        base = Path(imp).stem
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
                path_abs = Path(map_import["commontheme_absolute"])
                scss_content = path_abs.read_text(encoding="utf-8", errors="ignore")

                # Add header comment
                map_import_path = map_import.get("commontheme_relative", map_import["filename"])

                # Transform content if processor is available
                if processor:
                    logger.debug(f"Transforming map SCSS content for {map_import['filename']}...")
                    scss_content = processor.transform_scss_content(scss_content)

                map_section = f"""
/* Migrated from CommonTheme: {map_import_path} */
{scss_content}
"""
                all_map_content.append(map_section)
                logger.debug(f"Read SCSS content from {map_import['filename']}")

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
        if sb_inside_path.exists():
            with sb_inside_path.open("a", encoding="utf-8") as f:
                f.write("\n\n/* === MAP COMPONENTS === */")
                f.write(combined_content)
            logger.info("Added map SCSS content to sb-inside.scss")
            targets_written.append("sb-inside.scss")
        else:
            logger.warning("sb-inside.scss not found")

        # Add to sb-home.scss
        if sb_home_path.exists():
            with sb_home_path.open("a", encoding="utf-8") as f:
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


def migrate_map_partials(
    slug: str,
    map_imports: List[dict],
    interactive: bool = False,
    extra_partials: Optional[List[dict]] = None,
    oem_handler: Optional[object] = None,
) -> tuple[bool, List[str]]:
    """
    Find and migrate corresponding PHP partials for map components.

    Args:
        slug: Dealer theme slug
        map_imports: List of map import dictionaries
        interactive: Whether to prompt for user confirmation (default: False)
        extra_partials: Optional list of additional partials to migrate.
        oem_handler: Optional OEM handler to use for specific patterns

    Returns:
        tuple[bool, list]: (success, list of copied partials)
    """
    if not map_imports and not extra_partials:
        return True, []

    logger.info(f"Migrating map PHP partials for {slug}")

    try:
        theme_dir = Path(get_dealer_theme_dir(slug))

        # Look for PHP partials in front-page.php and other template files
        template_files = [
            theme_dir / "front-page.php",
            theme_dir / "index.php",
            theme_dir / "page.php",
            theme_dir / "home.php",
            theme_dir / "functions.php",
        ]

        # Also check partials directory
        partials_dir = theme_dir / "partials"
        if partials_dir.exists():
            template_files.extend(list(partials_dir.rglob("*.php")))

        partial_paths = []

        # Scan template files for get_template_part calls
        for template_file in template_files:
            if template_file.exists():
                partial_paths.extend(
                    find_template_parts_in_file(str(template_file), map_imports, oem_handler)
                )

        # Guessing logic REMOVED to enforce strict detection.
        # We only migrate partials if they are explicitly found in templates or shortcodes.
        if not partial_paths:
            # Only rely on extra_partials (from shortcodes) if template scan found nothing
            pass

        # Include any extra partials discovered via shortcodes/functions
        if extra_partials:
            partial_paths.extend(extra_partials)

        # Copy partials from CommonTheme to DealerTheme
        success_count = 0
        actually_copied = []
        processed_paths = set()

        for partial_info in partial_paths:
            p_path = partial_info.get("partial_path")
            if p_path in processed_paths:
                continue
            processed_paths.add(p_path)

            status = copy_partial_to_dealer_theme(slug, partial_info, interactive=interactive)
            if status == "copied":
                success_count += 1
                actually_copied.append(p_path)
            elif status == "already_exists":
                success_count += 1
            elif status == "skipped_missing":
                # Missing but acknowledged/skipped (e.g. in interactive or is a guess)
                success_count += 1

        logger.info(f"Successfully migrated {success_count}/{len(partial_paths)} map partials")
        return (success_count > 0 or len(partial_paths) == 0), actually_copied

    except Exception as e:
        logger.error(f"Error migrating map partials: {e}")
        return False, []


def find_template_parts_in_file(
    template_file: str, map_imports: List[dict], oem_handler: Optional[object] = None
) -> List[dict]:
    """
    Find get_template_part calls and custom map functions that might correspond to map imports.

    Args:
        template_file: Path to template file
        map_imports: List of map import dictionaries
        oem_handler: Optional OEM handler to use for specific patterns

    Returns:
        list: List of partial path dictionaries
    """
    try:
        path_template = Path(template_file)
        raw_content = path_template.read_text(encoding="utf-8", errors="ignore")
        content = remove_php_comments(raw_content)

        partial_paths = []

        # Determine patterns to search for
        from sbm.oem.default import DefaultHandler

        is_oem = oem_handler and not isinstance(oem_handler, DefaultHandler)

        if is_oem and hasattr(oem_handler, "get_map_partial_patterns"):
            search_patterns = oem_handler.get_map_partial_patterns()
        else:
            keyword_list = "|".join([re.escape(k) for k in MAP_KEYWORDS])
            search_patterns = [f"[^'\"]*\\b(?:{keyword_list})[^'\"]*"]

        for pattern in search_patterns:
            template_part_pattern = r"get_template_part\s*\(\s*['\"](" + pattern + r")['\"]"
            matches = re.finditer(template_part_pattern, content, re.IGNORECASE)

            for match in matches:
                partial_path = match.group(1)

                partial_info = {
                    "template_file": template_file,
                    "partial_path": partial_path,
                    "source": "found_in_template",
                }

                logger.info(
                    f"Found map template part: {partial_path} in {Path(template_file).name}"
                )
                partial_paths.append(partial_info)

        # Custom shortcode search is already covered by find_map_shortcodes_in_functions
        # and search_patterns above. Removing redundant keyword-only search.

        # Pattern: function xyz_map() { ... get_template_part('...directions...') ... }
        # More flexible pattern to match your full_map() function
        shortcode_function_pattern = r"function\s+(\w*(?:mapsection|maprow|mapbox|getdirections)\w*)\s*\([^)]*\)\s*\{[^}]*get_template_part\s*\(\s*['\"]([^'\"]*(?:directions|getdirections|mapsection)[^'\"]*)['\"]"
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
                f"Found map shortcode function: {function_name}() calling {partial_path} in {Path(template_file).name}"
            )
            partial_paths.append(partial_info)

        # 4. Specifically look for homecontent-getdirections pattern with word boundaries
        homecontent_pattern = (
            r"get_template_part\s*\(\s*['\"]([^'\"]*\\bhomecontent[^'\"]*directions\\b[^'\"]*)['\"]"
        )
        matches = re.finditer(homecontent_pattern, content, re.IGNORECASE)

        for match in matches:
            partial_path = match.group(1)

            partial_info = {
                "template_file": template_file,
                "partial_path": partial_path,
                "source": "found_homecontent_directions",
            }

            logger.info(
                f"Found homecontent-getdirections partial: {partial_path} in {Path(template_file).name}"
            )
            partial_paths.append(partial_info)

        return partial_paths

    except Exception as e:
        logger.warning(f"Error scanning template file {template_file}: {e}")
        return []


def guess_partial_paths_from_scss(map_imports: List[dict]) -> List[dict]:
    """
    Guess partial paths based on SCSS import paths when not found in templates.

    Args:
        map_imports: List of map import dictionaries

    Returns:
        list: List of guessed partial path dictionaries
    """
    partial_paths = []
    seen_paths = set()

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

        if partial_path in seen_paths:
            continue
        seen_paths.add(partial_path)

        partial_info = {
            "partial_path": partial_path,
            "template_file": "guessed_from_scss",
            "related_scss": map_import["filename"],
            "is_guess": True,
        }

        partial_paths.append(partial_info)
        logger.debug(f"Guessed partial path: {partial_path}")

    return partial_paths


def copy_partial_to_dealer_theme(slug: str, partial_info: dict, interactive: bool = False) -> str:
    """
    Copy a PHP partial from CommonTheme to DealerTheme with proper directory structure.

    Args:
        slug: Dealer theme slug
        partial_info: Partial information dictionary
        interactive: Whether to prompt for user confirmation (default: False)

    Returns:
        str: Status of the operation: "copied", "already_exists", "not_found", or "skipped_missing"
    """
    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        partial_path = partial_info["partial_path"]

        # Use the exact path from template part call for CommonTheme
        commontheme_partial_path = partial_path.lstrip("/")

        # 1. Check if file already exists in Dealer Theme FIRST
        dealer_dest_file = theme_dir / f"{commontheme_partial_path}.php"
        dealer_dest_dir = dealer_dest_file.parent

        if dealer_dest_file.exists():
            logger.info(
                f"✅ Partial already exists in dealer theme: {dealer_dest_file.relative_to(theme_dir)}"
            )
            return "already_exists"

        # 2. Try exact match in CommonTheme first
        commontheme_source = Path(COMMON_THEME_DIR) / f"{commontheme_partial_path}.php"

        # 3. If exact match fails, try fuzzy matching (AC4)
        if not commontheme_source.exists():
            path_parts = Path(commontheme_partial_path)
            directory = Path(COMMON_THEME_DIR) / path_parts.parent
            keyword = path_parts.name

            if directory.exists():
                matches = list(directory.glob(f"*{keyword}*.php"))

                if len(matches) == 1:
                    commontheme_source = matches[0]
                    logger.info(
                        f"🔍 Fuzzy matched: {commontheme_source.name} (from pattern *{keyword}*.php)"
                    )
                elif len(matches) > 1:
                    # Prefer exact stem match
                    exact = [m for m in matches if m.stem == keyword]
                    if exact:
                        commontheme_source = exact[0]
                    else:
                        logger.warning(
                            f"Multiple matches for *{keyword}*.php: {[m.name for m in matches]}"
                        )
                        commontheme_source = matches[0]
                        logger.info(f"Using first match: {commontheme_source.name}")

        # Verify source exists after fuzzy matching attempt
        if not commontheme_source.exists():
            logger.warning(
                f"CommonTheme partial not found: {commontheme_partial_path}.php (or fuzzy matches)"
            )

            # If it's a guess, ask user for confirmation (only in interactive mode)
            if partial_info.get("is_guess"):
                if interactive:
                    click.echo(f"\ni Guessed partial not found: {commontheme_partial_path}.php")
                    click.echo(f"Related SCSS: {partial_info['related_scss']}")

                    # Try to find similar files
                    similar_files = find_similar_partials(commontheme_partial_path)
                    if similar_files:
                        click.echo("Similar files found:")
                        for similar_file in similar_files[:3]:  # Show top 3
                            click.echo(f"  - {similar_file}")

                    if click.confirm("Skip this partial?", default=True):
                        return "skipped_missing"
                    return "not_found"
                # In non-interactive mode, automatically skip missing guessed partials
                logger.warning(f"Skipping missing guessed partial: {commontheme_partial_path}.php")
                return "skipped_missing"

            return "not_found"

        # Create directory structure only if it doesn't exist
        dealer_dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy the file
        shutil.copy2(commontheme_source, dealer_dest_file)

        logger.info(f"✅ Copied partial: {commontheme_partial_path.split('/')[-1]}.php")
        logger.info(f"   From: {commontheme_source}")
        logger.info(f"   To: {dealer_dest_file}")

        return "copied"

    except Exception as e:
        logger.error(f"Error copying partial {partial_info['partial_path']}: {e}")
        return False


def find_similar_partials(partial_path: str) -> List[str]:
    """
    Find similar partial files in CommonTheme when exact match is not found.

    Args:
        partial_path: The partial path we're looking for

    Returns:
        list: List of similar partial paths
    """
    try:
        # Extract key components from the path
        path_parts = partial_path.split("/")
        search_terms = [part for part in path_parts if "map" in part.lower() or len(part) > 3]

        # Search in CommonTheme partials directory
        search_base = Path(COMMON_THEME_DIR) / "partials"
        if not search_base.exists():
            return []

        similar_files = []

        # Walk through CommonTheme partials using rglob
        for php_file in search_base.rglob("*.php"):
            relative_path = str(php_file.relative_to(search_base))

            # Check if any search terms match
            if any(term.lower() in relative_path.lower() for term in search_terms):
                similar_files.append(relative_path.replace(".php", ""))

        return similar_files[:5]  # Return top 5 matches

    except Exception as e:
        logger.warning(f"Error finding similar partials: {e}")
        return []


# Legacy functions kept for backward compatibility
def find_map_shortcodes(slug: str, shortcode_patterns: Optional[list] = None) -> list:
    """Legacy function - kept for backward compatibility."""
    logger.info("Using legacy map shortcode detection")
    return []


def identify_map_partials(slug: str, oem_handler: Optional[Union[dict, object]] = None) -> list:
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
