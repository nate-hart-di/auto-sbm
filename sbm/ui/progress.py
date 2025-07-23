"""
Progress tracking components for the SBM CLI tool.

This module provides Rich-enhanced progress tracking for migration workflows,
including multi-step progress bars and real-time status updates.
"""

import logging
import queue
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

logger = logging.getLogger(__name__)


@dataclass
class SubprocessUpdate:
    """Data class for subprocess progress updates."""

    task_id: int
    message: str
    progress: Optional[int] = None
    completed: bool = False
    error: Optional[str] = None


class MigrationProgress:
    """
    Enhanced progress tracking for SBM migration workflow.

    This class provides visual progress tracking for the 6-step migration process,
    with support for both determinate and indeterminate progress indicators.
    """

    def __init__(self, show_speed: bool = False) -> None:
        """
        Initialize migration progress tracker.

        Args:
            show_speed: Whether to show processing speed (default: False)
        """
        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ]

        if show_speed:
            from rich.progress import MofNCompleteColumn

            columns.insert(-1, MofNCompleteColumn())

        self.progress = Progress(*columns, expand=True)
        self.tasks: dict[str, Any] = {}
        self.step_tasks: dict[str, Any] = {}

        # Enhanced timing tracking
        self._start_time = None
        self._step_times: dict[str, dict[str, float]] = {}
        self._current_step = None
        self._migration_completed = False
        self._total_migration_time = None

        # Non-blocking subprocess integration
        self._subprocess_queue: queue.Queue = queue.Queue()
        self._subprocess_threads: list[threading.Thread] = []
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()
        self._lock = threading.Lock()

    @contextmanager
    def progress_context(self):
        """
        Context manager for progress display with exception safety.

        Yields:
            Self instance for method chaining
        """
        self._start_time = time.time()
        logger.debug("Migration progress tracking started")

        try:
            # Start background update thread for subprocess communication
            self._start_update_thread()
            with self.progress:
                yield self
        except Exception:
            # Clean up all active tasks on error
            self._cleanup_all_tasks()
            logger.exception("Migration progress interrupted due to error")
            raise
        finally:
            # Complete migration timing
            if self._start_time and not self._migration_completed:
                self._total_migration_time = time.time() - self._start_time
                self._migration_completed = True
                logger.debug("Migration progress completed in %.2fs", self._total_migration_time)

            # Stop background threads first
            self._stop_update_thread()
            # Force cleanup all tasks before exit
            self._cleanup_all_tasks()
            # Ensure clean state
            self._reset_state()

    def add_migration_task(self, theme_name: str, total_steps: int = 6) -> int:
        """
        Add overall migration task.

        Args:
            theme_name: Name of the theme being migrated
            total_steps: Total number of migration steps

        Returns:
            Task ID for the migration task
        """
        task_id = self.progress.add_task(f"[cyan]Migrating {theme_name}[/]", total=total_steps)
        self.tasks["migration"] = task_id
        return task_id

    def add_step_task(self, step_name: str, description: str, total: int = 100) -> int:
        """
        Add individual step task.

        Args:
            step_name: Name/key for the step
            description: Human-readable description
            total: Total units for this step

        Returns:
            Task ID for the step task
        """
        task_id = self.progress.add_task(f"[progress]{description}[/]", total=total)
        self.step_tasks[step_name] = task_id
        return task_id

    def update_step_progress(
        self, step_name: str, completed: int, description: Optional[str] = None
    ) -> None:
        """
        Update progress for a specific step.

        Args:
            step_name: Name of the step to update
            completed: Amount of completed work
            description: Optional new description
        """
        if step_name not in self.step_tasks:
            logger.warning("Task %s for step %s no longer exists", step_name, step_name)
            return

        task_id = self.step_tasks[step_name]

        try:
            # Update progress
            self.progress.update(task_id, completed=completed)

            # Update description if provided
            if description:
                self.progress.update(task_id, description=f"[progress]{description}[/]")

        except (KeyError, IndexError):
            logger.warning("Task %s for step %s no longer exists", task_id, step_name)

    def complete_step(self, step_name: str) -> None:
        """
        Complete a migration step and advance migration progress.

        Args:
            step_name: Name of the step to complete
        """
        if step_name not in self.step_tasks:
            logger.warning("Step %s not found in step_tasks", step_name)
            return

        task_id = self.step_tasks[step_name]

        try:
            # Rich Progress tasks is a list, TaskID is the index
            # Check if task_id is valid index and task exists
            if 0 <= task_id < len(self.progress.tasks):
                task = self.progress.tasks[task_id]

                # Mark task as complete and hide it (don't remove to preserve IDs)
                self.progress.update(task_id, completed=task.total, visible=False)

                # Remove from our tracking
                del self.step_tasks[step_name]

                # Advance migration progress
                if "migration" in self.tasks:
                    migration_task_id = self.tasks["migration"]
                    if 0 <= migration_task_id < len(self.progress.tasks):
                        self.progress.update(migration_task_id, advance=1)

                logger.debug("Step '%s' completed successfully", step_name)
            else:
                logger.error("Task %s not found in progress tracker", task_id)

        except (KeyError, IndexError) as e:
            logger.exception("Error completing task %s: %s", task_id, e)

    def add_file_processing_task(self, file_count: int) -> int:
        """
        Add file processing task for tracking individual file operations.

        Args:
            file_count: Number of files to process

        Returns:
            Task ID for file processing
        """
        task_id = self.progress.add_task("[progress]Processing files...[/]", total=file_count)
        self.tasks["file_processing"] = task_id
        return task_id

    def update_file_progress(self, filename: str, advance: int = 1) -> None:
        """
        Update file processing progress.

        Args:
            filename: Name of current file being processed
            advance: Amount to advance progress
        """
        if "file_processing" in self.tasks:
            task_id = self.tasks["file_processing"]
            self.progress.update(
                task_id, description=f"[progress]Processing {filename}...[/]", advance=advance
            )

    def complete_file_processing(self) -> None:
        """Complete file processing task."""
        if "file_processing" in self.tasks:
            task_id = self.tasks["file_processing"]
            self.progress.update(
                task_id,
                description="[progress]✅ File processing complete[/]",
                completed=self.progress.tasks[task_id].total,
            )

    def add_indeterminate_task(self, description: str) -> int:
        """
        Add indeterminate task (spinner only).

        Args:
            description: Task description

        Returns:
            Task ID for indeterminate task
        """
        return self.progress.add_task(
            f"[progress]{description}[/]",
            total=None,  # Indeterminate
        )

    def update_indeterminate_task(self, task_id: int, description: str) -> None:
        """
        Update indeterminate task description.

        Args:
            task_id: Task ID to update
            description: New description
        """
        self.progress.update(task_id, description=f"[progress]{description}[/]")

    def complete_indeterminate_task(self, task_id: int, final_message: str) -> None:
        """
        Complete indeterminate task with final message.

        Args:
            task_id: Task ID to complete
            final_message: Final completion message
        """
        if task_id not in self.progress.tasks:
            return

        try:
            self.progress.update(task_id, description=f"[progress]✅ {final_message}[/]")
            # Remove immediately without timing dependency
            self.progress.remove_task(task_id)
        except Exception as e:
            logger.warning("Error completing indeterminate task %s: %s", task_id, e)

    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since progress started.

        Returns:
            Elapsed time in seconds
        """
        if self._start_time:
            return time.time() - self._start_time
        return 0.0

    def start_step_timing(self, step_name: str) -> None:
        """
        Start timing for a migration step.

        Args:
            step_name: Name of the step to track
        """
        current_time = time.time()
        if step_name not in self._step_times:
            self._step_times[step_name] = {}

        self._step_times[step_name]["start"] = current_time
        self._current_step = step_name
        logger.debug("Started timing for step: %s", step_name)

    def complete_step_timing(self, step_name: str) -> float:
        """
        Complete timing for a migration step.

        Args:
            step_name: Name of the step to complete

        Returns:
            Duration of the step in seconds
        """
        current_time = time.time()

        if step_name in self._step_times and "start" in self._step_times[step_name]:
            start_time = self._step_times[step_name]["start"]
            duration = current_time - start_time
            self._step_times[step_name]["end"] = current_time
            self._step_times[step_name]["duration"] = duration

            logger.debug("Completed step '%s' in %.2fs", step_name, duration)
            return duration
        logger.warning("No start time found for step: %s", step_name)
        return 0.0

    def get_step_duration(self, step_name: str) -> float:
        """
        Get duration of a completed step.

        Args:
            step_name: Name of the step

        Returns:
            Duration in seconds, or 0.0 if step not found/completed
        """
        if step_name in self._step_times and "duration" in self._step_times[step_name]:
            return self._step_times[step_name]["duration"]
        return 0.0

    def get_total_migration_time(self) -> float:
        """
        Get total migration time.

        Returns:
            Total migration time in seconds, or current elapsed time if not completed
        """
        if self._total_migration_time is not None:
            return self._total_migration_time
        return self.get_elapsed_time()

    def get_timing_summary(self) -> dict[str, float]:
        """
        Get comprehensive timing summary.

        Returns:
            Dictionary with timing information for all steps and total time
        """
        summary = {
            "total_time": self.get_total_migration_time(),
            "elapsed_time": self.get_elapsed_time(),
            "steps": {}
        }

        for step_name, timing_data in self._step_times.items():
            if "duration" in timing_data:
                summary["steps"][step_name] = timing_data["duration"]
            elif "start" in timing_data:
                # Step in progress
                current_duration = time.time() - timing_data["start"]
                summary["steps"][step_name] = current_duration

        return summary

    def format_duration(self, seconds: float) -> str:
        """
        Format duration for display.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"

    def get_task_progress(self, task_id: int) -> float:
        """
        Get completion percentage for a task.

        Args:
            task_id: Task ID to check

        Returns:
            Completion percentage (0.0 to 100.0)
        """
        if task_id in self.progress.tasks:
            task = self.progress.tasks[task_id]
            if task.total and task.total > 0:
                return (task.completed / task.total) * 100
        return 0.0

    def _advance_migration_progress(self) -> None:
        """
        Advance overall migration progress by one step.
        """
        try:
            if "migration" in self.tasks:
                migration_task_id = self.tasks["migration"]
                if migration_task_id in self.progress.tasks:
                    self.progress.update(migration_task_id, advance=1)
        except Exception as e:
            logger.warning("Error advancing migration progress: %s", e)

    def track_subprocess(
        self,
        command: list[str],
        description: str,
        cwd: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """
        Track subprocess execution without blocking Rich UI.

        Args:
            command: Command list to execute
            description: Description for progress display
            cwd: Working directory for command
            progress_callback: Optional callback for custom progress parsing

        Returns:
            Task ID for tracking progress
        """
        with self._lock:
            task_id = self.progress.add_task(
                f"[progress]{description}[/]",
                total=None,  # Indeterminate for subprocess
            )

        # Start subprocess in background thread
        thread = threading.Thread(
            target=self._run_subprocess_background,
            args=(task_id, command, description, cwd, progress_callback),
            daemon=True,
        )
        self._subprocess_threads.append(thread)
        thread.start()

        return task_id

    def _run_subprocess_background(
        self,
        task_id: int,
        command: list[str],
        description: str,
        cwd: Optional[str],
        progress_callback: Optional[Callable[[str], None]],
    ) -> None:
        """
        Run subprocess in background thread and send updates via queue.
        """
        try:
            # Send initial status
            self._subprocess_queue.put(
                SubprocessUpdate(
                    task_id=task_id, message=f"{description} - Starting...", progress=None
                )
            )

            # Start subprocess with real-time output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=cwd,
            )

            # Monitor output in real-time
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break

                if output:
                    line = output.strip()
                    # Send progress update
                    self._subprocess_queue.put(
                        SubprocessUpdate(
                            task_id=task_id,
                            message=f"{description} - {line[:50]}...",
                            progress=None,
                        )
                    )

                    # Call custom progress callback if provided
                    if progress_callback:
                        progress_callback(line)

            # Wait for completion
            returncode = process.wait()

            # Send completion status
            if returncode == 0:
                self._subprocess_queue.put(
                    SubprocessUpdate(
                        task_id=task_id, message=f"✅ {description} - Complete", completed=True
                    )
                )
            else:
                stderr_output = process.stderr.read()
                self._subprocess_queue.put(
                    SubprocessUpdate(
                        task_id=task_id,
                        message=f"❌ {description} - Failed",
                        completed=True,
                        error=stderr_output,
                    )
                )

        except Exception as e:
            # Send error status
            self._subprocess_queue.put(
                SubprocessUpdate(
                    task_id=task_id,
                    message=f"❌ {description} - Error: {e!s}",
                    completed=True,
                    error=str(e),
                )
            )

    def _start_update_thread(self) -> None:
        """Start background thread to process subprocess updates."""
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_updates.clear()
            self._update_thread = threading.Thread(
                target=self._process_subprocess_updates, daemon=True
            )
            self._update_thread.start()

    def _stop_update_thread(self) -> None:
        """Stop background update thread."""
        self._stop_updates.set()

        # Stop main update thread with reasonable timeout
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5.0)  # Reasonable timeout for cleanup
            if self._update_thread.is_alive():
                logger.warning("Update thread failed to stop within timeout")

        # Clean up subprocess threads safely
        self._cleanup_subprocess_threads()

    def _cleanup_subprocess_threads(self) -> bool:
        """Safe thread cleanup with proper timeout handling."""
        cleanup_success = True

        # PATTERN: Copy list to avoid modification during iteration
        threads_to_cleanup = self._subprocess_threads[:]

        for thread in threads_to_cleanup:
            if thread.is_alive():
                # CRITICAL: Configurable timeout, not hardcoded
                thread.join(timeout=5.0)  # Reasonable timeout for cleanup
                if thread.is_alive():
                    logger.warning("Thread %s failed to cleanup within timeout", thread.name)
                    cleanup_success = False
                else:
                    # PATTERN: Remove completed threads immediately (thread-safe)
                    with self._lock:
                        if thread in self._subprocess_threads:
                            self._subprocess_threads.remove(thread)

        # Clear any remaining threads (those that didn't respond to cleanup)
        with self._lock:
            remaining_count = len(self._subprocess_threads)
            if remaining_count > 0:
                logger.warning("Forcibly clearing %s unresponsive threads", remaining_count)
                self._subprocess_threads.clear()

        return cleanup_success

    def _process_subprocess_updates(self) -> None:
        """Process subprocess updates from queue in background thread."""
        while not self._stop_updates.is_set():
            try:
                # Check for updates with timeout
                update = self._subprocess_queue.get(timeout=0.1)

                # Apply update to Rich progress (thread-safe)
                with self._lock:
                    if update.task_id in self.progress.tasks:
                        self.progress.update(
                            update.task_id, description=f"[progress]{update.message}[/]"
                        )

                        # Remove completed tasks
                        if update.completed:
                            # Small delay for user to see completion message
                            time.sleep(0.5)
                            self.progress.remove_task(update.task_id)

                        # Log errors
                        if update.error:
                            logger.error("Subprocess error: %s", update.error)

                self._subprocess_queue.task_done()

            except queue.Empty:
                # Timeout - continue checking for stop signal
                continue
            except Exception as e:
                logger.warning("Error processing subprocess update: %s", e)

    def wait_for_subprocess_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all subprocess operations to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all completed successfully, False if timeout or error
        """
        start_time = time.time()
        completed_successfully = True

        # PATTERN: Copy list to avoid modification during iteration
        threads_to_wait = self._subprocess_threads[:]

        for i, thread in enumerate(threads_to_wait):
            if thread.is_alive():
                remaining_time = None
                if timeout:
                    elapsed = time.time() - start_time
                    remaining_time = max(0, timeout - elapsed)
                    if remaining_time <= 0:
                        logger.warning(
                            "Timeout reached (%ss): Subprocess thread %s still running", timeout, i
                        )
                        completed_successfully = False
                        break

                # CRITICAL: Per-thread timeout, not global
                thread_timeout = (
                    remaining_time if remaining_time else 30.0
                )  # Default 30s per thread
                thread.join(timeout=thread_timeout)

                if thread.is_alive():
                    logger.warning(
                        "Subprocess thread %s (%s) failed to complete within %ss timeout",
                        i, thread.name, thread_timeout
                    )
                    completed_successfully = False
                else:
                    # PATTERN: Remove completed threads immediately (thread-safe)
                    with self._lock:
                        if thread in self._subprocess_threads:
                            self._subprocess_threads.remove(thread)
                    logger.debug("Subprocess thread %s (%s) completed successfully", i, thread.name)

        # Process any remaining updates from completed threads
        self._process_remaining_updates()

        return completed_successfully

    def _cleanup_all_tasks(self) -> None:
        """
        Clean up all active tasks on error.
        """
        # Clean up main tasks
        for task_name, task_id in list(self.tasks.items()):
            try:
                if task_id in self.progress.tasks:
                    self.progress.remove_task(task_id)
            except Exception as e:
                logger.debug("Error removing task %s: %s", task_name, e)

        # Clean up step tasks
        for step_name, task_id in list(self.step_tasks.items()):
            try:
                if task_id in self.progress.tasks:
                    self.progress.remove_task(task_id)
            except Exception as e:
                logger.debug("Error removing step task %s: %s", step_name, e)

        # Clear dictionaries
        self.tasks.clear()
        self.step_tasks.clear()

    def _reset_state(self) -> None:
        """
        Reset progress tracker to clean state.
        """
        self.tasks.clear()
        self.step_tasks.clear()
        self._start_time = None

        # Clear subprocess state
        self._subprocess_threads.clear()
        self._stop_updates.clear()
        self._update_thread = None

    def _process_remaining_updates(self) -> None:
        """
        Process any remaining updates from completed subprocess threads.
        """
        processed_count = 0
        while not self._subprocess_queue.empty() and processed_count < 50:  # Safety limit
            try:
                update = self._subprocess_queue.get_nowait()

                # Log final status or errors
                if update.completed:
                    if update.error:
                        logger.error("Subprocess completed with error: %s", update.error)
                    else:
                        logger.debug("Subprocess completed successfully: %s", update.message)

                self._subprocess_queue.task_done()
                processed_count += 1
            except queue.Empty:
                break

        # No more recursive calls - processed_count safety limit handles cleanup
