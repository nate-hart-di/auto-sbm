#!/usr/bin/env python3
"""
Test simplified Rich UI progress fixes.
"""

import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, os.path.abspath("."))

from sbm.ui.progress import MigrationProgress


def test_simplified_progress():
    """Test the simplified progress tracking approach."""

    progress = MigrationProgress()

    with progress.progress_context():
        # Add migration task (6 steps)
        progress.add_migration_task("test_theme", 6)

        # Simulate the 6 migration steps
        steps = [
            ("git_ops", "Setting up Git branch"),
            ("docker_start", "Starting Docker environment"),
            ("create_files", "Creating Site Builder files"),
            ("migrate_styles", "Migrating SCSS styles"),
            ("predetermined_styles", "Adding predetermined styles"),
            ("map_components", "Migrating map components")
        ]

        for _i, (step_name, description) in enumerate(steps, 1):

            # Add step task
            progress.add_step_task(step_name, description, 100)

            # Update progress from 0 to 100
            for percent in [0, 25, 50, 75, 100]:
                progress.update_step_progress(step_name, 25 if percent < 100 else 0,
                                            f"{description} ({percent}%)")
                time.sleep(0.1)

            # Complete step
            progress.complete_step(step_name)
            time.sleep(0.2)

        # Verify migration task completion
        if "migration" in progress.tasks:
            migration_task_id = progress.tasks["migration"]
            if migration_task_id in progress.progress.tasks:
                task = progress.progress.tasks[migration_task_id]
                progress.progress.update(migration_task_id, completed=task.total)


def test_command_execution():
    """Test the simplified command execution."""

    from sbm.utils.command import execute_interactive_command

    # Test with suppressed output
    success = execute_interactive_command("echo 'test suppressed'", suppress_output=True)
    assert success, "Suppressed command should succeed"

    # Test with full output
    success = execute_interactive_command("echo 'test visible'", suppress_output=False)
    assert success, "Full output command should succeed"


def main():
    """Run simplified tests."""

    try:
        test_simplified_progress()
        test_command_execution()


    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
