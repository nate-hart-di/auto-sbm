"""
Enhanced map components migration for the SBM tool.

This module handles the migration of map components from CommonTheme to DealerTheme
by scanning for CommonTheme @import statements and copying both SCSS and PHP partials.
"""

import os
import re
import shutil
from glob import glob
from typing import Optional

import click

from sbm.utils.logger import logger
from sbm.utils.path import get_dealer_theme_dir

# CommonTheme directory path
COMMON_THEME_DIR = "/Users/nathanhart/di-websites-platform/app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme"


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
    logger.info(f"Starting enhanced map components migration for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)
        style_scss_path = os.path.join(theme_dir, "css", "style.scss")

        if not os.path.exists(style_scss_path):
            logger.warning(f"style.scss not found at {style_scss_path}")
            return True  # Not an error, just no style.scss to process

        # Step 1: Find CommonTheme map imports in style.scss
        map_imports = find_commontheme_map_imports(style_scss_path)

        if not map_imports:
            logger.info("No CommonTheme map imports found in style.scss")
            return True

        # Step 2: Migrate SCSS content to sb-inside.scss and sb-home.scss
        scss_success = migrate_map_scss_content(slug, map_imports)

        # Step 3: Find and migrate corresponding PHP partials
        partials_success = migrate_map_partials(slug, map_imports, interactive=interactive)

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

        # Look for @import statements with CommonTheme paths containing "map"
        # Pattern: @import '../../DealerInspireCommonTheme/css/...map...';
        import_pattern = r"@import\s+['\"]([^'\"]*DealerInspireCommonTheme[^'\"]*map[^'\"]*)['\"]"
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

            # Verify the file exists in CommonTheme (try with and without underscore prefix)
            actual_file_path = None
            if os.path.exists(commontheme_absolute):
                actual_file_path = commontheme_absolute
            else:
                # Try with underscore prefix if not found
                filename = os.path.basename(commontheme_absolute)
                directory = os.path.dirname(commontheme_absolute)
                underscore_filename = f"_{filename}" if not filename.startswith("_") else filename
                underscore_path = os.path.join(directory, underscore_filename)

                if os.path.exists(underscore_path):
                    actual_file_path = underscore_path
                    commontheme_absolute = underscore_path  # Update the path

            if actual_file_path:
                map_import["commontheme_absolute"] = actual_file_path  # Update with actual path
                map_imports.append(map_import)
                logger.info(f"Found map import: {map_import['filename']} at {actual_file_path}")
            else:
                logger.warning(f"CommonTheme file not found: {commontheme_absolute}")

        if map_imports:
            logger.info(f"Found {len(map_imports)} CommonTheme map imports")
        else:
            logger.info("No CommonTheme map imports found")

        return map_imports

    except Exception as e:
        logger.error(f"Error scanning style.scss for map imports: {e}")
        return []


def migrate_map_scss_content(slug, map_imports) -> Optional[bool]:
    """
    Migrate SCSS content from CommonTheme map files to sb-inside.scss and sb-home.scss.

    Args:
        slug (str): Dealer theme slug
        map_imports (list): List of map import dictionaries

    Returns:
        bool: True if successful, False otherwise
    """
    if not map_imports:
        return True

    logger.info(f"Migrating map SCSS content for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)
        sb_inside_path = os.path.join(theme_dir, "sb-inside.scss")
        sb_home_path = os.path.join(theme_dir, "sb-home.scss")

        # Collect all map SCSS content
        all_map_content = []

        for map_import in map_imports:
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
            return True

        # Combine all map content
        combined_content = "\n".join(all_map_content)

        # Add to sb-inside.scss
        if os.path.exists(sb_inside_path):
            with open(sb_inside_path, "a", encoding="utf-8") as f:
                f.write("\n\n/* === MAP COMPONENTS === */")
                f.write(combined_content)
            logger.info("Added map SCSS content to sb-inside.scss")
        else:
            logger.warning("sb-inside.scss not found")

        # Add to sb-home.scss
        if os.path.exists(sb_home_path):
            with open(sb_home_path, "a", encoding="utf-8") as f:
                f.write("\n\n/* === MAP COMPONENTS === */")
                f.write(combined_content)
            logger.info("Added map SCSS content to sb-home.scss")
        else:
            logger.warning("sb-home.scss not found")

        return True

    except Exception as e:
        logger.error(f"Error migrating map SCSS content: {e}")
        return False


def migrate_map_partials(slug, map_imports, interactive=False):
    """
    Find and migrate corresponding PHP partials for map components.

    Args:
        slug (str): Dealer theme slug
        map_imports (list): List of map import dictionaries
        interactive (bool): Whether to prompt for user confirmation (default: False)

    Returns:
        bool: True if successful, False otherwise
    """
    if not map_imports:
        return True

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

        # Copy partials from CommonTheme to DealerTheme
        success_count = 0
        for partial_info in partial_paths:
            if copy_partial_to_dealer_theme(slug, partial_info, interactive=interactive):
                success_count += 1

        logger.info(f"Successfully migrated {success_count}/{len(partial_paths)} map partials")
        return success_count > 0 or len(partial_paths) == 0

    except Exception as e:
        logger.error(f"Error migrating map partials: {e}")
        return False


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

        # 1. Look for get_template_part calls that contain "map"
        template_part_pattern = r"get_template_part\s*\(\s*['\"]([^'\"]*map[^'\"]*)['\"]"
        matches = re.finditer(template_part_pattern, content)

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
        directions_pattern = r"get_template_part\s*\(\s*['\"]([^'\"]*(?:directions|getdirections)[^'\"]*)['\"]"
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

        # CommonTheme source file (always .php extension)
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

        # Use the exact same relative path from front-page.php in dealer theme
        dealer_dest_file = os.path.join(theme_dir, f"{commontheme_partial_path}.php")
        dealer_dest_dir = os.path.dirname(dealer_dest_file)

        # Create directory structure only if it doesn't exist
        os.makedirs(dealer_dest_dir, exist_ok=True)

        # Check if file already exists
        if os.path.exists(dealer_dest_file):
            logger.info(
                f"✅ Partial already exists: {os.path.relpath(dealer_dest_file, theme_dir)}"
            )
            logger.info("   Using existing file instead of overwriting")
            return True

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
