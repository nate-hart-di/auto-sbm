#!/usr/bin/env python3
"""
Test the EXACT CLI workflow that hangs.
This reproduces the exact same call sequence as sbm auto.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath("."))

def test_exact_cli_workflow():
    """Test the exact same workflow as 'sbm auto magmaserati'."""

    # Import exactly like the CLI does
    from sbm.core.migration import migrate_dealer_theme
    from sbm.ui.console import get_console
    from sbm.ui.progress import MigrationProgress

    get_console()

    # Simulate exact CLI parameters
    theme_name = "magmaserati"
    skip_just = True  # Skip Docker to isolate the map issue
    force_reset = False
    create_pr = True
    interactive_review = False
    interactive_git = False
    interactive_pr = False
    verbose_docker = False

    # Create progress tracker exactly like CLI
    progress = MigrationProgress()


    try:
        with progress.progress_context():
            # Add overall migration task exactly like CLI
            progress.add_migration_task(theme_name)

            try:

                # Call with exact same parameters as CLI
                success = migrate_dealer_theme(
                    theme_name,
                    skip_just=skip_just,  # Skip Docker to focus on map issue
                    force_reset=force_reset,
                    create_pr=create_pr,
                    interactive_review=interactive_review,
                    interactive_git=interactive_git,
                    interactive_pr=interactive_pr,
                    progress_tracker=progress,
                    verbose_docker=verbose_docker
                )


                if success:
                    # Complete migration task exactly like CLI
                    if "migration" in progress.tasks:
                        migration_task_id = progress.tasks["migration"]
                        if migration_task_id in progress.progress.tasks:
                            task = progress.progress.tasks[migration_task_id]
                            progress.progress.update(migration_task_id, completed=task.total)

                else:
                    pass

            except Exception:
                import traceback
                traceback.print_exc()
                raise

    except Exception:
        import traceback
        traceback.print_exc()
        raise

def main():
    """Test exact CLI reproduction."""

    try:
        test_exact_cli_workflow()


    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
