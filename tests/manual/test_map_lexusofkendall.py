import logging
from pathlib import Path

from sbm.core.maps import migrate_map_components
from sbm.core.migration import create_sb_files, migrate_styles
from sbm.oem.factory import OEMFactory

logging.basicConfig(level=logging.DEBUG)

slug = "lexusofkendall"
oem_handler = OEMFactory.detect_from_theme(slug)

print("Running create_sb_files...")
create_sb_files(slug, force_reset=True)

print("Running migrate_styles...")
from sbm.scss.processor import SCSSProcessor

processor = SCSSProcessor(slug, exclude_nav_styles=True)
migrate_styles(slug, processor)

# Run map migration
print(f"Running map migration for {slug}...")
success = migrate_map_components(slug, oem_handler, interactive=False, processor=processor)
print(f"Success: {success}")

# Check what got written to sb-inside.scss
sb_inside = Path(f"/Users/nathanhart/di-websites-platform/dealer-themes/{slug}/sb-inside.scss")
if sb_inside.exists():
    content = sb_inside.read_text(encoding="utf-8")
    if "section-directions" in content or "map" in content.lower():
        print("MAP SCSS FOUND IN SB-INSIDE.SCSS!")
    else:
        print("MAP SCSS **NOT** FOUND IN SB-INSIDE.SCSS!")
