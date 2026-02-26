"""
Simple Rich UI components without progress bars.
"""

from rich.console import Console
from rich.panel import Panel

# Global Rich console for step output
_console = Console()


def print_step(step_num: int, total_steps: int, description: str, theme_name: str) -> None:
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
        "[bold green]🎉 Migration Success![/]\n\n"
        "[bold]✅ Migration Completed:[/] All 6 steps finished successfully\n"
        "[bold]📁 Files Generated:[/] Site Builder SCSS files (sb-*.scss)\n"
        "[bold]🔧 Variables Converted:[/] SCSS variables → CSS custom properties\n"
        "[bold]🐳 Docker Environment:[/] Compilation verified successfully\n"
        "[bold]📋 Pull Request:[/] Created and ready for review",
        title="[bold green]✅ Migration Complete",
        border_style="green",
        padding=(1, 2),
    )
    _console.print(panel)
