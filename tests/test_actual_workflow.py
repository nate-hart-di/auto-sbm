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
    print("🧪 Testing ACTUAL map migration workflow...")

    # Create progress tracker exactly like the real CLI
    progress = MigrationProgress()

    with progress.progress_context():
        # Add migration task
        migration_task = progress.add_migration_task("magmaserati", 6)

        # Skip to step 6 (where it hangs)
        print("Simulating steps 1-5...")
        for i in range(5):
            step_name = f"step_{i+1}"
            progress.add_step_task(step_name, f"Step {i+1}", 100)
            progress.update_step_progress(step_name, 100)
            progress.complete_step(step_name)

        # Now test the problematic step 6
        print("🎯 Testing step 6 (map migration) - where it hangs...")

        # This is the EXACT code from migration.py that hangs
        if progress:
            progress.add_step_task("map_components", "Migrating map components", 100)
            progress.update_step_progress("map_components", 0, "Scanning for map components")

        print("Calling migrate_map_components...")

        # Create OEM handler exactly like the real code
        oem_handler = OEMFactory.detect_from_theme("magmaserati")
        print(f"Using OEM handler: {oem_handler}")

        # This is where it hangs - let's see why
        try:
            # Call with exact same parameters as real migration
            result = migrate_map_components("magmaserati", oem_handler, interactive=False)
            print(f"migrate_map_components returned: {result}")

            # Complete step like real migration
            if progress:
                progress.update_step_progress("map_components", 100, "Map components migrated")
                progress.complete_step("map_components")

            print("✅ Map migration completed successfully!")

        except Exception as e:
            print(f"❌ Map migration failed with error: {e}")
            import traceback
            traceback.print_exc()
            raise

def test_map_function_directly():
    """Test just the map function without progress to isolate the issue."""
    print("🧪 Testing map function directly (no progress)...")

    try:
        # Test the function that's actually hanging
        oem_handler = OEMFactory.detect_from_theme("magmaserati")
        print(f"OEM handler: {oem_handler}")

        print("Calling migrate_map_components directly...")
        result = migrate_map_components("magmaserati", oem_handler, interactive=False)
        print(f"Direct call result: {result}")

        print("✅ Direct map function call completed!")

    except Exception as e:
        print(f"❌ Direct map function failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Test the actual hanging workflow."""
    print("🚀 Testing ACTUAL Hanging Workflow")
    print("=" * 50)

    try:
        # First test the function directly
        test_map_function_directly()
        print()

        # Then test with progress (where it hangs)
        test_actual_map_migration()

        print("=" * 50)
        print("🎉 All tests completed - no hanging!")

    except Exception as e:
        print("=" * 50)
        print(f"❌ Test revealed the hanging issue: {e}")
        import traceback
        traceback.print_exc()

        print("\n🔍 This is why it hangs in the real migration!")
        sys.exit(1)

if __name__ == "__main__":
    main()
