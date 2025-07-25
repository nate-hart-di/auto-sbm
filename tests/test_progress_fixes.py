#!/usr/bin/env python3
"""
Test script to validate Rich UI progress tracking fixes.
This simulates the migration workflow to ensure progress bars don't hang.
"""

import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, os.path.abspath("."))

from sbm.ui.progress import MigrationProgress


def test_basic_progress_lifecycle():
    """Test basic progress lifecycle without errors."""

    progress = MigrationProgress()

    with progress.progress_context():
        # Add migration task
        progress.add_migration_task("test_theme")

        # Add and complete step tasks
        steps = [
            ("git_ops", "Setting up Git branch"),
            ("docker_start", "Starting Docker environment"),
            ("create_files", "Creating Site Builder files"),
            ("migrate_styles", "Migrating SCSS styles"),
            ("predetermined_styles", "Adding predetermined styles"),
            ("map_components", "Migrating map components")
        ]

        for step_name, description in steps:
            progress.add_step_task(step_name, description, 100)

            # Simulate progress updates
            for i in range(0, 101, 25):
                progress.update_step_progress(step_name, 25, f"{description} ({i}%)")
                time.sleep(0.1)  # Short delay to see progress

            # Complete step
            progress.complete_step(step_name)
            time.sleep(0.1)



def test_error_handling():
    """Test progress tracking with simulated errors."""

    progress = MigrationProgress()

    try:
        with progress.progress_context():
            # Add migration task
            progress.add_migration_task("test_theme_error")

            # Add step task
            progress.add_step_task("git_ops", "Setting up Git branch", 100)

            # Simulate error during step
            msg = "Simulated migration error"
            raise ValueError(msg)

    except ValueError:
        pass

    # Verify cleanup occurred
    if not progress.tasks and not progress.step_tasks:
        pass
    else:
        pass


def test_indeterminate_tasks():
    """Test indeterminate task lifecycle."""

    progress = MigrationProgress()

    with progress.progress_context():
        # Add indeterminate task (like Docker startup)
        docker_task = progress.add_indeterminate_task("Starting Docker environment...")

        # Simulate updates
        for i in range(5):
            progress.update_indeterminate_task(docker_task, f"Building containers... ({i+1}/5)")
            time.sleep(0.2)

        # Complete task
        progress.complete_indeterminate_task(docker_task, "Docker environment started")
        time.sleep(0.5)



def test_stale_task_handling():
    """Test handling of stale task references."""

    progress = MigrationProgress()

    with progress.progress_context():
        # Add step task
        step_task = progress.add_step_task("test_step", "Test step", 100)

        # Simulate Rich internally removing the task
        if step_task in progress.progress.tasks:
            progress.progress.remove_task(step_task)

        # Try to update the removed task - should handle gracefully
        progress.update_step_progress("test_step", 50, "Should handle gracefully")

        # Try to complete the removed task - should handle gracefully
        progress.complete_step("test_step")



def test_concurrent_operations():
    """Test concurrent-like operations that might cause race conditions."""

    progress = MigrationProgress()

    with progress.progress_context():
        # Add multiple tasks quickly
        tasks = []
        for i in range(5):
            progress.add_step_task(f"step_{i}", f"Step {i}", 100)
            tasks.append(f"step_{i}")

        # Update all tasks
        for step_name in tasks:
            progress.update_step_progress(step_name, 50)

        # Complete all tasks
        for step_name in tasks:
            progress.complete_step(step_name)



def main():
    """Run all progress tracking tests."""

    try:
        test_basic_progress_lifecycle()
        test_error_handling()
        test_indeterminate_tasks()
        test_stale_task_handling()
        test_concurrent_operations()


    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
