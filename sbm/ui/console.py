"""
Console management and theming for the SBM CLI tool.

This module provides centralized console management with Rich theming support,
ensuring consistent styling across all CLI components.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from sbm.config import Config
from sbm.ui.panels import StatusPanels


class SBMConsole:
    """
    Centralized console management for SBM CLI with theming support.

    This class provides a consistent interface for all Rich console operations
    throughout the SBM tool, with configuration-aware theming and fallback support.
    """

    def __init__(self, config: Config | None = None) -> None:
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
        self.total_steps = 0
        self.current_step = 0

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

    def set_total_steps(self, total: int) -> None:
        """Set the total number of steps for the current process."""
        self.total_steps = total
        self.current_step = 0

    def print_step(self, description: str, step_num: int | None = None) -> None:
        """
        Print step header with consistent formatting.

        Args:
            description: Description of the step
            step_num: Optional step number (auto-increments if not provided)
        """
        if step_num is not None:
            self.current_step = step_num
        else:
            self.current_step += 1

        total_str = f"/{self.total_steps}" if self.total_steps > 0 else ""
        self.console.print(f"\n[step]Step {self.current_step}{total_str}:[/] {description}")

    def print_status(self, message: str, style: str = "info") -> None:
        """
        Print status message with appropriate styling.

        Args:
            message: Status message to display
            style: Rich style to apply (info, warning, error, success)
        """
        self.console.print(f"[{style}]{message}[/{style}]")

    def status(self, message: str) -> Any:
        """
        Create a status context manager with a spinner.

        Args:
            message: Status message to display with the spinner
        """
        return self.console.status(f"[bold info]{message}[/]", spinner="dots")

    def print_header(self, title: str, subtitle: str | None = None) -> None:
        """
        Print section header with consistent formatting.

        Args:
            title: Main title text
            subtitle: Optional subtitle text
        """
        content = Text.from_markup(f"[bold cyan]{title}[/]")
        if subtitle:
            content.append("\n")
            content.append(subtitle, style="dim")

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
        self.console.print(f"[info]i {message}[/]")

    def print_migration_header(self, theme_name: str) -> None:
        """Print migration header with premium SBM branding."""
        metadata = Table.grid(padding=(0, 2))
        metadata.add_column(style="bold cyan")
        metadata.add_column()
        metadata.add_row("Theme:", f"[filename]{theme_name}[/]")
        metadata.add_row("System:", "[sbm.primary]Auto-SBM v2.0[/]")
        metadata.add_row("Mode:", "Full Automated Workflow")

        panel = Panel(
            metadata,
            title="[sbm.primary]SBM Migration Tool[/]",
            subtitle="[dim]Real-time progress tracking enabled[/dim]",
            border_style="bright_blue",
            padding=(1, 2),
        )
        self.console.print("\n")
        self.console.print(panel)

    def print_docker_status(self, message: str) -> None:
        """Print Docker-related status with Docker styling."""
        self.console.print(f"[sbm.docker]🐳 {message}[/]")

    def print_aws_status(self, message: str) -> None:
        """Print AWS-related status with AWS styling."""
        self.console.print(f"[sbm.aws]☁️  {message}[/]")

    def print_manual_review_prompt(self, theme_name: str, files: list[str]) -> None:
        """Print a premium manual review prompt using StatusPanels."""
        table = StatusPanels.create_file_review_table(theme_name, files)

        prompt_panel = Panel(
            table,
            title="[bold yellow]Manual Review Required[/bold yellow]",
            subtitle="[dim]Check the files above, then confirm to continue[/dim]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print("\n")
        self.console.print(prompt_panel)

    def print_migration_complete(
        self,
        theme_name: str,
        elapsed_time: float,
        files_processed: int = 0,
        warnings: int = 0,
        errors: int = 0,
        pr_url: str | None = None,
    ) -> None:
        """Print migration completion with premium styling and summary panel."""
        summary_panel = StatusPanels.create_completion_summary_panel(
            theme_name=theme_name,
            elapsed_time=elapsed_time,
            files_processed=files_processed,
            warnings=warnings,
            errors=errors,
            pr_url=pr_url,
        )
        self.console.print("\n")
        self.console.print(summary_panel)


# Global console instance for consistency
_console_instance: Optional[SBMConsole] = None


def get_console(config: Config | None = None) -> SBMConsole:
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
