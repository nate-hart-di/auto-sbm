"""
Simple Rich UI components without progress bars.
"""

from rich.console import Console
from rich.panel import Panel

# Global Rich console for step output
_console = Console()


def print_step(step_num: int, total_steps: int, description: str, _theme_name: str) -> None:
    """Print a beautiful step header without progress bars."""
    _console.print(f"\n🌟 [bold cyan]Step {step_num}/{total_steps}:[/] {description}")


def print_step_success(message: str) -> None:
    """Print step completion message."""
    _console.print(f"✅ [bold green]{message}[/]")


def print_step_warning(message: str) -> None:
    """Print step warning message."""
    _console.print(f"⚠️ [bold yellow]{message}[/]")


def print_step_error(message: str) -> None:
    """Print step error message."""
    _console.print(f"❌ [bold red]{message}[/]")


def print_migration_header(theme_name: str) -> None:
    """Print beautiful migration start header."""
    panel = Panel(
        f"[bold cyan]🚀 Site Builder Migration Starting[/]\n\n"
        f"[bold]Theme:[/] {theme_name}\n"
        f"[bold]Process:[/] 6-step automated migration\n"
        f"[dim]Rich UI enabled with step-by-step feedback[/]",
        title="[bold green]SBM Migration",
        border_style="cyan",
        padding=(1, 2),
    )
    _console.print(panel)


def print_migration_complete(theme_name: str) -> None:
    """Print beautiful migration completion message."""
    panel = Panel(
        f"[bold green]🎉 Migration Process Complete![/]\n\n"
        f"[bold]Theme:[/] {theme_name}\n"
        f"[bold]Status:[/] [green]All steps completed successfully[/]\n"
        f"[bold]Files:[/] Site Builder SCSS files ready for review\n"
        f"[bold]Next:[/] Manual review and Git operations",
        title="[bold green]✅ Success",
        border_style="green",
        padding=(1, 2),
    )
    _console.print(panel)
