#!/usr/bin/env python3
"""
Auto-SBM v2.0 - Main CLI Entry Point

This is the main command-line interface for the Auto-SBM tool.
Provides migration, validation, and utility commands with Rich UI.
"""

import sys
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add src to Python path for development
if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent.parent
    src_path = repo_root / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

from auto_sbm.config import AutoSBMSettings, get_settings

# Import feature modules with fallback for development
try:
    from auto_sbm.features.migration.cli import migration_commands
except ImportError:
    migration_commands = None

try:
    from auto_sbm.features.validation.cli import validation_commands
except ImportError:
    validation_commands = None

try:
    from auto_sbm.features.ui.console import console
except ImportError:
    # Fallback console if Rich isn't available
    from rich.console import Console
    console = Console()


@click.group()
@click.version_option(version="2.0.0", prog_name="Auto-SBM")
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug mode with verbose logging",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to custom configuration file",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, config_file: Optional[str]) -> None:
    """
    Auto-SBM v2.0 - Automated Site Builder Migration Tool
    
    A powerful tool for migrating DealerInspire themes with type safety,
    rich UI, and comprehensive validation.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Load configuration
    try:
        config = get_settings()
        ctx.obj["config"] = config
        ctx.obj["debug"] = debug
        
        if debug:
            console.print("[yellow]Debug mode enabled[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before migration",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Run validation after migration",
)
@click.option(
    "--branch",
    default=None,
    help="Target branch for migration (defaults to config)",
)
@click.pass_context
def migrate(
    ctx: click.Context,
    theme_name: str,
    backup: bool,
    validate: bool,
    branch: Optional[str],
) -> None:
    """Migrate a theme using the Auto-SBM migration pipeline."""
    try:
        from auto_sbm.features.migration.service import MigrationService
        
        config = ctx.obj["config"]
        debug = ctx.obj["debug"]
        
        service = MigrationService(config)
        
        console.print(Panel.fit(
            f"🚀 Starting migration for [bold cyan]{theme_name}[/bold cyan]",
            border_style="green"
        ))
        
        # Run migration
        result = service.migrate_theme(
            theme_name=theme_name,
            create_backup=backup,
            run_validation=validate,
            target_branch=branch,
            debug=debug,
        )
        
        if result.success:
            console.print(Panel.fit(
                f"✅ Migration completed successfully for [bold green]{theme_name}[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                f"❌ Migration failed for [bold red]{theme_name}[/bold red]\nError: {result.error}",
                border_style="red"
            ))
            sys.exit(1)
            
    except ImportError:
        console.print("[red]Migration feature not yet implemented. Coming in v2.1![/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Migration error: {e}[/red]")
        if ctx.obj["debug"]:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
@click.option(
    "--strict/--no-strict",
    default=False,
    help="Use strict validation mode",
)
@click.pass_context
def validate(
    ctx: click.Context,
    theme_name: str,
    strict: bool,
) -> None:
    """Validate a theme's SCSS and structure."""
    try:
        from auto_sbm.features.validation.service import ValidationService
        
        config = ctx.obj["config"]
        service = ValidationService(config)
        
        console.print(Panel.fit(
            f"🔍 Validating [bold cyan]{theme_name}[/bold cyan]",
            border_style="blue"
        ))
        
        result = service.validate_theme(theme_name, strict=strict)
        
        if result.is_valid:
            console.print(Panel.fit(
                f"✅ Validation passed for [bold green]{theme_name}[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                f"❌ Validation failed for [bold red]{theme_name}[/bold red]",
                border_style="red"
            ))
            for error in result.errors:
                console.print(f"  • {error}")
            sys.exit(1)
            
    except ImportError:
        console.print("[red]Validation feature not yet implemented. Coming in v2.1![/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        if ctx.obj["debug"]:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show Auto-SBM status and configuration."""
    config = ctx.obj["config"]
    
    # Create status display
    status_text = Text()
    status_text.append("Auto-SBM v2.0 Status\n\n", style="bold blue")
    status_text.append(f"GitHub Org: {config.git.github_org}\n")
    status_text.append(f"Themes Directory: {config.themes_directory}\n")
    status_text.append(f"Backup Directory: {config.backup_directory}\n")
    status_text.append(f"Rich UI: {'✅' if config.migration.rich_ui_enabled else '❌'}\n")
    status_text.append(f"Backups: {'✅' if config.migration.create_backups else '❌'}\n")
    status_text.append(f"Cleanup Snapshots: {'✅' if config.migration.cleanup_snapshots else '❌'}\n")
    
    console.print(Panel(status_text, title="Status", border_style="blue"))


@cli.command()
@click.option(
    "--clean/--no-clean",
    default=False,
    help="Clean generated files and caches",
)
def setup(clean: bool) -> None:
    """Run setup checks and environment validation."""
    if clean:
        console.print("[yellow]Cleaning generated files...[/yellow]")
        # Add cleanup logic here
        
    console.print("[green]Running setup verification...[/green]")
    
    # Run the verification script
    import subprocess
    result = subprocess.run([sys.executable, "verify-install.py"], capture_output=True, text=True)
    
    if result.returncode == 0:
        console.print("[green]✅ Setup verification passed![/green]")
    else:
        console.print("[red]❌ Setup verification failed![/red]")
        console.print(result.stdout)
        console.print(result.stderr)
        sys.exit(1)


# Add feature-specific command groups (these will be implemented in v2.1)
def add_feature_commands() -> None:
    """Add feature-specific command groups."""
    try:
        # Migration commands
        if migration_commands:
            cli.add_command(migration_commands, name="migration")
    except Exception:
        pass
        
    try:
        # Validation commands  
        if validation_commands:
            cli.add_command(validation_commands, name="validation")
    except Exception:
        pass


if __name__ == "__main__":
    add_feature_commands()
    cli()
