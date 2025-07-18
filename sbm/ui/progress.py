"""
Progress tracking components for the SBM CLI tool.

This module provides Rich-enhanced progress tracking for migration workflows,
including multi-step progress bars and real-time status updates.
"""

from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TimeElapsedColumn, 
    BarColumn, 
    TaskProgressColumn,
    TextColumn
)
from typing import Dict, Any, Optional
from contextlib import contextmanager
import time


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
    
    @contextmanager
    def progress_context(self):
        """
        Context manager for progress display.
        
        Yields:
            Self instance for method chaining
        """
        self._start_time = time.time()
        with self.progress:
            yield self
    
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
        self.tasks['migration'] = task_id
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
        if step_name in self.step_tasks:
            task_id = self.step_tasks[step_name]
            if description:
                self.progress.update(task_id, description=f"[progress]{description}[/]")
            self.progress.update(task_id, advance=advance)
    
    def complete_step(self, step_name: str):
        """
        Mark a step as complete and advance overall migration.
        
        Args:
            step_name: Name of the step to complete
        """
        if step_name in self.step_tasks:
            task_id = self.step_tasks[step_name]
            
            # Ensure task still exists before updating
            if task_id in self.progress.tasks:
                self.progress.update(task_id, completed=self.progress.tasks[task_id].total)
                
                # Remove the step task and advance migration
                self.progress.remove_task(task_id)
            
            del self.step_tasks[step_name]
            
            # Advance overall migration
            if 'migration' in self.tasks:
                migration_task_id = self.tasks['migration']
                if migration_task_id in self.progress.tasks:
                    self.progress.update(migration_task_id, advance=1)
    
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
        self.tasks['file_processing'] = task_id
        return task_id
    
    def update_file_progress(self, filename: str, advance: int = 1):
        """
        Update file processing progress.
        
        Args:
            filename: Name of current file being processed
            advance: Amount to advance progress
        """
        if 'file_processing' in self.tasks:
            task_id = self.tasks['file_processing']
            self.progress.update(
                task_id,
                description=f"[progress]Processing {filename}...[/]",
                advance=advance
            )
    
    def complete_file_processing(self):
        """Complete file processing task."""
        if 'file_processing' in self.tasks:
            task_id = self.tasks['file_processing']
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
        self.progress.update(
            task_id,
            description=f"[progress]✅ {final_message}[/]"
        )
        # Remove task after a brief pause
        time.sleep(0.5)
        self.progress.remove_task(task_id)
    
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