#!/usr/bin/env python3
"""
Minimal test to isolate the Rich UI hanging issue.
"""

import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, os.path.abspath("."))

from sbm.ui.progress import MigrationProgress


def test_minimal_rich_hang():
    """Test minimal Rich context that reproduces the hang."""
    print("🧪 Testing minimal Rich context...")

    progress = MigrationProgress()

    print("Entering progress context...")

    with progress.progress_context():
        print("Inside progress context")

        # Add tasks exactly like the real migration
        migration_task = progress.add_migration_task("test", 6)
        print(f"Added migration task: {migration_task}")

        # Add step tasks that get auto-removed by Rich
        for i in range(6):
            step_name = f"step_{i}"
            task_id = progress.add_step_task(step_name, f"Step {i}", 100)
            print(f"Added step task {step_name}: {task_id}")

            # Update progress
            progress.update_step_progress(step_name, 50)

            # Rich might remove tasks internally here
            time.sleep(0.1)

        print("All tasks added, attempting to exit context...")

    print("✅ Exited progress context successfully!")

def test_rich_cleanup_only():
    """Test just the Rich cleanup logic."""
    print("🧪 Testing Rich cleanup logic...")

    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        expand=True
    )

    print("Creating Rich progress with tasks...")

    with progress:
        # Add tasks
        task_ids = []
        for i in range(5):
            task_id = progress.add_task(f"Task {i}", total=100)
            task_ids.append(task_id)
            progress.update(task_id, advance=20)
            time.sleep(0.1)

        print("Tasks created, exiting...")

    print("✅ Rich cleanup completed!")

def main():
    """Test Rich UI hanging."""
    print("🚀 Testing Rich UI Hanging Issue")
    print("=" * 40)

    try:
        # Test basic Rich first
        test_rich_cleanup_only()
        print()

        # Test our wrapper that hangs
        test_minimal_rich_hang()

        print("=" * 40)
        print("🎉 No hanging detected!")

    except Exception as e:
        print("=" * 40)
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
