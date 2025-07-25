"""
Tests for SBM Rich progress tracking components.

This module tests the progress tracking functionality including migration
progress, step tracking, and file processing progress.
"""

import time
from io import StringIO

from rich.console import Console

from sbm.ui.progress import MigrationProgress


class TestMigrationProgress:
    """Test suite for MigrationProgress class."""

    def test_progress_initialization(self):
        """Test progress tracker initializes correctly."""
        progress = MigrationProgress()
        assert progress.progress is not None
        assert progress.tasks == {}
        assert progress.step_tasks == {}
        assert progress._start_time is None

    def test_progress_initialization_with_speed(self):
        """Test progress tracker initializes with speed tracking."""
        progress = MigrationProgress(show_speed=True)
        assert progress.progress is not None
        # Should have additional columns when show_speed is True

    def test_migration_task_creation(self):
        """Test migration task creation."""
        progress = MigrationProgress()
        with progress.progress_context():
            task_id = progress.add_migration_task("test-theme")
            assert task_id is not None
            assert progress.tasks["migration"] == task_id
            assert task_id in progress.progress.tasks

            # Test with custom step count
            task_id2 = progress.add_migration_task("test-theme2", 8)
            assert task_id2 != task_id

    def test_step_task_creation(self):
        """Test step task creation."""
        progress = MigrationProgress()
        with progress.progress_context():
            task_id = progress.add_step_task("test_step", "Test step description", 100)
            assert task_id is not None
            assert progress.step_tasks["test_step"] == task_id
            assert task_id in progress.progress.tasks

    def test_step_progress_updates(self):
        """Test step progress updates work correctly."""
        progress = MigrationProgress()
        with progress.progress_context():
            progress.add_migration_task("test-theme")
            step_task = progress.add_step_task("test_step", "Test step", 100)

            # Update step progress
            progress.update_step_progress("test_step", 25)

            # Check progress state
            task = progress.progress.tasks[step_task]
            assert task.completed == 25

    def test_step_progress_with_description(self):
        """Test step progress updates with description changes."""
        progress = MigrationProgress()
        with progress.progress_context():
            step_task = progress.add_step_task("test_step", "Initial description", 100)

            # Update with new description
            progress.update_step_progress("test_step", 50, "Updated description")

            task = progress.progress.tasks[step_task]
            assert task.completed == 50

    def test_step_completion(self):
        """Test step completion advances migration progress."""
        progress = MigrationProgress()
        with progress.progress_context():
            migration_task = progress.add_migration_task("test-theme", 3)
            step_task = progress.add_step_task("test_step", "Test step", 100)

            # Complete the step
            progress.complete_step("test_step")

            # Step should be removed
            assert "test_step" not in progress.step_tasks
            assert step_task not in progress.progress.tasks

            # Migration should advance
            migration_progress = progress.progress.tasks[migration_task]
            assert migration_progress.completed == 1

    def test_multiple_step_completion(self):
        """Test multiple step completions advance migration correctly."""
        progress = MigrationProgress()
        with progress.progress_context():
            migration_task = progress.add_migration_task("test-theme", 3)

            # Add and complete 3 steps
            for i in range(3):
                step_name = f"step_{i}"
                progress.add_step_task(step_name, f"Step {i}", 100)
                progress.complete_step(step_name)

            # Migration should be complete
            migration_progress = progress.progress.tasks[migration_task]
            assert migration_progress.completed == 3

    def test_context_manager(self):
        """Test progress context manager works correctly."""
        progress = MigrationProgress()

        with progress.progress_context() as p:
            assert p is progress
            assert progress._start_time is not None
            task_id = p.add_migration_task("test-theme")
            assert task_id is not None

        # Context should exit cleanly
        assert True

    def test_file_processing_task(self):
        """Test file processing task functionality."""
        progress = MigrationProgress()
        with progress.progress_context():
            task_id = progress.add_file_processing_task(4)
            assert task_id is not None
            assert progress.tasks["file_processing"] == task_id

            # Update file progress
            progress.update_file_progress("test.scss", 1)

            task = progress.progress.tasks[task_id]
            assert task.completed == 1

            # Complete file processing
            progress.complete_file_processing()

            task = progress.progress.tasks[task_id]
            assert task.completed == 4

    def test_indeterminate_task(self):
        """Test indeterminate task (spinner only) functionality."""
        progress = MigrationProgress()
        with progress.progress_context():
            task_id = progress.add_indeterminate_task("Loading...")
            assert task_id is not None
            assert task_id in progress.progress.tasks

            # Update description
            progress.update_indeterminate_task(task_id, "Still loading...")

            # Complete indeterminate task
            progress.complete_indeterminate_task(task_id, "Loading complete")

            # Small delay to allow removal
            time.sleep(0.6)

            # Task should be removed
            assert task_id not in progress.progress.tasks

    def test_elapsed_time_tracking(self):
        """Test elapsed time tracking functionality."""
        progress = MigrationProgress()

        with progress.progress_context():
            # Time should start tracking
            assert progress._start_time is not None

            # Sleep briefly
            time.sleep(0.1)

            elapsed = progress.get_elapsed_time()
            assert elapsed > 0
            assert elapsed < 1  # Should be less than 1 second

    def test_task_progress_percentage(self):
        """Test task progress percentage calculation."""
        progress = MigrationProgress()
        with progress.progress_context():
            task_id = progress.add_step_task("test_step", "Test", 100)

            # Initially 0%
            percentage = progress.get_task_progress(task_id)
            assert percentage == 0.0

            # Update to 50%
            progress.update_step_progress("test_step", 50)
            percentage = progress.get_task_progress(task_id)
            assert percentage == 50.0

            # Update to 100%
            progress.update_step_progress("test_step", 50)
            percentage = progress.get_task_progress(task_id)
            assert percentage == 100.0

    def test_nonexistent_step_handling(self):
        """Test handling of operations on nonexistent steps."""
        progress = MigrationProgress()
        with progress.progress_context():
            # These should not raise errors
            progress.update_step_progress("nonexistent_step", 50)
            progress.complete_step("nonexistent_step")

            # No exceptions should be raised
            assert True


class TestProgressIntegration:
    """Integration tests for progress tracking functionality."""

    def test_full_migration_progress_simulation(self):
        """Test a complete migration progress simulation."""
        progress = MigrationProgress()

        with progress.progress_context():
            # Start migration
            migration_task = progress.add_migration_task("test-theme", 6)

            # Simulate 6-step migration
            steps = [
                ("git_ops", "Setting up Git branch"),
                ("docker_start", "Starting Docker environment"),
                ("create_files", "Creating Site Builder files"),
                ("migrate_styles", "Migrating SCSS styles"),
                ("predetermined_styles", "Adding predetermined styles"),
                ("map_components", "Migrating map components")
            ]

            for step_name, description in steps:
                # Add step
                progress.add_step_task(step_name, description, 100)

                # Simulate progress within step
                for _i in range(0, 101, 25):
                    progress.update_step_progress(step_name, 25)
                    time.sleep(0.01)  # Brief pause

                # Complete step
                progress.complete_step(step_name)

            # Check final state
            migration_progress = progress.progress.tasks[migration_task]
            assert migration_progress.completed == 6
            assert len(progress.step_tasks) == 0  # All steps should be removed

    def test_progress_with_errors(self):
        """Test progress tracking with simulated errors."""
        progress = MigrationProgress()

        with progress.progress_context():
            migration_task = progress.add_migration_task("test-theme", 3)

            # Complete first step successfully
            progress.add_step_task("step1", "Step 1", 100)
            progress.update_step_progress("step1", 100)
            progress.complete_step("step1")

            # Simulate error in step 2 (incomplete)
            progress.add_step_task("step2", "Step 2 (with error)", 100)
            progress.update_step_progress("step2", 50)
            # Don't complete step2 to simulate error

            # Check state
            migration_progress = progress.progress.tasks[migration_task]
            assert migration_progress.completed == 1  # Only first step completed
            assert "step2" in progress.step_tasks  # Second step still active

    def test_console_output_capture(self):
        """Test that progress can be captured for testing."""
        output = StringIO()
        console = Console(file=output, force_terminal=False, width=80)

        progress = MigrationProgress()
        # Override console for testing
        progress.progress.console = console

        with progress.progress_context():
            progress.add_migration_task("test-theme")
            progress.add_step_task("test_step", "Test step", 100)
            progress.update_step_progress("test_step", 50)
            progress.complete_step("test_step")

        # Verify output was captured
        output_text = output.getvalue()
        assert len(output_text) > 0  # Some output should be captured

    def test_subprocess_integration_no_hanging(self):
        """Test that subprocess integration doesn't hang CLI."""
        progress = MigrationProgress()

        with progress.progress_context():
            # Track a simple command that should complete quickly
            progress.track_subprocess(
                command=["echo", "test"],
                description="Test subprocess"
            )

            # Wait for completion with short timeout
            success = progress.wait_for_subprocess_completion(timeout=5.0)
            assert success  # Should complete quickly

    def test_subprocess_with_callback(self):
        """Test subprocess tracking with output callback."""
        progress = MigrationProgress()
        output_lines = []

        def capture_output(line):
            output_lines.append(line)

        with progress.progress_context():
            progress.track_subprocess(
                command=["echo", "hello world"],
                description="Test subprocess with callback",
                progress_callback=capture_output
            )

            success = progress.wait_for_subprocess_completion(timeout=5.0)
            assert success

        # Give time for output processing
        time.sleep(0.2)
        assert len(output_lines) > 0
        assert "hello world" in str(output_lines)

    def test_multiple_subprocess_tracking(self):
        """Test tracking multiple subprocess operations."""
        progress = MigrationProgress()

        with progress.progress_context():
            # Start multiple subprocess operations
            progress.track_subprocess(
                command=["echo", "task1"],
                description="First task"
            )
            progress.track_subprocess(
                command=["echo", "task2"],
                description="Second task"
            )

            # Both should complete successfully
            success = progress.wait_for_subprocess_completion(timeout=10.0)
            assert success

    def test_subprocess_timeout_handling(self):
        """Test subprocess timeout handling."""
        progress = MigrationProgress()

        with progress.progress_context():
            # Track a command that might take longer
            progress.track_subprocess(
                command=["sleep", "0.1"],
                description="Test timeout"
            )

            # Very short timeout should still work for sleep 0.1
            success = progress.wait_for_subprocess_completion(timeout=1.0)
            assert success  # Should complete within 1 second

    def test_progress_thread_cleanup(self):
        """Test that background threads are properly cleaned up."""
        progress = MigrationProgress()

        with progress.progress_context():
            progress.track_subprocess(
                command=["echo", "cleanup test"],
                description="Cleanup test"
            )
            progress.wait_for_subprocess_completion(timeout=5.0)

        # After context exit, threads should be cleaned up
        assert len(progress._subprocess_threads) == 0
        assert progress._update_thread is None or not progress._update_thread.is_alive()
