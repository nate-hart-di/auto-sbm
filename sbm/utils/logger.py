"""
Enhanced logging system for SBM Tool V2.

Provides Rich console output, progress tracking, migration headers/summaries,
and demo mode banner support for team-friendly user experience.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box


class SBMLogger:
    """Enhanced logger with Rich console integration."""
    
    def __init__(self, name: str = "sbm"):
        self.name = name
        self.console = Console()
        self._logger = logging.getLogger(name)
        self._progress: Optional[Progress] = None
        self._current_task: Optional[TaskID] = None
        
    def setup(self, level: str = "INFO", log_file: Optional[str] = None) -> None:
        """Setup logging configuration."""
        # Clear existing handlers
        self._logger.handlers.clear()
        
        # Set level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(log_level)
        
        # Rich console handler
        rich_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True
        )
        rich_handler.setLevel(log_level)
        self._logger.addHandler(rich_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(message, **kwargs)
    
    def success(self, message: str) -> None:
        """Log success message with green styling."""
        self.console.print(f"✅ {message}", style="green")
    
    def failure(self, message: str) -> None:
        """Log failure message with red styling."""
        self.console.print(f"❌ {message}", style="red")
    
    def step(self, message: str) -> None:
        """Log step message with blue styling."""
        self.console.print(f"🔄 {message}", style="blue")
    
    def migration_header(self, slug: str, oem: str = "Unknown") -> None:
        """Display migration header banner."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("SBM Tool V2 - Site Builder Migration\n", style="bold blue")
        header_text.append(f"Dealer: {slug}\n", style="bold white")
        header_text.append(f"OEM: {oem}\n", style="bold cyan")
        header_text.append(f"Started: {timestamp}", style="dim white")
        
        panel = Panel(
            header_text,
            title="🚀 Migration Started",
            border_style="blue",
            box=box.ROUNDED
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()
    
    def migration_summary(self, slug: str, success: bool, duration: float, 
                         files_created: int = 0, errors: int = 0) -> None:
        """Display migration summary."""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        status_style = "green" if success else "red"
        
        summary_text = Text()
        summary_text.append(f"Status: {status}\n", style=f"bold {status_style}")
        summary_text.append(f"Duration: {duration:.2f}s\n", style="white")
        summary_text.append(f"Files Created: {files_created}\n", style="cyan")
        if errors > 0:
            summary_text.append(f"Errors: {errors}\n", style="red")
        
        panel = Panel(
            summary_text,
            title=f"📊 Migration Summary - {slug}",
            border_style=status_style,
            box=box.ROUNDED
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()
    
    def demo_banner(self) -> None:
        """Display demo mode banner."""
        banner_text = Text()
        banner_text.append("🎯 DEMO MODE ACTIVE 🎯\n", style="bold yellow")
        banner_text.append("Enhanced logging and validation enabled\n", style="yellow")
        banner_text.append("Optimized for live presentation", style="dim yellow")
        
        panel = Panel(
            banner_text,
            title="Demo Mode",
            border_style="yellow",
            box=box.DOUBLE
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()
    

    
    def start_progress(self, description: str = "Processing...") -> None:
        """Start progress tracking."""
        if self._progress is None:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            )
            self._progress.start()
        
        self._current_task = self._progress.add_task(description, total=100)
    
    def update_progress(self, advance: int = 10, description: Optional[str] = None) -> None:
        """Update progress."""
        if self._progress and self._current_task is not None:
            if description:
                self._progress.update(self._current_task, description=description)
            self._progress.advance(self._current_task, advance)
    
    def complete_progress(self) -> None:
        """Complete and stop progress tracking."""
        if self._progress:
            if self._current_task is not None:
                self._progress.update(self._current_task, completed=100)
            self._progress.stop()
            self._progress = None
            self._current_task = None
    
    def validation_results(self, results: Dict[str, Any]) -> None:
        """Display validation results in a table."""
        table = Table(title="Validation Results", box=box.ROUNDED)
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        for check, result in results.items():
            if isinstance(result, dict):
                status = "✅" if result.get("passed", False) else "❌"
                details = result.get("message", "")
            else:
                status = "✅" if result else "❌"
                details = ""
            
            table.add_row(check, status, details)
        
        self.console.print()
        self.console.print(table)
        self.console.print()
    
    def error_with_suggestion(self, error: str, suggestion: str) -> None:
        """Display error with helpful suggestion."""
        error_text = Text()
        error_text.append(f"Error: {error}\n", style="bold red")
        error_text.append(f"Suggestion: {suggestion}", style="yellow")
        
        panel = Panel(
            error_text,
            title="❌ Error",
            border_style="red",
            box=box.ROUNDED
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()


# Global logger instances
_loggers: Dict[str, SBMLogger] = {}


def get_logger(name: str = "sbm") -> SBMLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        SBMLogger instance
    """
    if name not in _loggers:
        _loggers[name] = SBMLogger(name)
    return _loggers[name]


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Setup logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    logger = get_logger()
    logger.setup(level, log_file)


def reset_loggers() -> None:
    """Reset all logger instances (for testing)."""
    global _loggers
    _loggers.clear()


def reset_loggers() -> None:
    """Reset all logger instances (for testing)."""
    global _loggers
    _loggers.clear() 
