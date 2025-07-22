#!/usr/bin/env python3
"""
Test the ACTUAL workflow that's hanging at map migration.
This simulates the exact same calls that happen in the real migration.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath("."))

from sbm.core.maps import migrate_map_components
from sbm.oem.factory import OEMFactory
from sbm.ui.progress import MigrationProgress


def test_actual_map_migration():
    """Test the actual map migration that's hanging."""

    # Create progress tracker exactly like the real CLI
    progress = MigrationProgress()

    with progress.progress_context():
        # Add migration task
        progress.add_migration_task("magmaserati", 6)

        # Skip to step 6 (where it hangs)
        for i in range(5):
            step_name = f"step_{i+1}"
            progress.add_step_task(step_name, f"Step {i+1}", 100)
            progress.update_step_progress(step_name, 100)
            progress.complete_step(step_name)

        # Now test the problematic step 6

        # This is the EXACT code from migration.py that hangs
        if progress:
            progress.add_step_task("map_components", "Migrating map components", 100)
            progress.update_step_progress("map_components", 0, "Scanning for map components")


        # Create OEM handler exactly like the real code
        oem_handler = OEMFactory.detect_from_theme("magmaserati")

        # This is where it hangs - let's see why
        try:
            # Call with exact same parameters as real migration
            migrate_map_components("magmaserati", oem_handler, interactive=False)

            # Complete step like real migration
            if progress:
                progress.update_step_progress("map_components", 100, "Map components migrated")
                progress.complete_step("map_components")


        except Exception:
            import traceback
            traceback.print_exc()
            raise

def test_map_function_directly():
    """Test just the map function without progress to isolate the issue."""

    try:
        # Test the function that's actually hanging
        oem_handler = OEMFactory.detect_from_theme("magmaserati")

        migrate_map_components("magmaserati", oem_handler, interactive=False)


    except Exception:
        import traceback
        traceback.print_exc()
        raise

def main():
    """Test the actual hanging workflow."""

    try:
        # First test the function directly
        test_map_function_directly()

        # Then test with progress (where it hangs)
        test_actual_map_migration()


    except Exception:
        import traceback
        traceback.print_exc()

        sys.exit(1)

if __name__ == "__main__":
    main()
