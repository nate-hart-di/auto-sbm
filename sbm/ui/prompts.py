"""
Interactive prompts and confirmations for the SBM CLI tool.

This module provides Rich-enhanced interactive prompts with context panels,
improving user experience during manual review and decision points.
"""

import sys
import select
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from sbm.utils.path import get_dealer_theme_dir

from .console import get_console
from .panels import StatusPanels
from sbm.config import get_settings


class DuplicateAction(Enum):
    """Action to take when duplicates are detected."""
    SKIP = "skip"           # Skip duplicates, proceed with remaining
    REMIGRATE = "remigrate" # Remigrate duplicates, mark old runs as superseded
    CANCEL = "cancel"       # Cancel the entire operation


class InteractivePrompts:
    """
    Enhanced interactive prompts with Rich context panels.

    This class provides consistent, professional prompts throughout the SBM
    migration workflow with contextual information and visual enhancements.
    """

    @staticmethod
    def confirm_migration_start(theme_name: str, config: Dict[str, Any]) -> bool:
        """
        Enhanced confirmation prompt for migration start.

        Args:
            theme_name: Name of theme to migrate
            config: Migration configuration dictionary

        Returns:
            True if user confirms, False otherwise
        """
        if get_settings().non_interactive:
            return True

        console = get_console()

        # Consolidate configuration for the single panel
        config_info = {
            "Just Start": "Enabled" if not config.get("skip_just") else "Skipped",
            "Clean Reset": "Yes" if config.get("force_reset") else "No",
            "Create PR": "Yes" if config.get("create_pr") else "No",
        }

        # Show the single consolidated panel
        config_panel = StatusPanels.create_migration_status_panel(
            theme_name, "Initialization", "in_progress", config_info
        )
        console.console.print(config_panel)

        return Confirm.ask("[bold green]Start migration with these settings?[/]", default=True)

    @staticmethod
    def manual_review_interface(theme_name: str) -> bool:
        """
        Enhanced manual review interface with file browser.

        Args:
            theme_name: Name of theme being reviewed

        Returns:
            True if user wants to continue, False otherwise
        """
        console = get_console()

        # Create file review table
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
        file_table = StatusPanels.create_file_review_table(theme_name, sb_files)

        # Show review instructions panel
        theme_dir = get_dealer_theme_dir(theme_name)
        review_panel = Panel(
            Text.assemble(
                ("Manual Review Phase", "bold cyan"),
                "\n\n",
                ("Please review the migrated SCSS files for ", "white"),
                (theme_name, "bold filename"),
                (":\n", "white"),
                ("• Check variable transformations\n", "white"),
                ("• Verify mixin conversions\n", "white"),
                ("• Validate color functions\n", "white"),
                ("• Test responsive breakpoints\n", "white"),
                ("\n", "white"),
                ("Files are located in: ", "dim"),
                (theme_dir, "dim filename"),
            ),
            title="Review Instructions",
            border_style="yellow",
            padding=(1, 2),
        )

        console.console.print(review_panel)
        console.console.print(file_table)

        return Confirm.ask("\n[bold cyan]Continue after manual review?[/]", default=True)

    @staticmethod
    def git_operation_prompts(theme_name: str, branch_name: str) -> Dict[str, bool]:
        """
        Enhanced Git operation prompts with change preview.

        Args:
            theme_name: Name of theme
            branch_name: Current Git branch name

        Returns:
            Dictionary with user choices for Git operations
        """
        if get_settings().non_interactive:
            return {"commit": True, "push": True, "create_pr": True}

        console = get_console()

        # Show branch information
        branch_panel = Panel(
            Text.assemble(
                ("Theme: ", "bold cyan"),
                (theme_name, "filename"),
                "\n",
                ("Branch: ", "bold green"),
                (branch_name, "branch"),
                "\n",
                ("Status: ", "bold yellow"),
                ("Ready to commit changes", "white"),
            ),
            title="Git Operations",
            border_style="green",
            padding=(1, 2),
        )
        console.console.print(branch_panel)

        # Prompt for each operation
        commit = Confirm.ask("[bold green]Commit all changes?[/]", default=True)

        push = False
        create_pr = False

        if commit:
            push = Confirm.ask(f"[bold blue]Push to origin/{branch_name}?[/]", default=True)

            if push:
                create_pr = Confirm.ask("[bold cyan]Create pull request?[/]", default=True)

        return {"commit": commit, "push": push, "create_pr": create_pr}

    @staticmethod
    def error_recovery_prompt(error_info: Dict[str, Any]) -> str:
        """
        Enhanced error recovery prompt with options.

        Args:
            error_info: Dictionary containing error details

        Returns:
            User's choice for error recovery
        """
        if get_settings().non_interactive:
            # Default to original prompt default which is usually "retry" or "skip" depending on context
            # But let's look at the actual prompt content if possible
            return "retry"

        console = get_console()

        # Show error details
        error_panel = StatusPanels.create_error_panel(
            error_info.get("type", "Unknown"),
            error_info.get("file", "Unknown"),
            error_info.get("line", 0),
            error_info.get("message", "No details available"),
            error_info.get("code_snippet"),
            error_info.get("suggested_fix"),
        )
        console.console.print(error_panel)

        # Recovery options with descriptions
        options_panel = Panel(
            Text.assemble(
                ("Recovery Options:\n\n", "bold yellow"),
                ("auto", "bold cyan"),
                ("   - Attempt automatic fix\n", "white"),
                ("manual", "bold cyan"),
                (" - Open file for manual editing\n", "white"),
                ("skip", "bold cyan"),
                ("   - Skip this error and continue\n", "white"),
                ("abort", "bold cyan"),
                ("  - Stop migration process\n", "white"),
            ),
            title="Available Actions",
            border_style="yellow",
            padding=(1, 2),
        )
        console.console.print(options_panel)

        return Prompt.ask(
            "[bold yellow]Choose recovery option[/]",
            choices=["auto", "manual", "skip", "abort"],
            default="auto",
        )

    @staticmethod
    def docker_startup_prompt(container_name: str, status: str) -> bool:
        """
        Prompt for Docker container startup with status display.

        Args:
            container_name: Name of Docker container
            status: Current container status

        Returns:
            True if user wants to continue, False otherwise
        """
        console = get_console()

        status_icons = {"running": "🟢", "stopped": "🔴", "starting": "🟡", "error": "❌"}

        docker_panel = Panel(
            Text.assemble(
                ("Docker Container Status\n\n", "bold docker"),
                ("Container: ", "bold"),
                (container_name, "filename"),
                "\n",
                ("Status: ", "bold"),
                (f"{status_icons.get(status, '❓')} {status.title()}", "white"),
                "\n\n",
                ("The Docker environment is required for SCSS compilation testing.", "dim"),
            ),
            title="Docker Environment",
            border_style="blue",
            padding=(1, 2),
        )
        console.console.print(docker_panel)

        if status == "running":
            return True
        if status == "starting":
            return Confirm.ask(
                "[bold blue]Container is starting. Continue waiting?[/]", default=True
            )
        return Confirm.ask(
            f"[bold yellow]Container is {status}. Continue anyway?[/]", default=False
        )

    @staticmethod
    def select_theme_variant(theme_name: str, variants: List[str]) -> Optional[str]:
        """
        Prompt user to select theme variant if multiple are available.

        Args:
            theme_name: Base theme name
            variants: List of available variants

        Returns:
            Selected variant or None if cancelled
        """
        if get_settings().non_interactive:
            return variants[0] if variants else None

        if not variants:
            return None

        if len(variants) == 1:
            return variants[0]

        console = get_console()

        # Create variants table
        table = Table(title=f"Available Variants for {theme_name}")
        table.add_column("Option", style="cyan", width=10)
        table.add_column("Variant", style="filename", width=40)
        table.add_column("Description", style="white", width=30)

        for i, variant in enumerate(variants, 1):
            # Generate description based on variant name
            if "mobile" in variant.lower():
                desc = "Mobile-optimized version"
            elif "tablet" in variant.lower():
                desc = "Tablet-optimized version"
            elif "desktop" in variant.lower():
                desc = "Desktop-optimized version"
            else:
                desc = "Standard variant"

            table.add_row(str(i), variant, desc)

        console.console.print(table)

        try:
            choice = IntPrompt.ask(
                f"[bold cyan]Select variant (1-{len(variants)}) or 0 to cancel[/]", default=1
            )

            if choice == 0:
                return None
            if 1 <= choice <= len(variants):
                return variants[choice - 1]
            console.print_warning(f"Invalid choice: {choice}")
            return None

        except KeyboardInterrupt:
            console.print_info("Selection cancelled by user")
            return None

    @staticmethod
    def compilation_retry_prompt(attempt: int, max_attempts: int, error_count: int) -> bool:
        """
        Prompt for compilation retry after errors.

        Args:
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            error_count: Number of errors found

        Returns:
            True if user wants to retry, False otherwise
        """
        if get_settings().non_interactive:
            return True

        console = get_console()

        retry_panel = Panel(
            Text.assemble(
                ("Compilation Attempt ", "bold yellow"),
                (f"{attempt}/{max_attempts}", "bold white"),
                ("\n\n", "white"),
                ("Errors found: ", "bold red"),
                (str(error_count), "red"),
                ("\n\n", "white"),
                ("Options:\n", "bold"),
                ("• Continue - Attempt automatic fixes\n", "white"),
                ("• Skip - Proceed with warnings\n", "white"),
                ("• Abort - Stop migration\n", "white"),
            ),
            title="Compilation Errors",
            border_style="yellow",
            padding=(1, 2),
        )
        console.console.print(retry_panel)

        if attempt >= max_attempts:
            return Confirm.ask(
                "[bold red]Maximum attempts reached. Proceed anyway?[/]", default=False
            )
        return Confirm.ask(
            f"[bold yellow]Retry compilation? ({max_attempts - attempt} attempts remaining)[/]",
            default=True,
        )

    @staticmethod
    def pr_configuration_prompt(theme_name: str, branch_name: str) -> Dict[str, Any]:
        """
        Prompt for pull request configuration options.

        Args:
            theme_name: Name of theme
            branch_name: Git branch name

        Returns:
            Dictionary with PR configuration
        """
        if get_settings().non_interactive:
            return {
                "title": f"SBM: Migrate {theme_name} to Site Builder format",
                "draft": False,
                "add_reviewers": True,
                "reviewers": ["carsdotcom/fe-dev-sbm"],
                "labels": ["fe-dev"],
            }

        console = get_console()

        pr_panel = Panel(
            Text.assemble(
                ("Pull Request Configuration\n\n", "bold cyan"),
                ("Theme: ", "bold"),
                (theme_name, "filename"),
                "\n",
                ("Branch: ", "bold"),
                (branch_name, "branch"),
                "\n\n",
                ("Configure your pull request options below.", "dim"),
            ),
            title="GitHub Integration",
            border_style="green",
            padding=(1, 2),
        )
        console.console.print(pr_panel)

        # Get PR configuration
        title = Prompt.ask(
            "[bold green]PR Title[/]", default=f"SBM: Migrate {theme_name} to Site Builder format"
        )

        draft = Confirm.ask("[bold blue]Create as draft PR?[/]", default=False)

        add_reviewers = Confirm.ask(
            "[bold cyan]Add default reviewers (carsdotcom/fe-dev-sbm)?[/]", default=True
        )

        return {
            "title": title,
            "draft": draft,
            "add_reviewers": add_reviewers,
            "reviewers": ["carsdotcom/fe-dev-sbm"] if add_reviewers else [],
            "labels": ["fe-dev"],
        }

    @staticmethod
    def confirm_retry_with_timeout(
        failed_slugs_count: int, source_file: str, timeout: int = 30
    ) -> bool:
        """
        Prompt user for rerun with a timeout.

        Args:
            failed_slugs_count: Number of slugs that failed
            source_file: Path to the file that was updated
            timeout: Seconds to wait before defaulting to No

        Returns:
            True if user confirms, False otherwise
        """
        if get_settings().non_interactive:
            return False

        console = get_console()

        retry_panel = Panel(
            Text.assemble(
                ("Batch Completed with Failures\n\n", "bold red"),
                ("Failed Migrations: ", "bold"),
                (str(failed_slugs_count), "red"),
                ("\n", "white"),
                ("Retry File Updated: ", "bold"),
                (source_file, "filename"),
                ("\n\n", "white"),
                (
                    f"The source file has been updated with failed slugs. Would you like to rerun the migration for these {failed_slugs_count} slugs now?",
                    "white",
                ),
                ("\n\n", "white"),
                (f"Defaulting to 'No' in {timeout} seconds if no input received.", "dim"),
            ),
            title="Automated Retry",
            border_style="red",
            padding=(1, 2),
        )
        console.console.print(retry_panel)

        console.console.print("\n[bold green]Rerun failed migrations? (y/n) [default: n]: [/bold green]", end="")
        sys.stdout.flush()

        # Simple timed input using select
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                response = sys.stdin.readline().strip().lower()
                return response in ["y", "yes"]
            else:
                console.console.print("\n[yellow]Prompt timed out. Defaulting to No.[/]")
                return False
        except Exception as e:
            console.console.print(f"\n[red]Error during timed prompt: {e}[/]")
            return False

    @staticmethod
    def confirm_duplicate_migration(duplicates: List[tuple], default: str = "skip") -> DuplicateAction:
        """
        Prompt user to decide what to do with duplicate migrations.

        Args:
            duplicates: List of (slug, user) tuples.
            default: Default choice ("skip", "remigrate", or "cancel").

        Returns:
            DuplicateAction indicating the user's choice.
        """
        if get_settings().non_interactive:
            return DuplicateAction.SKIP

        sbm_console = get_console()
        console = sbm_console.console  # Get the actual Rich Console
        console.print("\n[bold cyan]What would you like to do with these duplicates?[/bold cyan]")
        console.print("  [yellow]1[/yellow] - Skip duplicates (proceed with remaining sites)")
        console.print("  [green]2[/green] - Remigrate (mark old PRs as superseded, create new ones)")
        console.print("  [red]3[/red] - Cancel (abort the entire operation)")

        choice = Prompt.ask(
            "\nYour choice",
            choices=["1", "2", "3"],
            default="1" if default == "skip" else ("2" if default == "remigrate" else "3")
        )

        if choice == "1":
            return DuplicateAction.SKIP
        elif choice == "2":
            return DuplicateAction.REMIGRATE
        else:
            return DuplicateAction.CANCEL
