#!/usr/bin/env python3
"""
Test script to validate Rich UI progress tracking fixes.
This simulates the migration workflow to ensure progress bars don't hang.
"""

import time
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from sbm.ui.progress import MigrationProgress

def test_basic_progress_lifecycle():
    """Test basic progress lifecycle without errors."""
    print("🧪 Testing basic progress lifecycle...")
    
    progress = MigrationProgress()
    
    with progress.progress_context():
        # Add migration task
        migration_task = progress.add_migration_task("test_theme")
        
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
            step_task = progress.add_step_task(step_name, description, 100)
            
            # Simulate progress updates
            for i in range(0, 101, 25):
                progress.update_step_progress(step_name, 25, f"{description} ({i}%)")
                time.sleep(0.1)  # Short delay to see progress
            
            # Complete step
            progress.complete_step(step_name)
            time.sleep(0.1)
    
    print("✅ Basic progress lifecycle test passed")


def test_error_handling():
    """Test progress tracking with simulated errors."""
    print("🧪 Testing error handling...")
    
    progress = MigrationProgress()
    
    try:
        with progress.progress_context():
            # Add migration task
            migration_task = progress.add_migration_task("test_theme_error")
            
            # Add step task
            step_task = progress.add_step_task("git_ops", "Setting up Git branch", 100)
            
            # Simulate error during step
            raise ValueError("Simulated migration error")
            
    except ValueError as e:
        print(f"🎯 Caught expected error: {e}")
    
    # Verify cleanup occurred
    if not progress.tasks and not progress.step_tasks:
        print("✅ Error handling and cleanup test passed")
    else:
        print("❌ Error handling test failed - tasks not cleaned up")
        print(f"   Remaining tasks: {progress.tasks}")
        print(f"   Remaining step tasks: {progress.step_tasks}")


def test_indeterminate_tasks():
    """Test indeterminate task lifecycle."""
    print("🧪 Testing indeterminate tasks...")
    
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
    
    print("✅ Indeterminate tasks test passed")


def test_stale_task_handling():
    """Test handling of stale task references."""
    print("🧪 Testing stale task handling...")
    
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
    
    print("✅ Stale task handling test passed")


def test_concurrent_operations():
    """Test concurrent-like operations that might cause race conditions."""
    print("🧪 Testing concurrent-like operations...")
    
    progress = MigrationProgress()
    
    with progress.progress_context():
        # Add multiple tasks quickly
        tasks = []
        for i in range(5):
            task_id = progress.add_step_task(f"step_{i}", f"Step {i}", 100)
            tasks.append(f"step_{i}")
        
        # Update all tasks
        for step_name in tasks:
            progress.update_step_progress(step_name, 50)
        
        # Complete all tasks
        for step_name in tasks:
            progress.complete_step(step_name)
    
    print("✅ Concurrent-like operations test passed")


def main():
    """Run all progress tracking tests."""
    print("🚀 Starting Rich UI Progress Tracking Tests")
    print("=" * 50)
    
    try:
        test_basic_progress_lifecycle()
        test_error_handling()
        test_indeterminate_tasks()
        test_stale_task_handling()
        test_concurrent_operations()
        
        print("=" * 50)
        print("🎉 All progress tracking tests passed!")
        print("✅ Rich UI progress tracking fixes are working correctly")
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()