#!/usr/bin/env python3
"""
Test the EXACT CLI workflow that hangs.
This reproduces the exact same call sequence as sbm auto.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_exact_cli_workflow():
    """Test the exact same workflow as 'sbm auto magmaserati'."""
    print("🧪 Testing EXACT CLI workflow...")
    
    # Import exactly like the CLI does
    from sbm.ui.progress import MigrationProgress
    from sbm.core.migration import migrate_dealer_theme
    from sbm.ui.console import get_console
    from sbm.ui.panels import StatusPanels
    
    console = get_console()
    
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
    
    print("Starting migration with progress context...")
    
    try:
        with progress.progress_context():
            # Add overall migration task exactly like CLI
            migration_task = progress.add_migration_task(theme_name)
            print(f"Created migration task: {migration_task}")
            
            try:
                print("Calling migrate_dealer_theme...")
                
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
                
                print(f"migrate_dealer_theme returned: {success}")
                
                if success:
                    # Complete migration task exactly like CLI
                    if 'migration' in progress.tasks:
                        migration_task_id = progress.tasks['migration']
                        if migration_task_id in progress.progress.tasks:
                            task = progress.progress.tasks[migration_task_id]
                            progress.progress.update(migration_task_id, completed=task.total)
                            print("Completed overall migration task")
                    
                    print("✅ CLI workflow completed successfully!")
                else:
                    print("❌ Migration failed")
                    
            except Exception as migration_error:
                print(f"❌ Migration error: {migration_error}")
                import traceback
                traceback.print_exc()
                raise
                
    except Exception as context_error:
        print(f"❌ Progress context error: {context_error}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Test exact CLI reproduction."""
    print("🚀 Testing EXACT CLI Reproduction")
    print("This should hang at map migration just like the real CLI")
    print("=" * 60)
    
    try:
        test_exact_cli_workflow()
        
        print("=" * 60)
        print("🎉 No hanging detected - workflow completed!")
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ HANG/ERROR DETECTED: {e}")
        print("This is the exact issue causing the CLI to hang!")
        sys.exit(1)

if __name__ == "__main__":
    main()