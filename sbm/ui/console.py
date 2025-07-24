"""
Console management and theming for the SBM CLI tool.

This module provides centralized console management with Rich theming support,
ensuring consistent styling across all CLI components.
"""

import os
from typing import Optional

from rich.console import Console
from rich.theme import Theme

from sbm.config import Config


class SBMConsole:
    """
    Centralized console management for SBM CLI with theming support.

    This class provides a consistent interface for all Rich console operations
    throughout the SBM tool, with configuration-aware theming and fallback support.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
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
            legacy_windows=False,
        )

    def _create_theme(self) -> Theme:
        """
        Create SBM-specific theme with colorblind-friendly patterns.

        Returns:
            Rich Theme object with SBM color scheme
        """
        theme_name = self.config.get_setting("ui", {}).get("theme", "default")

        if theme_name == "high-contrast":
            return Theme(
                {
                    "info": "bright_cyan",
                    "warning": "bright_yellow on black",
                    "error": "bright_red on black",
                    "success": "bright_green on black",
                    "progress": "bright_blue",
                    "step": "bright_cyan bold",
                    "filename": "bright_white bold",
                    "branch": "bright_magenta",
                    "docker": "bright_blue",
                    "aws": "bright_magenta",
                    "git": "bright_green",
                    "sbm.primary": "bright_cyan bold",
                    "sbm.success": "bright_green",
                    "sbm.docker": "bright_blue",
                    "sbm.aws": "bright_magenta",
                }
            )
        # default theme with auto-sbm branding
        return Theme(
            {
                "info": "cyan",
                "warning": "#FFA500",  # Orange for better visibility
                "error": "bold red",
                "success": "bold green",
                "progress": "#0066CC",  # Auto-SBM primary blue
                "step": "bold #0066CC",  # Auto-SBM blue
                "filename": "bold white",
                "branch": "#9A4FE7",  # Purple for Git branches
                "docker": "#0db7ed",  # Docker blue
                "aws": "#FF9900",  # AWS orange
                "git": "#00AA44",  # Git green
                # Auto-SBM specific styles
                "sbm.primary": "bold #0066CC",
                "sbm.success": "bold #00AA44",
                "sbm.warning": "bold #FFA500",
                "sbm.error": "bold #DC143C",
                "sbm.docker": "#0db7ed",
                "sbm.aws": "#FF9900",
                "sbm.progress": "#0066CC",
                "sbm.migration": "bold #0066CC",
                "sbm.step": "bold cyan",
            }
        )

    def _is_ci_environment(self) -> bool:
        """
        Check if running in CI/CD environment.

        Returns:
            True if in CI environment, False otherwise
        """
        ci_indicators = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "GITHUB_ACTIONS",
            "TRAVIS",
            "CIRCLECI",
            "JENKINS_URL",
            "GITLAB_CI",
        ]

        return any(os.getenv(var) for var in ci_indicators) or os.getenv("TERM") == "dumb"

    def print_step(self, step_num: int, total_steps: int, description: str) -> None:
        """
        Print step header with consistent formatting.

        Args:
            step_num: Current step number
            total_steps: Total number of steps
            description: Description of the step
        """
        self.console.print(f"\n[step]Step {step_num}/{total_steps}:[/] {description}")

    def print_status(self, message: str, style: str = "info") -> None:
        """
        Print status message with appropriate styling.

        Args:
            message: Status message to display
            style: Rich style to apply (info, warning, error, success)
        """
        self.console.print(f"[{style}]{message}[/{style}]")

    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
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

        panel = Panel(content, border_style="cyan", padding=(1, 2))
        self.console.print(panel)

    def print_success(self, message: str) -> None:
        """Print success message with checkmark."""
        self.console.print(f"[success]✅ {message}[/]")

    def print_warning(self, message: str) -> None:
        """Print warning message with warning icon."""
        self.console.print(f"[warning]⚠️  {message}[/]")

    def print_error(self, message: str) -> None:
        """Print error message with error icon."""
        self.console.print(f"[error]❌ {message}[/]")

    def print_info(self, message: str) -> None:
        """Print info message with info icon."""
        self.console.print(f"[info]ℹ️  {message}[/]")

    def print_migration_header(self, theme_name: str) -> None:
        """Print migration header with SBM branding."""
        from rich.panel import Panel

        content = "[sbm.primary]🚀 Site Builder Migration[/]\n\n"
        content += f"[bold]Theme:[/] [sbm.migration]{theme_name}[/]\n"
        content += "[bold]Process:[/] 6-step automated migration\n"
        content += "[dim]Enhanced progress tracking with real-time Docker monitoring[/]"

        panel = Panel(
            content, title="[sbm.primary]SBM Migration Tool[/]", border_style="blue", padding=(1, 2)
        )
        self.console.print(panel)

    def print_docker_status(self, message: str) -> None:
        """Print Docker-related status with Docker styling."""
        self.console.print(f"[sbm.docker]🐳 {message}[/]")

    def print_aws_status(self, message: str) -> None:
        """Print AWS-related status with AWS styling."""
        self.console.print(f"[sbm.aws]☁️  {message}[/]")

    def print_migration_complete(self, theme_name: str, elapsed_time: float, timing_summary: Optional[dict] = None) -> None:
        """
        Print migration completion with enhanced styling and timing details.

        Args:
            theme_name: Name of the migrated theme
            elapsed_time: Total elapsed time
            timing_summary: Optional detailed timing breakdown from MigrationProgress
        """
        from rich.panel import Panel

        content = "[sbm.success]🎉 Migration Complete![/]\n\n"
        content += f"[bold]Theme:[/] [sbm.migration]{theme_name}[/]\n"
        content += "[bold]Status:[/] [sbm.success]All steps completed successfully[/]\n"

        # Enhanced timing display
        if elapsed_time < 60:
            time_display = f"{elapsed_time:.1f}s"
        elif elapsed_time < 3600:
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            time_display = f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            seconds = elapsed_time % 60
            time_display = f"{hours}h {minutes}m {seconds:.1f}s"

        content += f"[bold]Total Time:[/] [sbm.info]{time_display}[/]\n"

        # Add step timing breakdown if available
        if timing_summary and "steps" in timing_summary and timing_summary["steps"]:
            content += "\n[bold]Step Breakdown:[/]\n"
            for step_name, step_time in timing_summary["steps"].items():
                if step_time > 0:
                    if step_time < 60:
                        step_display = f"{step_time:.1f}s"
                    else:
                        step_mins = int(step_time // 60)
                        step_secs = step_time % 60
                        step_display = f"{step_mins}m {step_secs:.1f}s"
                    content += f"  • {step_name}: [sbm.info]{step_display}[/]\n"

        content += "\n[bold]Next:[/] Review changes and create pull request"

        panel = Panel(
            content,
            title="[sbm.success]✅ Migration Success[/]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)


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
