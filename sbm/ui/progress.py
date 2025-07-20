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
from typing import Any, Callable, Dict, List, Optional

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

    def __init__(self, show_speed: bool = False):
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
            TimeElapsedColumn()
        ]

        if show_speed:
            from rich.progress import MofNCompleteColumn
            columns.insert(-1, MofNCompleteColumn())

        self.progress = Progress(*columns, expand=True)
        self.tasks: Dict[str, Any] = {}
        self.step_tasks: Dict[str, Any] = {}
        self._start_time = None

        # Non-blocking subprocess integration
        self._subprocess_queue: queue.Queue = queue.Queue()
        self._subprocess_threads: List[threading.Thread] = []
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
        try:
            # Start background update thread for subprocess communication
            self._start_update_thread()
            with self.progress:
                yield self
        except Exception:
            # Clean up all active tasks on error
            self._cleanup_all_tasks()
            raise
        finally:
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
        task_id = self.progress.add_task(
            f"[cyan]Migrating {theme_name}[/]",
            total=total_steps
        )
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
        task_id = self.progress.add_task(
            f"[progress]{description}[/]",
            total=total
        )
        self.step_tasks[step_name] = task_id
        return task_id

    def update_step_progress(self, step_name: str, advance: int = 1,
                           description: str = None):
        """
        Update step progress and optionally advance overall migration.
        
        Args:
            step_name: Name of the step to update
            advance: Amount to advance progress
            description: Optional new description
        """
        if step_name not in self.step_tasks:
            logger.debug(f"Step {step_name} not found in active steps")
            return

        task_id = self.step_tasks[step_name]

        # Validate task still exists
        if task_id not in self.progress.tasks:
            logger.warning(f"Task {task_id} for step {step_name} no longer exists")
            # Clean up stale reference
            del self.step_tasks[step_name]
            return

        try:
            if description:
                self.progress.update(task_id, description=f"[progress]{description}[/]")
            self.progress.update(task_id, advance=advance)
        except Exception as e:
            logger.warning(f"Error updating progress for {step_name}: {e}")

    def complete_step(self, step_name: str):
        """
        Mark a step as complete and advance overall migration.
        
        Args:
            step_name: Name of the step to complete
        """
        if step_name not in self.step_tasks:
            return

        task_id = self.step_tasks[step_name]

        try:
            # Safely complete task
            if task_id in self.progress.tasks:
                task = self.progress.tasks[task_id]
                self.progress.update(task_id, completed=task.total)

            # Always clean up our tracking regardless of Rich's state
            if task_id in self.progress.tasks:
                self.progress.remove_task(task_id)

        except Exception as e:
            logger.warning(f"Error completing step {step_name}: {e}")
        finally:
            # Always clean up our dictionary
            del self.step_tasks[step_name]

            # Advance overall migration
            self._advance_migration_progress()

    def add_file_processing_task(self, file_count: int) -> int:
        """
        Add file processing task for tracking individual file operations.
        
        Args:
            file_count: Number of files to process
            
        Returns:
            Task ID for file processing
        """
        task_id = self.progress.add_task(
            "[progress]Processing files...[/]",
            total=file_count
        )
        self.tasks["file_processing"] = task_id
        return task_id

    def update_file_progress(self, filename: str, advance: int = 1):
        """
        Update file processing progress.
        
        Args:
            filename: Name of current file being processed
            advance: Amount to advance progress
        """
        if "file_processing" in self.tasks:
            task_id = self.tasks["file_processing"]
            self.progress.update(
                task_id,
                description=f"[progress]Processing {filename}...[/]",
                advance=advance
            )

    def complete_file_processing(self):
        """Complete file processing task."""
        if "file_processing" in self.tasks:
            task_id = self.tasks["file_processing"]
            self.progress.update(
                task_id,
                description="[progress]✅ File processing complete[/]",
                completed=self.progress.tasks[task_id].total
            )

    def add_indeterminate_task(self, description: str) -> int:
        """
        Add indeterminate task (spinner only).
        
        Args:
            description: Task description
            
        Returns:
            Task ID for indeterminate task
        """
        task_id = self.progress.add_task(
            f"[progress]{description}[/]",
            total=None  # Indeterminate
        )
        return task_id

    def update_indeterminate_task(self, task_id: int, description: str):
        """
        Update indeterminate task description.
        
        Args:
            task_id: Task ID to update
            description: New description
        """
        self.progress.update(
            task_id,
            description=f"[progress]{description}[/]"
        )

    def complete_indeterminate_task(self, task_id: int, final_message: str):
        """
        Complete indeterminate task with final message.
        
        Args:
            task_id: Task ID to complete
            final_message: Final completion message
        """
        if task_id not in self.progress.tasks:
            return

        try:
            self.progress.update(
                task_id,
                description=f"[progress]✅ {final_message}[/]"
            )
            # Remove immediately without timing dependency
            self.progress.remove_task(task_id)
        except Exception as e:
            logger.warning(f"Error completing indeterminate task {task_id}: {e}")

    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since progress started.
        
        Returns:
            Elapsed time in seconds
        """
        if self._start_time:
            return time.time() - self._start_time
        return 0.0

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

    def _advance_migration_progress(self):
        """
        Advance overall migration progress by one step.
        """
        try:
            if "migration" in self.tasks:
                migration_task_id = self.tasks["migration"]
                if migration_task_id in self.progress.tasks:
                    self.progress.update(migration_task_id, advance=1)
        except Exception as e:
            logger.warning(f"Error advancing migration progress: {e}")

    def track_subprocess(self, command: List[str], description: str,
                        cwd: Optional[str] = None,
                        progress_callback: Optional[Callable[[str], None]] = None) -> int:
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
                total=None  # Indeterminate for subprocess
            )

        # Start subprocess in background thread
        thread = threading.Thread(
            target=self._run_subprocess_background,
            args=(task_id, command, description, cwd, progress_callback),
            daemon=True
        )
        self._subprocess_threads.append(thread)
        thread.start()

        return task_id

    def _run_subprocess_background(self, task_id: int, command: List[str],
                                  description: str, cwd: Optional[str],
                                  progress_callback: Optional[Callable[[str], None]]):
        """
        Run subprocess in background thread and send updates via queue.
        """
        try:
            # Send initial status
            self._subprocess_queue.put(SubprocessUpdate(
                task_id=task_id,
                message=f"{description} - Starting...",
                progress=None
            ))

            # Start subprocess with real-time output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=cwd
            )

            # Monitor output in real-time
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break

                if output:
                    line = output.strip()
                    # Send progress update
                    self._subprocess_queue.put(SubprocessUpdate(
                        task_id=task_id,
                        message=f"{description} - {line[:50]}...",
                        progress=None
                    ))

                    # Call custom progress callback if provided
                    if progress_callback:
                        progress_callback(line)

            # Wait for completion
            returncode = process.wait()

            # Send completion status
            if returncode == 0:
                self._subprocess_queue.put(SubprocessUpdate(
                    task_id=task_id,
                    message=f"✅ {description} - Complete",
                    completed=True
                ))
            else:
                stderr_output = process.stderr.read()
                self._subprocess_queue.put(SubprocessUpdate(
                    task_id=task_id,
                    message=f"❌ {description} - Failed",
                    completed=True,
                    error=stderr_output
                ))

        except Exception as e:
            # Send error status
            self._subprocess_queue.put(SubprocessUpdate(
                task_id=task_id,
                message=f"❌ {description} - Error: {e!s}",
                completed=True,
                error=str(e)
            ))

    def _start_update_thread(self):
        """Start background thread to process subprocess updates."""
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_updates.clear()
            self._update_thread = threading.Thread(
                target=self._process_subprocess_updates,
                daemon=True
            )
            self._update_thread.start()

    def _stop_update_thread(self):
        """Stop background update thread."""
        self._stop_updates.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)

        # Wait for all subprocess threads to complete
        for thread in self._subprocess_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._subprocess_threads.clear()

    def _process_subprocess_updates(self):
        """Process subprocess updates from queue in background thread."""
        while not self._stop_updates.is_set():
            try:
                # Check for updates with timeout
                update = self._subprocess_queue.get(timeout=0.1)

                # Apply update to Rich progress (thread-safe)
                with self._lock:
                    if update.task_id in self.progress.tasks:
                        self.progress.update(
                            update.task_id,
                            description=f"[progress]{update.message}[/]"
                        )

                        # Remove completed tasks
                        if update.completed:
                            # Small delay for user to see completion message
                            time.sleep(0.5)
                            self.progress.remove_task(update.task_id)

                        # Log errors
                        if update.error:
                            logger.error(f"Subprocess error: {update.error}")

                self._subprocess_queue.task_done()

            except queue.Empty:
                # Timeout - continue checking for stop signal
                continue
            except Exception as e:
                logger.warning(f"Error processing subprocess update: {e}")

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

        for i, thread in enumerate(self._subprocess_threads):
            if thread.is_alive():
                remaining_time = None
                if timeout:
                    elapsed = time.time() - start_time
                    remaining_time = max(0, timeout - elapsed)
                    if remaining_time <= 0:
                        logger.warning(f"Timeout reached ({timeout}s): Subprocess thread {i} still running")
                        return False

                thread.join(timeout=remaining_time)
                if thread.is_alive():
                    logger.warning(f"Subprocess thread {i} failed to complete within timeout")
                    completed_successfully = False

        # Process any remaining updates from completed threads
        self._process_remaining_updates()
        
        return completed_successfully

    def _cleanup_all_tasks(self):
        """
        Clean up all active tasks on error.
        """
        # Clean up main tasks
        for task_name, task_id in list(self.tasks.items()):
            try:
                if task_id in self.progress.tasks:
                    self.progress.remove_task(task_id)
            except Exception as e:
                logger.debug(f"Error removing task {task_name}: {e}")

        # Clean up step tasks
        for step_name, task_id in list(self.step_tasks.items()):
            try:
                if task_id in self.progress.tasks:
                    self.progress.remove_task(task_id)
            except Exception as e:
                logger.debug(f"Error removing step task {step_name}: {e}")

        # Clear dictionaries
        self.tasks.clear()
        self.step_tasks.clear()

    def _reset_state(self):
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
    
    def _process_remaining_updates(self):
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
                        logger.error(f"Subprocess completed with error: {update.error}")
                    else:
                        logger.debug(f"Subprocess completed successfully: {update.message}")
                        
                self._subprocess_queue.task_done()
                processed_count += 1
            except queue.Empty:
                break

        # Clear any remaining updates in queue
        self._process_remaining_updates()
