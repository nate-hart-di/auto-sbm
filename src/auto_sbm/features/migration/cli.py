"""Migration CLI commands for the migration feature slice"""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ...config import get_settings
from ...models.migration import MigrationConfig, MigrationStep, MigrationMode, MigrationPriority
from ...models.theme import Theme, ThemeType
from .service import MigrationService


console = Console()


@click.group()
def migration():
    """Migration-related commands for theme transformation"""
    pass


@migration.command()
@click.argument('theme_name')
@click.option('--mode', 
              type=click.Choice(['full', 'dry_run', 'incremental']), 
              default='full',
              help='Migration mode')
@click.option('--priority', 
              type=click.Choice(['low', 'normal', 'high', 'urgent']), 
              default='normal',
              help='Migration priority')
@click.option('--skip-git', is_flag=True, help='Skip Git operations')
@click.option('--skip-docker', is_flag=True, help='Skip Docker startup')
@click.option('--skip-maps', is_flag=True, help='Skip map components migration')
@click.option('--force-reset', is_flag=True, help='Reset existing Site Builder files')
@click.option('--no-ui', is_flag=True, help='Disable Rich UI progress tracking')
@click.option('--steps', 
              help='Comma-separated list of steps to execute',
              default=None)
def migrate(
    theme_name: str,
    mode: str,
    priority: str,
    skip_git: bool,
    skip_docker: bool,
    skip_maps: bool,
    force_reset: bool,
    no_ui: bool,
    steps: Optional[str]
):
    """Migrate a theme to Site Builder format with comprehensive tracking"""
    
    # Run async migration
    asyncio.run(_async_migrate(
        theme_name=theme_name,
        mode=mode,
        priority=priority,
        skip_git=skip_git,
        skip_docker=skip_docker,
        skip_maps=skip_maps,
        force_reset=force_reset,
        no_ui=no_ui,
        steps=steps
    ))


async def _async_migrate(
    theme_name: str,
    mode: str,
    priority: str,
    skip_git: bool,
    skip_docker: bool,
    skip_maps: bool,
    force_reset: bool,
    no_ui: bool,
    steps: Optional[str]
):
    """Async migration implementation with Rich UI"""
    
    try:
        # Load settings
        settings = get_settings()
        
        # Determine theme directory
        theme_dir = settings.themes_directory / theme_name
        if not theme_dir.exists():
            console.print(f"[red]Error: Theme directory not found: {theme_dir}[/red]")
            raise click.Abort()
        
        # Create theme model
        theme = Theme(
            name=theme_name,
            type=ThemeType.LEGACY,
            source_path=theme_dir
        )
        
        # Parse enabled steps
        enabled_steps = _parse_enabled_steps(steps, skip_git, skip_docker, skip_maps)
        
        # Create migration configuration
        migration_config = MigrationConfig(
            theme=theme,
            mode=getattr(MigrationMode, mode.upper()),
            priority=getattr(MigrationPriority, priority.upper()),
            git_operations_enabled=not skip_git,
            rich_ui_enabled=not no_ui,
            preserve_original=not force_reset,
            enabled_steps=enabled_steps
        )
        
        # Initialize migration service
        migration_service = MigrationService(settings)
        
        # Setup progress tracking
        if not no_ui:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=False
            ) as progress:
                
                # Create progress tasks for each step
                step_tasks = {}
                for step in enabled_steps:
                    task_id = progress.add_task(
                        f"[blue]{step.value.replace('_', ' ').title()}[/blue]",
                        total=100
                    )
                    step_tasks[step] = task_id
                
                def progress_callback(step: MigrationStep, percentage: int, message: str):
                    """Update progress bar"""
                    if step in step_tasks:
                        task_id = step_tasks[step]
                        if percentage >= 0:
                            progress.update(task_id, completed=percentage, description=f"[blue]{step.value.replace('_', ' ').title()}[/blue]: {message}")
                        else:
                            # Error indicated by negative percentage
                            progress.update(task_id, description=f"[red]{step.value.replace('_', ' ').title()}[/red]: {message}")
                
                # Execute migration with progress tracking
                console.print(f"\n[bold blue]Starting migration for theme: {theme_name}[/bold blue]")
                console.print(f"Mode: {mode}, Priority: {priority}")
                console.print(f"Steps: {len(enabled_steps)}")
                
                result = await migration_service.migrate_theme(
                    migration_config,
                    progress_callback=progress_callback
                )
        else:
            # Simple progress output for CI/non-interactive environments
            def simple_progress_callback(step: MigrationStep, percentage: int, message: str):
                if percentage == 0:
                    console.print(f"Starting: {step.value.replace('_', ' ').title()}")
                elif percentage == 100:
                    console.print(f"✅ Completed: {step.value.replace('_', ' ').title()}")
                elif percentage < 0:
                    console.print(f"❌ Failed: {step.value.replace('_', ' ').title()} - {message}")
            
            console.print(f"Starting migration for theme: {theme_name}")
            result = await migration_service.migrate_theme(
                migration_config,
                progress_callback=simple_progress_callback
            )
        
        # Display results
        _display_migration_results(result, no_ui)
        
        if not result.success:
            raise click.Abort()
            
    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        raise click.Abort()


@migration.command()
@click.argument('theme_name')
def test_compilation(theme_name: str):
    """Test SCSS compilation for a theme without modifying files"""
    
    try:
        settings = get_settings()
        migration_service = MigrationService(settings)
        
        console.print(f"[blue]Testing SCSS compilation for: {theme_name}[/blue]")
        
        # Run compilation test
        result = asyncio.run(migration_service._test_scss_compilation(theme_name, None))
        
        if result.success:
            console.print(f"[green]✅ Compilation test passed for {theme_name}[/green]")
            console.print(f"Files tested: {', '.join(result.files_tested)}")
        else:
            console.print(f"[red]❌ Compilation test failed for {theme_name}[/red]")
            for error in result.compilation_errors:
                console.print(f"  [red]Error: {error}[/red]")
        
    except Exception as e:
        console.print(f"[red]Compilation test failed: {e}[/red]")
        raise click.Abort()


@migration.command()
@click.argument('theme_name')
def create_snapshot(theme_name: str):
    """Create automation snapshots for a theme"""
    
    try:
        settings = get_settings()
        migration_service = MigrationService(settings)
        
        console.print(f"[blue]Creating snapshots for: {theme_name}[/blue]")
        
        snapshot_info = migration_service.create_snapshot(theme_name)
        
        console.print(f"[green]✅ Snapshots created[/green]")
        console.print(f"Directory: {snapshot_info.snapshot_directory}")
        console.print(f"Files: {', '.join(snapshot_info.files_snapshotted)}")
        
    except Exception as e:
        console.print(f"[red]Snapshot creation failed: {e}[/red]")
        raise click.Abort()


@migration.command()
def list_steps():
    """List all available migration steps"""
    
    console.print("[bold blue]Available Migration Steps:[/bold blue]\n")
    
    for step in MigrationStep:
        console.print(f"  [cyan]{step.value}[/cyan] - {step.value.replace('_', ' ').title()}")


def _parse_enabled_steps(
    steps: Optional[str],
    skip_git: bool,
    skip_docker: bool,
    skip_maps: bool
) -> list[MigrationStep]:
    """Parse enabled steps from CLI options"""
    
    if steps:
        # Parse comma-separated step names
        step_names = [s.strip().upper() for s in steps.split(',')]
        enabled_steps = []
        
        for step_name in step_names:
            try:
                step = MigrationStep[step_name]
                enabled_steps.append(step)
            except KeyError:
                console.print(f"[yellow]Warning: Unknown step '{step_name}', skipping[/yellow]")
        
        return enabled_steps
    else:
        # Use default steps with CLI flags
        default_steps = list(MigrationStep)
        
        if skip_git:
            default_steps = [s for s in default_steps if s != MigrationStep.GIT_SETUP]
        
        if skip_docker:
            default_steps = [s for s in default_steps if s != MigrationStep.DOCKER_STARTUP]
        
        if skip_maps:
            default_steps = [s for s in default_steps if s != MigrationStep.MAP_COMPONENTS]
        
        return default_steps


def _display_migration_results(result, no_ui: bool):
    """Display migration results in appropriate format"""
    
    if result.success:
        console.print(f"\n[bold green]✅ Migration completed successfully![/bold green]")
    else:
        console.print(f"\n[bold red]❌ Migration failed[/bold red]")
    
    # Summary statistics
    console.print(f"\nSummary:")
    console.print(f"  Theme: {result.theme_name}")
    console.print(f"  Duration: {result.total_duration_seconds:.1f}s" if result.total_duration_seconds else "  Duration: Unknown")
    console.print(f"  Files processed: {result.files_processed}")
    console.print(f"  Files created: {result.files_created}")
    console.print(f"  Files modified: {result.files_modified}")
    
    if result.files_failed > 0:
        console.print(f"  Files failed: {result.files_failed}")
    
    # Show errors if any
    if result.errors:
        console.print(f"\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")
    
    # Show warnings if any
    if result.warnings:
        console.print(f"\n[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")
    
    # Show output files
    if result.output_files and not no_ui:
        console.print(f"\n[blue]Output files:[/blue]")
        for file_path in result.output_files:
            console.print(f"  • {file_path}")


# Entry point for the migration CLI
if __name__ == '__main__':
    migration()