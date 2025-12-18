"""
Status panels and displays for the SBM CLI tool.

This module provides Rich-enhanced status panels for different migration phases,
including error displays, Docker status, and file review interfaces.
"""

import os
from typing import Any, Dict, List, Optional

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from sbm.utils.path import get_dealer_theme_dir


class StatusPanels:
    """
    Rich status panels for different migration phases.

    This class provides static methods for creating consistent status displays
    throughout the SBM migration workflow.
    """

    @staticmethod
    def create_migration_status_panel(
        theme_name: str, step: str, status: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> Panel:
        """
        Create migration status panel with theme information.

        Args:
            theme_name: Name of the theme being migrated
            step: Current migration step
            status: Current status (success, warning, error, in_progress, pending)
            additional_info: Optional dictionary of additional information

        Returns:
            Rich Panel object for display
        """
        status_icons = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "in_progress": "⏳",
            "pending": "⏸️",
            "running": "🔄",
        }

        # Truncate long theme names for display
        display_theme = theme_name if len(theme_name) <= 40 else f"{theme_name[:37]}..."

        content = Text()
        # Use consistent padding for labels as requested in screenshot
        content.append("Theme", style="bold cyan")
        content.append(f"{' ':13}: ", style="bold")
        content.append(f"{display_theme}\n", style="filename")

        content.append("Current Step", style="bold green")
        content.append(f"{' ':6}: ", style="bold")
        content.append(f"{step}\n", style="white")

        content.append("Status", style="bold yellow")
        content.append(f"{' ':12}: ", style="bold")
        content.append(f"{status_icons.get(status, '❓')} {status.title()}", style="white")

        if additional_info:
            content.append("\n\n")
            for key, value in additional_info.items():
                label = key
                # Calculate padding for alignment (assuming max label width around 18)
                padding = " " * (18 - len(label))
                content.append(f"{label}", style="bold")
                content.append(f"{padding}: ", style="bold")

                # Special styling for values
                style = "white"
                if str(value).lower() in ["yes", "enabled", "success"]:
                    style = "green"
                elif str(value).lower() in ["no", "skipped", "error"]:
                    style = "yellow"

                content.append(f"{value}\n", style=style)

        return Panel(
            content, title="Auto-SBM Config", border_style="cyan", width=80, padding=(1, 2)
        )

    @staticmethod
    def create_docker_status_panel(
        container_name: str, logs: List[str], status: str = "running"
    ) -> Panel:
        """
        Create Docker container status panel.

        Args:
            container_name: Name of the Docker container
            logs: List of recent log lines
            status: Container status

        Returns:
            Rich Panel object for display
        """
        # Create status header
        status_icons = {"running": "🟢", "stopped": "🔴", "starting": "🟡", "error": "❌"}

        header = Text()
        header.append("Container: ", style="bold docker")
        header.append(container_name, style="filename")
        header.append(f" {status_icons.get(status, '❓')} {status.title()}", style="docker")

        # Create logs table
        table = Table(show_header=True, header_style="bold docker")
        table.add_column("Time", style="dim", width=12)
        table.add_column("Message", style="white")

        # Process and display recent logs
        recent_logs = logs[-8:] if len(logs) > 8 else logs
        for log_line in recent_logs:
            # Parse timestamp and message from log line
            parts = log_line.strip().split(" ", 2)
            if len(parts) >= 3:
                timestamp = f"{parts[0]} {parts[1]}"
                message = parts[2]
            else:
                timestamp = "N/A"
                message = log_line.strip()

            # Style message based on content
            if "error" in message.lower():
                message = f"[red]{message}[/]"
            elif "warning" in message.lower():
                message = f"[yellow]{message}[/]"
            elif "success" in message.lower() or "complete" in message.lower():
                message = f"[green]{message}[/]"

            table.add_row(timestamp[-12:], message)

        # Combine header and table
        content = Text()
        content.append_text(header)
        content.append("\n\n")

        return Panel(
            content, title="Docker Container Status", border_style="blue", width=120, padding=(1, 2)
        )

    @staticmethod
    def create_error_panel(
        error_type: str,
        file_path: str,
        line_number: int,
        message: str,
        code_snippet: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ) -> Panel:
        """
        Create error display panel with context.

        Args:
            error_type: Type of error (e.g., "Syntax Error", "Compilation Error")
            file_path: Path to the file with the error
            line_number: Line number where error occurred
            message: Error message
            code_snippet: Optional code snippet showing the error
            suggested_fix: Optional suggested fix

        Returns:
            Rich Panel object for display
        """
        content = Text()
        content.append("Error Type: ", style="bold red")
        content.append(f"{error_type}\n", style="red")
        content.append("File: ", style="bold")
        content.append(f"{file_path}\n", style="filename")
        content.append("Line: ", style="bold")
        content.append(f"{line_number}\n", style="white")
        content.append("Message: ", style="bold")
        content.append(f"{message}", style="white")

        if code_snippet:
            content.append("\n\nCode Context:\n", style="bold")
            # Add syntax highlighting for SCSS
            try:
                syntax = Syntax(
                    code_snippet,
                    "scss",
                    line_numbers=True,
                    start_line=max(1, line_number - 3),
                    highlight_lines={line_number},
                )
                content.append(syntax)
            except Exception:
                # Fallback to plain text if syntax highlighting fails
                content.append(code_snippet, style="dim")

        if suggested_fix:
            content.append("\n\nSuggested Fix:\n", style="bold green")
            content.append(suggested_fix, style="green")

        return Panel(
            content, title="Compilation Error", border_style="red", width=100, padding=(1, 2)
        )

    @staticmethod
    def create_file_review_table(theme_name: str, files: List[str]) -> Table:
        """
        Create file review table for manual review phase.

        Args:
            theme_name: Name of theme being reviewed
            files: List of file names to review

        Returns:
            Rich Table object for display
        """
        table = Table(title=f"Files to Review - {theme_name}")
        table.add_column("File", style="filename", width=30)
        table.add_column("Status", style="green", width=15)
        table.add_column("Lines", style="white", width=10)
        table.add_column("Size", style="dim", width=12)
        table.add_column("Modified", style="dim", width=20)

        theme_dir = get_dealer_theme_dir(theme_name)

        for file_name in files:
            file_path = os.path.join(theme_dir, file_name)

            if os.path.exists(file_path):
                try:
                    # Get file statistics
                    with open(file_path, encoding="utf-8") as f:
                        lines = len(f.readlines())

                    stat = os.stat(file_path)
                    size = stat.st_size

                    # Format size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"

                    # Format modification time
                    from datetime import datetime

                    mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                    # Determine status
                    if lines > 0:
                        status = "✅ Ready"
                        status_style = "green"
                    else:
                        status = "⚠️ Empty"
                        status_style = "yellow"

                    table.add_row(
                        file_name, f"[{status_style}]{status}[/]", str(lines), size_str, mod_time
                    )

                except Exception as e:
                    table.add_row(
                        file_name, "[red]❌ Error[/]", "N/A", "N/A", f"Error: {str(e)[:20]}..."
                    )
            else:
                table.add_row(file_name, "[red]❌ Missing[/]", "0", "0 B", "N/A")

        return table

    @staticmethod
    def create_git_status_panel(
        theme_name: str,
        branch_name: str,
        files_changed: List[str],
        commit_message: Optional[str] = None,
    ) -> Panel:
        """
        Create Git status panel for repository operations.

        Args:
            theme_name: Name of theme
            branch_name: Current Git branch
            files_changed: List of files that have been modified
            commit_message: Optional commit message preview

        Returns:
            Rich Panel object for display
        """
        content = Text()
        content.append("Theme: ", style="bold cyan")
        content.append(f"{theme_name}\n", style="filename")
        content.append("Branch: ", style="bold git")
        content.append(f"{branch_name}\n", style="branch")

        if files_changed:
            content.append("Files Changed:\n", style="bold")
            for file_path in files_changed:
                content.append(f"  • {file_path}\n", style="filename")

        if commit_message:
            content.append("\nCommit Message:\n", style="bold")
            content.append(f"{commit_message}", style="dim")

        return Panel(
            content, title="Git Operations", border_style="green", width=80, padding=(1, 2)
        )

    @staticmethod
    def create_completion_summary_panel(
        theme_name: str,
        elapsed_time: float,
        files_processed: int,
        warnings: int = 0,
        errors: int = 0,
        pr_url: Optional[str] = None,
    ) -> Panel:
        """
        Create migration completion summary panel.

        Args:
            theme_name: Name of migrated theme
            elapsed_time: Total elapsed time in seconds
            files_processed: Number of files processed
            warnings: Number of warnings encountered
            errors: Number of errors encountered
            pr_url: Optional pull request URL

        Returns:
            Rich Panel object for display
        """
        content = Text()
        content.append("Migration Complete! ", style="bold success")
        content.append("🎉\n\n", style="success")

        content.append("Theme: ", style="bold cyan")
        content.append(f"{theme_name}\n", style="filename")

        # Format elapsed time
        if elapsed_time < 60:
            time_str = f"{elapsed_time:.1f}s"
        elif elapsed_time < 3600:
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            time_str = f"{minutes}m {seconds}s"
        else:
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            time_str = f"{hours}h {minutes}m"

        content.append("Duration: ", style="bold")
        content.append(f"{time_str}\n", style="white")

        content.append("Files Processed: ", style="bold")
        content.append(f"{files_processed}\n", style="white")

        if warnings > 0:
            content.append("Warnings: ", style="bold yellow")
            content.append(f"{warnings}\n", style="yellow")

        if errors > 0:
            content.append("Errors: ", style="bold red")
            content.append(f"{errors}\n", style="red")

        if pr_url:
            content.append("\nPull Request: ", style="bold green")
            content.append(f"{pr_url}", style="blue underline")

        from sbm.utils.tracker import get_migration_stats

        global_stats = get_migration_stats().get("global_metrics", {})
        if global_stats:
            team_saved = global_stats.get("total_time_saved_h", 0)
            content.append("\n\nTeam Impact: ", style="bold cyan")
            content.append(f"{team_saved}h saved total", style="sbm.primary")

        return Panel(
            content, title="Migration Summary", border_style="green", width=80, padding=(1, 2)
        )
