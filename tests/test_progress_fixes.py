"""
Test cases for progress tracking fixes to verify the critical bug fixes work correctly.

This test module covers:
- Progress completion logic (0% → 100% display)
- Thread cleanup and race condition handling  
- Subprocess tracking without hanging processes
"""

import threading
import time
from unittest.mock import Mock, patch
import pytest
from rich.progress import Progress

from sbm.ui.progress import MigrationProgress


class TestProgressCompletionLogic:
    """Test the fixed progress completion logic."""
    
    def test_progress_completion_normal_case(self):
        """Test 0% → 100% progress display works correctly for normal completion."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                # Add a step task
                step_name = "test_step"
                progress_tracker.add_step_task(step_name, "Test Step", total=100)
                
                # Simulate some progress
                progress_tracker.update_step_progress(step_name, advance=50)
                
                # Complete the step
                progress_tracker.complete_step(step_name)
                
                # Verify task shows 100% completion
                task_id = progress_tracker.step_tasks[step_name]
                task = progress_tracker.progress.tasks[task_id]
                
                # Critical test: Task should be at 100% completion
                assert task.completed == task.total
                assert task.percentage == 100.0
                
    def test_progress_completion_already_completed(self):
        """Test progress completion when task is already at 100%."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                step_name = "test_step"
                progress_tracker.add_step_task(step_name, "Test Step", total=100)
                
                # Complete the task fully first
                progress_tracker.update_step_progress(step_name, advance=100)
                
                # Now call complete_step (should handle gracefully)
                progress_tracker.complete_step(step_name)
                
                # Should still be at 100%
                task_id = progress_tracker.step_tasks[step_name]
                task = progress_tracker.progress.tasks[task_id]
                assert task.completed == task.total
                
    def test_progress_completion_over_completed(self):
        """Test progress completion when task has been over-completed."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                step_name = "test_step" 
                progress_tracker.add_step_task(step_name, "Test Step", total=100)
                
                # Simulate over-completion (this was causing the bug)
                progress_tracker.update_step_progress(step_name, advance=150)
                
                # Complete the step (should handle negative remaining)
                progress_tracker.complete_step(step_name)
                
                # Task should still be valid
                task_id = progress_tracker.step_tasks[step_name]
                task = progress_tracker.progress.tasks[task_id]
                assert task.completed >= task.total
                
    def test_progress_completion_nonexistent_step(self):
        """Test progress completion for non-existent step."""
        with patch('sbm.ui.progress.logger') as mock_logger:
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                # Try to complete a step that doesn't exist
                progress_tracker.complete_step("nonexistent_step")
                
                # Should log a warning
                mock_logger.warning.assert_called_once()


class TestThreadCleanupRaceConditions:
    """Test the fixed thread cleanup logic."""
    
    def test_subprocess_thread_cleanup_handles_race_conditions(self):
        """Test subprocess thread cleanup handles race conditions properly."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            # Add mock subprocess threads
            mock_threads = []
            for i in range(5):
                mock_thread = Mock()
                mock_thread.is_alive.return_value = True
                mock_thread.name = f"test_thread_{i}"
                mock_threads.append(mock_thread)
                progress_tracker._subprocess_threads.append(mock_thread)
            
            # Test cleanup doesn't hang or fail
            cleanup_success = progress_tracker._cleanup_subprocess_threads()
            
            # Should complete without hanging
            assert isinstance(cleanup_success, bool)
            
            # All threads should have been joined
            for mock_thread in mock_threads:
                mock_thread.join.assert_called_once()
    
    def test_wait_for_subprocess_completion_race_condition_safe(self):
        """Test wait_for_subprocess_completion handles list modification during iteration."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            # Add threads to the list
            mock_threads = []
            for i in range(3):
                mock_thread = Mock()
                mock_thread.is_alive.return_value = False  # Already completed
                mock_thread.name = f"completed_thread_{i}"
                mock_threads.append(mock_thread)
                progress_tracker._subprocess_threads.append(mock_thread)
            
            # This should complete without race conditions
            result = progress_tracker.wait_for_subprocess_completion(timeout=5.0)
            
            # Should return True for successful completion
            assert result is True
            
    def test_subprocess_cleanup_timeout_handling(self):
        """Test subprocess cleanup handles threads that don't respond to join."""
        with patch('sbm.ui.progress.logger') as mock_logger:
            progress_tracker = MigrationProgress()
            
            # Add a stubborn thread that won't stop
            stubborn_thread = Mock()
            stubborn_thread.is_alive.return_value = True  # Refuses to stop
            stubborn_thread.name = "stubborn_thread"
            progress_tracker._subprocess_threads.append(stubborn_thread)
            
            # Should handle timeout gracefully
            cleanup_success = progress_tracker._cleanup_subprocess_threads()
            
            # Should log a warning about the stubborn thread
            mock_logger.warning.assert_called()
            
            # Should forcibly clear remaining threads
            assert len(progress_tracker._subprocess_threads) == 0


class TestThreadSafetyImprovements:
    """Test thread safety improvements."""
    
    def test_complete_step_thread_safety(self):
        """Test that complete_step uses proper locking."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                step_name = "test_step"
                progress_tracker.add_step_task(step_name, "Test Step", total=100)
                
                # Test that the lock is acquired during complete_step
                with patch.object(progress_tracker._lock, '__enter__') as mock_enter:
                    with patch.object(progress_tracker._lock, '__exit__') as mock_exit:
                        progress_tracker.complete_step(step_name)
                        
                        # Lock should have been acquired
                        mock_enter.assert_called_once()
                        mock_exit.assert_called_once()
    
    def test_concurrent_step_completion(self):
        """Test concurrent step completion doesn't cause race conditions."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                # Add multiple steps
                step_names = ["step1", "step2", "step3"]
                for step_name in step_names:
                    progress_tracker.add_step_task(step_name, f"Test {step_name}", total=100)
                
                # Complete steps concurrently
                threads = []
                for step_name in step_names:
                    thread = threading.Thread(
                        target=progress_tracker.complete_step, 
                        args=(step_name,)
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join(timeout=5.0)
                    assert not thread.is_alive()  # No hanging threads
                
                # All steps should be completed
                for step_name in step_names:
                    task_id = progress_tracker.step_tasks[step_name]
                    task = progress_tracker.progress.tasks[task_id]
                    assert task.completed >= task.total


class TestProgressTrackerIntegration:
    """Integration tests for the overall progress tracking system."""
    
    def test_full_migration_progress_workflow(self):
        """Test a complete migration workflow with progress tracking."""
        with patch('sbm.ui.progress.logger'):
            progress_tracker = MigrationProgress()
            
            with progress_tracker.progress_context():
                # Simulate full migration workflow
                migration_steps = [
                    "git_setup",
                    "docker_start", 
                    "file_creation",
                    "scss_migration",
                    "style_addition",
                    "component_migration"
                ]
                
                # Add migration task
                progress_tracker.add_migration_task("test_theme", len(migration_steps))
                
                # Add and complete each step
                for i, step in enumerate(migration_steps):
                    progress_tracker.add_step_task(step, f"Step {i+1}: {step.title()}", 100)
                    
                    # Simulate work with incremental progress
                    progress_tracker.update_step_progress(step, advance=50)
                    progress_tracker.update_step_progress(step, advance=25)
                    
                    # Complete the step
                    progress_tracker.complete_step(step)
                    
                    # Verify step is completed
                    task_id = progress_tracker.step_tasks[step]
                    task = progress_tracker.progress.tasks[task_id]
                    assert task.completed >= task.total
                
                # All steps should be in completed state
                assert len(progress_tracker.step_tasks) == len(migration_steps)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])