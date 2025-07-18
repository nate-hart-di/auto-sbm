"""
Console management and theming for the SBM CLI tool.

This module provides centralized console management with Rich theming support,
ensuring consistent styling across all CLI components.
"""

from rich.console import Console
from rich.theme import Theme
from typing import Optional
import os
from ..config import Config


class SBMConsole:
    """
    Centralized console management for SBM CLI with theming support.
    
    This class provides a consistent interface for all Rich console operations
    throughout the SBM tool, with configuration-aware theming and fallback support.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize SBM console with optional configuration.
        
        Args:
            config: Optional Config object for theming and display options
        """
        self.config = config or Config({})
        self.theme = self._create_theme()
        
        # Check if Rich should be disabled (CI/CD environments)
        force_terminal = not self._is_ci_environment()
        
        self.console = Console(
            theme=self.theme,
            force_terminal=force_terminal,
            width=None,  # Auto-detect terminal width
            legacy_windows=False
        )
    
    def _create_theme(self) -> Theme:
        """
        Create SBM-specific theme with colorblind-friendly patterns.
        
        Returns:
            Rich Theme object with SBM color scheme
        """
        theme_name = self.config.get_setting('ui', {}).get('theme', 'default')
        
        if theme_name == 'high-contrast':
            return Theme({
                "info": "bright_cyan",
                "warning": "bright_yellow on black",
                "error": "bright_red on black",
                "success": "bright_green on black",
                "progress": "bright_blue",
                "step": "bright_cyan bold",
                "filename": "bright_white bold",
                "branch": "bright_magenta",
                "docker": "bright_blue",
                "git": "bright_green"
            })
        else:  # default theme
            return Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "success": "bold green",
                "progress": "blue",
                "step": "bold cyan",
                "filename": "bold white",
                "branch": "magenta",
                "docker": "blue",
                "git": "green"
            })
    
    def _is_ci_environment(self) -> bool:
        """
        Check if running in CI/CD environment.
        
        Returns:
            True if in CI environment, False otherwise
        """
        ci_indicators = [
            'CI', 'CONTINUOUS_INTEGRATION', 'GITHUB_ACTIONS',
            'TRAVIS', 'CIRCLECI', 'JENKINS_URL', 'GITLAB_CI'
        ]
        
        return any(os.getenv(var) for var in ci_indicators) or os.getenv('TERM') == 'dumb'
    
    def print_step(self, step_num: int, total_steps: int, description: str):
        """
        Print step header with consistent formatting.
        
        Args:
            step_num: Current step number
            total_steps: Total number of steps
            description: Description of the step
        """
        self.console.print(f"\n[step]Step {step_num}/{total_steps}:[/] {description}")
    
    def print_status(self, message: str, style: str = "info"):
        """
        Print status message with appropriate styling.
        
        Args:
            message: Status message to display
            style: Rich style to apply (info, warning, error, success)
        """
        self.console.print(f"[{style}]{message}[/{style}]")
    
    def print_header(self, title: str, subtitle: str = None):
        """
        Print section header with consistent formatting.
        
        Args:
            title: Main title text
            subtitle: Optional subtitle text
        """
        from rich.panel import Panel
        
        content = f"[bold cyan]{title}[/]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/]"
        
        panel = Panel(
            content,
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def print_success(self, message: str):
        """Print success message with checkmark."""
        self.console.print(f"[success]✅ {message}[/]")
    
    def print_warning(self, message: str):
        """Print warning message with warning icon."""
        self.console.print(f"[warning]⚠️  {message}[/]")
    
    def print_error(self, message: str):
        """Print error message with error icon."""
        self.console.print(f"[error]❌ {message}[/]")
    
    def print_info(self, message: str):
        """Print info message with info icon."""
        self.console.print(f"[info]ℹ️  {message}[/]")


# Global console instance for consistency
_console_instance = None

def get_console(config: Optional[Config] = None) -> SBMConsole:
    """
    Get global console instance with optional configuration.
    
    Args:
        config: Optional Config object for theming
        
    Returns:
        Global SBMConsole instance
    """
    global _console_instance
    if _console_instance is None:
        _console_instance = SBMConsole(config)
    return _console_instance