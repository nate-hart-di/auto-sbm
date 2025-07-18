"""Rich console singleton for Auto-SBM v2.0."""

from rich.console import Console

# Global console instance for consistent Rich UI
console = Console(force_terminal=True, no_color=False)
