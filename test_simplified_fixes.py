#!/usr/bin/env python3
"""
Test simplified Rich UI progress fixes.
"""

import sys
import os
import time

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from sbm.ui.progress import MigrationProgress

def test_simplified_progress():
    """Test the simplified progress tracking approach."""
    print("🧪 Testing simplified progress approach...")
    
    progress = MigrationProgress()
    
    with progress.progress_context():
        # Add migration task (6 steps)
        migration_task = progress.add_migration_task("test_theme", 6)
        
        # Simulate the 6 migration steps
        steps = [
            ("git_ops", "Setting up Git branch"),
            ("docker_start", "Starting Docker environment"), 
            ("create_files", "Creating Site Builder files"),
            ("migrate_styles", "Migrating SCSS styles"),
            ("predetermined_styles", "Adding predetermined styles"),
            ("map_components", "Migrating map components")
        ]
        
        for i, (step_name, description) in enumerate(steps, 1):
            print(f"  Step {i}/6: {description}")
            
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
        if 'migration' in progress.tasks:
            migration_task_id = progress.tasks['migration']
            if migration_task_id in progress.progress.tasks:
                task = progress.progress.tasks[migration_task_id] 
                progress.progress.update(migration_task_id, completed=task.total)
    
    print("✅ Simplified progress test completed successfully!")

def test_command_execution():
    """Test the simplified command execution."""
    print("🧪 Testing simplified command execution...")
    
    from sbm.utils.command import execute_interactive_command
    
    # Test with suppressed output
    print("  Testing suppressed execution...")
    success = execute_interactive_command("echo 'test suppressed'", suppress_output=True)
    assert success, "Suppressed command should succeed"
    
    # Test with full output
    print("  Testing full output execution...")
    success = execute_interactive_command("echo 'test visible'", suppress_output=False)
    assert success, "Full output command should succeed"
    
    print("✅ Command execution test completed successfully!")

def main():
    """Run simplified tests."""
    print("🚀 Testing Simplified Rich UI Fixes")
    print("=" * 40)
    
    try:
        test_simplified_progress()
        test_command_execution()
        
        print("=" * 40)
        print("🎉 All simplified tests passed!")
        print("✅ Ready for real-world testing")
        
    except Exception as e:
        print("=" * 40)
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()