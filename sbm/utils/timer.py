"""
Timer and progress tracking utilities for SBM.

This module provides timing capabilities with pause/resume functionality
for tracking automation time vs user interaction time.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional

from sbm.utils.logger import logger


# Global timing summary storage
_timing_summary: Dict[str, float] = {}
_current_theme: Optional[str] = None


@dataclass
class TimerSegment:
    """Represents a timed segment of the migration process."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    paused_duration: float = 0.0

    @property
    def duration(self) -> float:
        """Get the total duration excluding paused time."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) - self.paused_duration

    @property
    def is_running(self) -> bool:
        """Check if this segment is currently running."""
        return self.end_time is None


class MigrationTimer:
    """
    Tracks timing for migration processes with pause/resume capabilities.
    
    This timer can pause during user interactions and resume for automated
    tasks, allowing separate tracking of automation time vs total time.
    """

    def __init__(self, theme_name: str):
        """
        Initialize the migration timer.
        
        Args:
            theme_name: Name of the theme being migrated
        """
        self.theme_name = theme_name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.current_segment: Optional[TimerSegment] = None
        self.segments: List[TimerSegment] = []
        self.pause_start: Optional[float] = None
        self.total_paused_time = 0.0
        self.is_paused = False

        logger.info(f"Migration timer started for {theme_name}")

    def start_segment(self, name: str):
        """
        Start a new timed segment.
        
        Args:
            name: Name of the segment (e.g., "Git Operations", "SCSS Migration")
        """
        # End current segment if running
        if self.current_segment and self.current_segment.is_running:
            self.end_segment()

        # Resume if paused
        if self.is_paused:
            self.resume()

        self.current_segment = TimerSegment(name=name, start_time=time.time())
        logger.debug(f"Started timer segment: {name}")

    def end_segment(self):
        """End the current segment."""
        if self.current_segment and self.current_segment.is_running:
            self.current_segment.end_time = time.time()
            self.segments.append(self.current_segment)

            duration = self.current_segment.duration
            logger.debug(f"Completed timer segment: {self.current_segment.name} ({duration:.2f}s)")

            self.current_segment = None

    def pause(self, reason: str = "User interaction"):
        """
        Pause the timer (e.g., during user prompts).
        
        Args:
            reason: Reason for pausing (for logging)
        """
        if not self.is_paused:
            self.pause_start = time.time()
            self.is_paused = True
            logger.debug(f"Timer paused: {reason}")

    def resume(self, reason: str = "Resuming automation"):
        """
        Resume the timer after a pause.
        
        Args:
            reason: Reason for resuming (for logging)
        """
        if self.is_paused and self.pause_start is not None:
            pause_duration = time.time() - self.pause_start
            self.total_paused_time += pause_duration

            # Add pause time to current segment if running
            if self.current_segment:
                self.current_segment.paused_duration += pause_duration

            self.pause_start = None
            self.is_paused = False
            logger.debug(f"Timer resumed: {reason} (paused for {pause_duration:.2f}s)")

    def finish(self):
        """Finish the migration timer."""
        # End current segment
        if self.current_segment and self.current_segment.is_running:
            self.end_segment()

        # Resume if paused to get accurate end time
        if self.is_paused:
            self.resume("Migration finished")

        self.end_time = time.time()
        logger.info(f"Migration timer finished for {self.theme_name}")

    @property
    def total_time(self) -> float:
        """Get total elapsed time including pauses."""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def automation_time(self) -> float:
        """Get time spent on automation (excluding pauses)."""
        return self.total_time - self.total_paused_time

    @property
    def user_interaction_time(self) -> float:
        """Get time spent on user interactions (paused time)."""
        return self.total_paused_time

    def get_summary(self) -> Dict[str, float]:
        """
        Get a summary of timing information.
        
        Returns:
            Dictionary with timing breakdown
        """
        return {
            "total_time": self.total_time,
            "automation_time": self.automation_time,
            "user_interaction_time": self.user_interaction_time,
            "automation_percentage": (self.automation_time / self.total_time * 100) if self.total_time > 0 else 0,
            "segments": {seg.name: seg.duration for seg in self.segments}
        }

    def print_summary(self):
        """Print a formatted summary of the timing."""
        summary = self.get_summary()

        print(f"\n⏱️  Migration Timing Summary for {self.theme_name}")
        print("=" * 60)
        print(f"Total Time:           {summary['total_time']:.2f} seconds")
        print(f"Automation Time:      {summary['automation_time']:.2f} seconds")
        print(f"User Interaction:     {summary['user_interaction_time']:.2f} seconds")
        print(f"Automation Efficiency: {summary['automation_percentage']:.1f}%")

        if self.segments:
            print("\nSegment Breakdown:")
            for segment in self.segments:
                print(f"  {segment.name:<25} {segment.duration:.2f}s")

        print("=" * 60)


# Global timer instance
_current_timer: Optional[MigrationTimer] = None


def start_migration_timer(theme_name: str) -> MigrationTimer:
    """
    Start a new migration timer.
    
    Args:
        theme_name: Name of the theme being migrated
        
    Returns:
        MigrationTimer instance
    """
    global _current_timer
    _current_timer = MigrationTimer(theme_name)
    return _current_timer


def get_current_timer() -> Optional[MigrationTimer]:
    """Get the current migration timer if one is active."""
    return _current_timer


def finish_migration_timer():
    """Finish the current migration timer."""
    global _current_timer
    if _current_timer:
        _current_timer.finish()
        _current_timer.print_summary()
        _current_timer = None


@contextmanager
def timer_segment(name: str):
    """
    Context manager for timing a segment of work.
    Creates standalone segment timer if no main timer exists.
    
    Args:
        name: Name of the segment
    """
    timer = get_current_timer()
    if timer:
        # Use existing timer system
        timer.start_segment(name)
        try:
            yield timer
        finally:
            timer.end_segment()
    else:
        # Create standalone segment timer and track in global summary
        start_time = time.time()
        logger.info(f"⏱️  Started: {name}")
        try:
            yield None
        finally:
            duration = time.time() - start_time
            logger.info(f"✅ Completed: {name} ({duration:.2f}s)")
            
            # Add to global timing summary
            global _timing_summary
            _timing_summary[name] = duration


@contextmanager
def timer_pause(reason: str = "User interaction"):
    """
    Context manager for pausing the timer.
    
    Args:
        reason: Reason for pausing
    """
    timer = get_current_timer()
    if timer:
        timer.pause(reason)
        try:
            yield timer
        finally:
            timer.resume()
    else:
        # No timer to pause, just yield None
        yield None


def patch_click_confirm_for_timing():
    """Patch click.confirm to automatically pause/resume timer."""
    import click

    original_confirm = click.confirm

    def timed_confirm(*args, **kwargs):
        """Wrapper that pauses timer during confirmation."""
        with timer_pause("User confirmation prompt"):
            return original_confirm(*args, **kwargs)

    click.confirm = timed_confirm
    return original_confirm


def restore_click_confirm(original_confirm):
    """Restore the original click.confirm function."""
    import click
    click.confirm = original_confirm


def init_timing_summary(theme_name: str):
    """Initialize timing summary for a theme migration."""
    global _timing_summary, _current_theme
    _timing_summary = {}
    _current_theme = theme_name


def get_timing_summary() -> Dict[str, float]:
    """Get the current timing summary."""
    return _timing_summary.copy()


def print_timing_summary():
    """Print a beautiful Rich timing summary box."""
    if not _timing_summary or not _current_theme:
        return
        
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        
        console = Console()
        
        # Calculate totals
        total_time = sum(_timing_summary.values())
        
        # Calculate automation time (exclude Docker time as requested)
        docker_time = _timing_summary.get("Docker Startup", 0)
        automation_time = total_time - docker_time
        automation_percentage = (automation_time / total_time * 100) if total_time > 0 else 100.0
        
        # Create timing table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Step", style="white", width=25)
        table.add_column("Duration", style="green", justify="right", width=12)
        table.add_column("Percentage", style="yellow", justify="right", width=10)
        
        # Add each segment to the table
        for segment_name, duration in _timing_summary.items():
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            
            # Format duration
            if duration < 60:
                duration_str = f"{duration:.2f}s"
            elif duration < 3600:
                minutes = int(duration // 60)
                seconds = duration % 60
                duration_str = f"{minutes}m {seconds:.1f}s"
            else:
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = duration % 60
                duration_str = f"{hours}h {minutes}m {seconds:.1f}s"
            
            table.add_row(
                segment_name,
                duration_str,
                f"{percentage:.1f}%"
            )
        
        # Format total time
        if total_time < 60:
            total_str = f"{total_time:.2f} seconds"
        elif total_time < 3600:
            minutes = int(total_time // 60)
            seconds = total_time % 60
            total_str = f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            seconds = total_time % 60
            total_str = f"{hours}h {minutes}m {seconds:.1f}s"
        
        # Create summary content
        summary_content = Text()
        summary_content.append("🎯 ", style="bold blue")
        summary_content.append("Migration Timing Summary for ", style="white")
        summary_content.append(_current_theme, style="bold cyan")
        summary_content.append("\n\n")
        
        # Format automation time
        if automation_time < 60:
            automation_str = f"{automation_time:.2f} seconds"
        elif automation_time < 3600:
            minutes = int(automation_time // 60)
            seconds = automation_time % 60
            automation_str = f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(automation_time // 3600)
            minutes = int((automation_time % 3600) // 60)
            seconds = automation_time % 60
            automation_str = f"{hours}h {minutes}m {seconds:.1f}s"
        
        # Format docker time
        if docker_time < 60:
            docker_str = f"{docker_time:.2f} seconds"
        elif docker_time < 3600:
            minutes = int(docker_time // 60)
            seconds = docker_time % 60
            docker_str = f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(docker_time // 3600)
            minutes = int((docker_time % 3600) // 60)
            seconds = docker_time % 60
            docker_str = f"{hours}h {minutes}m {seconds:.1f}s"
        
        summary_content.append("📊 Total Time: ", style="bold white")
        summary_content.append(total_str, style="bold green")
        summary_content.append("\n")
        
        summary_content.append("🤖 Automation Time: ", style="bold white") 
        summary_content.append(automation_str, style="bold green")
        summary_content.append("\n")
        
        summary_content.append("🐳 Docker Setup Time: ", style="bold white")
        summary_content.append(docker_str, style="bold blue")
        summary_content.append("\n")
        
        summary_content.append("⚡ Automation Efficiency: ", style="bold white")
        summary_content.append(f"{automation_percentage:.1f}%", style="bold green")
        
        # Print the main panel
        console.print(Panel(
            summary_content,
            title="⏱️  Migration Timer Results",
            title_align="center",
            border_style="bright_blue",
            padding=(1, 2)
        ))
        
        # Print the detailed breakdown table
        console.print(Panel(
            table,
            title="📋 Segment Breakdown",
            title_align="center", 
            border_style="bright_green",
            padding=(1, 1)
        ))
        
    except ImportError:
        # Fallback to plain text if Rich is not available
        print(f"\n⏱️  Migration Timing Summary for {_current_theme}")
        print("=" * 60)
        print(f"Total Time:           {total_time:.2f} seconds")
        print(f"Automation Time:      {automation_time:.2f} seconds")
        print(f"Docker Setup Time:    {docker_time:.2f} seconds")
        print(f"Automation Efficiency: {automation_percentage:.1f}%")
        
        if _timing_summary:
            print("\nSegment Breakdown:")
            for segment_name, duration in _timing_summary.items():
                print(f"  {segment_name:<25} {duration:.2f}s")
        
        print("=" * 60)


def clear_timing_summary():
    """Clear the timing summary."""
    global _timing_summary, _current_theme
    _timing_summary = {}
    _current_theme = None
