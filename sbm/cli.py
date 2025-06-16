"""
Command Line Interface for SBM Tool V2.

Team-friendly CLI with comprehensive commands for migration, validation,
and demo operations with Context7 integration.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

import click
from rich.console import Console

from sbm.config import get_config
from sbm.utils.logger import get_logger, setup_logging
from sbm.utils.errors import SBMError, format_error_for_display
from sbm.core.workflow import MigrationWorkflow
from sbm.core.full_workflow import FullMigrationWorkflow
from sbm.core.validation import validate_theme, validate_scss, ValidationEngine
from sbm.core.diagnostics import SystemDiagnostics
from sbm.oem.handler import OEMHandler
from sbm.oem.factory import OEMHandlerFactory


console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--log-level', default='INFO', help='Set log level (DEBUG, INFO, WARNING, ERROR)')
@click.option('--log-file', help='Log to file')
@click.option('--config', help='Path to configuration file')
@click.pass_context
def cli(ctx, verbose, log_level, log_file, config):
    """
    SBM Tool V2 - Site Builder Migration Tool
    
    FULLY AUTOMATED WORKFLOW: Just run 'sbm auto [dealer-slug]' for complete migration!
    
    Examples:
        sbm auto friendlycdjrofgeneva          # Complete automated migration
        sbm auto chryslerofportland --force    # Force migration past validation
        sbm auto dodgeofseattle --dry-run      # Preview what would be done
    
    Individual commands:
        sbm setup [slug]     # Git setup only
        sbm migrate [slug]   # Migration only  
        sbm validate [slug]  # Validation only
        sbm doctor          # System diagnostics
        sbm pr              # Create PR only
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Setup logging
    if verbose:
        log_level = 'DEBUG'
    setup_logging(log_level, log_file)
    
    # Load configuration
    try:
        ctx.obj['config'] = get_config(config)
        ctx.obj['logger'] = get_logger()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.argument('slug')
@click.option('--force', '-f', is_flag=True, help='Force migration even if validation fails')
@click.option('--dry-run', '-n', is_flag=True, help='Preview the full workflow without making changes')
@click.option('--skip-docker', is_flag=True, help='Skip Docker container monitoring (advanced users only)')
@click.option('--prod', '-p', is_flag=True, help='Use production database for Docker container')
@click.pass_context
def auto(ctx, slug, force, dry_run, skip_docker, prod):
    """
    🚀 FULLY AUTOMATED SBM WORKFLOW - Complete migration from start to finish.
    
    This command executes the complete SBM workflow in the correct order:
    1. Run diagnostics (sbm doctor)
    2. Switch to di-websites-platform directory
    3. Git setup (checkout main, pull, create branch)
    4. Start Docker container (just start {slug})
    5. Monitor Docker until ready or error
    6. Run migration (sbm migrate)
    7. Validate migration results
    8. Create GitHub PR
    9. Copy Salesforce message to clipboard
    10. Display complete summary
    
    SLUG: Dealer theme slug (e.g., 'friendlycdjrofgeneva')
    
    Examples:
        sbm auto friendlycdjrofgeneva
        sbm auto chryslerofportland --force
        sbm auto dodgeofseattle --dry-run
        sbm auto roncartercdjrinalvin --prod    # Use production database
        sbm roncartercdjrinalvin -p             # Shorthand for production mode
        sbm roncartercdjrinalvin prod           # Alternative syntax
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    start_time = time.time()
    
    try:
        # Initialize the full migration workflow
        full_workflow = FullMigrationWorkflow(config)
        
        # Display initial banner
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING FULLY AUTOMATED SBM MIGRATION WORKFLOW")
        logger.info("="*80)
        logger.info(f"📋 Dealer: {slug}")
        logger.info(f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🔧 Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
        if skip_docker:
            logger.info("⚠️  Docker container monitoring will be skipped")
        if force:
            logger.info("💪 Force mode enabled - will override validation failures")
        if prod:
            logger.info("🏭 Production database mode enabled")
        logger.info("="*80)
        
        # Execute the full workflow
        result = full_workflow.run(slug, skip_docker_wait=skip_docker, use_prod_db=prod)
        
        # Exit with appropriate code
        if result.get("success"):
            logger.info("\n🎉 FULLY AUTOMATED MIGRATION COMPLETED SUCCESSFULLY!")
            sys.exit(0)
        else:
            logger.error("\n❌ FULLY AUTOMATED MIGRATION FAILED")
            if result.get("error"):
                logger.error(f"Error: {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        duration = time.time() - start_time
        logger.warning(f"\n⚠️  Workflow interrupted by user after {duration:.1f}s")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"\n❌ Unexpected error after {duration:.1f}s: {e}")
        sys.exit(1)


def _monitor_docker_startup(slug: str, logger, config) -> Dict[str, Any]:
    """Monitor Docker container startup with real-time output visible to user."""
    try:
        logger.info(f"Starting 'just start {slug}' process...")
        logger.warning("⚠️  You will see the Docker startup output below...")
        logger.warning("⚠️  If prompted for login or passwords, please respond in the terminal")
        
        # Start the just start process with real-time output
        process = subprocess.Popen(
            ['just', 'start', slug],
            cwd=config.di_platform_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        logger.info(f"Started 'just start {slug}' (PID: {process.pid})")
        print("=" * 60)
        print(f"DOCKER STARTUP OUTPUT FOR {slug.upper()}")
        print("=" * 60)
        
        # Monitor the process with real-time output
        start_time = time.time()
        timeout = 300  # 5 minutes timeout
        output_lines = []
        
        # Read output line by line in real-time
        while True:
            # Check if process is still running
            if process.poll() is not None:
                break
                
            # Check for timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error("Timeout waiting for 'just start' to complete")
                process.terminate()
                print("=" * 60)
                return {
                    "success": False,
                    "error": "Timeout waiting for Docker container to start (5 minutes)"
                }
            
            # Read a line of output
            try:
                line = process.stdout.readline()
                if line:
                    # Print the line immediately so user can see it
                    print(line.rstrip())
                    output_lines.append(line.rstrip())
                    
                    # Check for common success indicators
                    line_lower = line.lower()
                    if any(indicator in line_lower for indicator in [
                        'server started', 'ready', 'listening on', 'compiled successfully',
                        'webpack compiled', 'development server is running'
                    ]):
                        logger.info(f"Detected startup indicator: {line.strip()}")
                else:
                    # No output, sleep briefly
                    time.sleep(0.1)
            except:
                break
        
        # Process completed, get final output
        remaining_output, _ = process.communicate()
        if remaining_output:
            print(remaining_output)
            output_lines.extend(remaining_output.split('\n'))
        
        print("=" * 60)
        
        if process.returncode == 0:
            logger.success("Docker container started successfully!")
            return {
                "success": True,
                "message": "Docker container ready",
                "duration": time.time() - start_time,
                "output": output_lines
            }
        else:
            # Look for error indicators in output
            error_lines = [line for line in output_lines if any(err in line.lower() for err in [
                'error', 'failed', 'exception', 'cannot', 'unable'
            ])]
            
            error_msg = "Docker startup failed"
            if error_lines:
                error_msg = f"Docker startup failed: {error_lines[-1]}"
            
            logger.error(f"'just start' failed with return code {process.returncode}")
            return {
                "success": False,
                "error": error_msg,
                "output": output_lines
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _display_workflow_summary(results: Dict, start_time: float, logger, dry_run: bool):
    """Display comprehensive workflow summary."""
    duration = time.time() - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    
    logger.info("=" * 60)
    logger.info("📊 WORKFLOW SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Dealer: {results['slug']}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
    logger.info(f"Duration: {minutes:02d}:{seconds:02d}")
    logger.info(f"Branch: {results.get('branch_name', 'N/A')}")
    
    if results['steps_completed']:
        logger.info(f"✅ Steps Completed ({len(results['steps_completed'])}):")
        for step in results['steps_completed']:
            logger.info(f"  - {step}")
    
    if results['steps_failed']:
        logger.info(f"❌ Steps Failed ({len(results['steps_failed'])}):")
        for step in results['steps_failed']:
            logger.info(f"  - {step}")
    
    if results['total_files_created'] > 0:
        logger.info(f"📁 Files Created: {results['total_files_created']}")
    
    if results['pr_url']:
        logger.info(f"🔗 PR URL: {results['pr_url']}")
    
    logger.info("=" * 60)


@cli.command()
@click.argument('slug')
@click.option('--auto-start', '-a', is_flag=True, help='Automatically start and monitor Docker container')
@click.pass_context
def setup(ctx, slug, auto_start):
    """
    Run pre-migration git setup for a dealer theme.
    
    This command executes the required git workflow:
    - git switch main && git pull && git fetch --prune && git status
    - git pull (second pull)
    - git checkout -b {slug}-SBM{MMYY}
    - git sparse-checkout add dealer-themes/{slug}
    
    With --auto-start, it will also run and monitor 'just start {slug}'
    
    SLUG: Dealer theme slug (e.g., 'friendlycdjrofgeneva')
    
    Examples:
        sbm setup friendlycdjrofgeneva
        sbm setup friendlycdjrofgeneva --auto-start
        sbm setup chryslerofportland -a
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        from sbm.core.git_operations import GitOperations
        git_ops = GitOperations(config)
        
        result = git_ops.pre_migration_setup(slug, auto_start=auto_start)
        
        if result['success']:
            logger.success(f"Pre-migration setup completed for {slug}")
            logger.info(f"Branch created: {result['branch_name']}")
            
            if auto_start and result.get('docker_ready'):
                logger.success("Docker container is ready!")
                logger.info("You can now run: sbm migrate {slug}")
            elif not auto_start:
                logger.warning("⚠️  WAIT for Docker container to fully start before proceeding!")
                logger.info(f"Next step: Run 'just start {slug}' in {config.di_platform_dir}")
                logger.info("Then run: sbm migrate {slug}")
        else:
            logger.error(f"Pre-migration setup failed: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Setup error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('slug')
@click.option('--force', '-f', is_flag=True, help='Force reset existing Site Builder files')
@click.option('--skip-git', is_flag=True, help='Skip Git operations')
@click.option('--skip-validation', is_flag=True, help='Skip validation steps')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.pass_context
def migrate(ctx, slug, force, skip_git, skip_validation, dry_run):
    """
    Migrate a dealer theme to Site Builder format.
    
    SLUG: Dealer theme slug (e.g., 'chryslerofportland')
    
    Examples:
        sbm migrate chryslerofportland
        sbm migrate dodgeofseattle --force
        sbm migrate jeepnorthwest --skip-git
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    start_time = time.time()
    
    try:
        # Display migration header
        oem_handler = OEMHandler(config)
        oem_info = oem_handler.detect_oem(slug)
        logger.migration_header(slug, oem_info.get('oem', 'Unknown'))
        
        # Run migration
        workflow = MigrationWorkflow(config)
        result = workflow.run(
            slug=slug,
            environment="prod",  # Default to prod for now
            dry_run=dry_run,
            force=force
        )
        
        # Display summary
        duration = time.time() - start_time
        logger.migration_summary(
            slug=slug,
            success=result['success'],
            duration=duration,
            files_created=result.get('files_created', 0),
            errors=result.get('errors', 0)
        )
        
        if result['success']:
            logger.success(f"Migration completed successfully for {slug}")
            if result.get('branch_name'):
                logger.info(f"Created branch: {result['branch_name']}")
            if result.get('pr_url'):
                logger.info(f"Pull request: {result['pr_url']}")
        else:
            logger.failure(f"Migration failed for {slug}")
            if result.get('error'):
                logger.error(str(result['error']))
            sys.exit(1)
            
    except SBMError as e:
        duration = time.time() - start_time
        logger.migration_summary(slug, False, duration, errors=1)
        logger.error_with_suggestion(e.message, e.suggestion or "Check logs for details")
        sys.exit(1)
    except Exception as e:
        duration = time.time() - start_time
        logger.migration_summary(slug, False, duration, errors=1)
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('slug')
@click.option('--scss-only', is_flag=True, help='Validate only SCSS files')
@click.option('--fix', is_flag=True, help='Attempt to fix validation errors')
@click.pass_context
def validate(ctx, slug, scss_only, fix):
    """
    Validate a dealer theme and its Site Builder files.
    
    SLUG: Dealer theme slug to validate
    
    Examples:
        sbm validate chryslerofportland
        sbm validate dodgeofseattle --scss-only
        sbm validate jeepnorthwest --fix
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        logger.step(f"Validating theme: {slug}")
        
        if scss_only:
            results = validate_scss(slug, config)
        else:
            results = validate_theme(slug, config)
        
        logger.validation_results(results)
        
        # Check if validation passed
        all_passed = all(
            result.get('passed', False) if isinstance(result, dict) else result
            for result in results.values()
        )
        
        if all_passed:
            logger.success(f"Validation passed for {slug}")
        else:
            logger.failure(f"Validation failed for {slug}")
            if fix:
                logger.step("Attempting to fix validation errors...")
                # TODO: Implement auto-fix functionality
                logger.warning("Auto-fix not yet implemented")
            sys.exit(1)
            
    except SBMError as e:
        logger.error_with_suggestion(e.message, e.suggestion or "Check validation logs")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('slug')
@click.pass_context
def status(ctx, slug):
    """
    Show the current status of a dealer theme migration.
    
    SLUG: Dealer theme slug to check
    
    Examples:
        sbm status chryslerofportland
        sbm status dodgeofseattle
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        theme_path = config.get_theme_path(slug)
        
        if not theme_path.exists():
            logger.failure(f"Theme not found: {slug}")
            sys.exit(1)
        
        logger.step(f"Checking status for: {slug}")
        
        # Check Site Builder files
        sb_files = [
            'sb-inside.scss',
            'sb-vdp.scss', 
            'sb-vrp.scss',
            'sb-home.scss'
        ]
        
        status_info = {}
        for sb_file in sb_files:
            file_path = theme_path / sb_file
            status_info[sb_file] = {
                'exists': file_path.exists(),
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'modified': file_path.stat().st_mtime if file_path.exists() else None
            }
        
        # Check OEM detection
        factory = OEMHandlerFactory(config)
        oem_handler = factory.get_handler(slug)
        status_info['oem'] = {
            'detected': oem_handler.get_oem_name(),
            'brand': oem_handler.detect_brand(slug)
        }
        
        # Display status
        from rich.table import Table
        table = Table(title=f"Status: {slug}")
        table.add_column("Component", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        # Site Builder files
        for sb_file, info in status_info.items():
            if sb_file == 'oem':
                continue
            status = "✅" if info['exists'] else "❌"
            details = f"{info['size']} bytes" if info['exists'] else "Not found"
            table.add_row(sb_file, status, details)
        
        # OEM info
        table.add_row(
            "OEM Detection",
            "✅",
            f"{status_info['oem']['detected']} ({status_info['oem']['brand']})"
        )
        
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def config_info(ctx):
    """Show current configuration information."""
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        config_dict = config.to_dict()
        
        from rich.tree import Tree
        tree = Tree("🔧 SBM Tool V2 Configuration")
        
        # Core paths
        paths_branch = tree.add("📁 Paths")
        paths_branch.add(f"DI Platform: {config_dict['di_platform_dir']}")
        paths_branch.add(f"Dealer Themes: {config_dict['dealer_themes_dir']}")
        paths_branch.add(f"Common Theme: {config_dict['common_theme_dir']}")
        

        
        console.print()
        console.print(tree)
        console.print()
        
    except Exception as e:
        logger.error(f"Configuration display error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--list-themes', is_flag=True, help='List available dealer themes')
# @click.option('--check-context7', is_flag=True, help='Test Context7 connection')
@click.option('--check-git', is_flag=True, help='Check Git repository status')
@click.pass_context
def doctor(ctx, list_themes, check_git):
    """
    Run diagnostic checks on the SBM tool setup.
    
    Examples:
        sbm doctor
        sbm doctor --list-themes
        sbm doctor --check-git
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        logger.step("Running SBM Tool diagnostics...")
        
        checks = {}
        
        # Basic configuration check
        checks['Configuration'] = {
            'passed': True,
            'message': 'Configuration loaded successfully'
        }
        
        # DI Platform directory check
        checks['DI Platform Directory'] = {
            'passed': config.di_platform_dir.exists(),
            'message': str(config.di_platform_dir)
        }
        
        # Dealer themes directory check
        checks['Dealer Themes Directory'] = {
            'passed': config.dealer_themes_dir.exists(),
            'message': str(config.dealer_themes_dir)
        }
        
        if list_themes and config.dealer_themes_dir.exists():
            themes = [d.name for d in config.dealer_themes_dir.iterdir() if d.is_dir()]
            logger.info(f"Found {len(themes)} dealer themes")
            for theme in sorted(themes)[:10]:  # Show first 10
                logger.info(f"  - {theme}")
            if len(themes) > 10:
                logger.info(f"  ... and {len(themes) - 10} more")
        

        
        if check_git:
            try:
                from sbm.core.git import GitOperations
                git_ops = GitOperations(config)
                checks['Git Repository'] = {
                    'passed': git_ops.check_repository_status(),
                    'message': 'Repository is clean and ready'
                }
            except Exception as e:
                checks['Git Repository'] = {
                    'passed': False,
                    'message': str(e)
                }
        
        logger.validation_results(checks)
        
        # Overall status
        all_passed = all(check['passed'] for check in checks.values())
        if all_passed:
            logger.success("All diagnostic checks passed!")
        else:
            logger.failure("Some diagnostic checks failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Diagnostic error: {e}")
        sys.exit(1)


@cli.command(name="create-pr", context_settings=dict(help_option_names=["-h", "--help"]))
@click.option('--slug', '-s', help='Dealer slug (auto-detected if in dealer-themes directory)')
@click.option('--branch', '-b', help='Branch to create PR for (defaults to current branch)')
@click.option('--title', '-t', help='Custom PR title')
@click.option('--draft', '-d', is_flag=True, default=False, help='Create as draft')
@click.option('--publish', '-p', is_flag=True, default=True, help='Create as published PR (default: true)')
@click.option('--reviewers', '-r', help='Comma-separated list of reviewers')
@click.option('--labels', '-l', help='Comma-separated list of labels')
@click.pass_context
def create_pr(ctx, slug, branch, title, draft, publish, reviewers, labels):
    """Create a GitHub pull request with SBM-specific content.

    This command creates a properly formatted PR for Site Builder migrations,
    with auto-detection of dealer slug and SBM-specific content.

    Examples:
        sbm create-pr                           # Auto-detect everything
        sbm pr -s friendlychryslerdodge         # Specify slug
        sbm pr --publish -r "user1,user2"       # Published PR with reviewers
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        from sbm.core.git_operations import GitOperations
        git_ops = GitOperations(config)
        
        # Auto-detect slug if not provided
        if not slug:
            import os
            current_dir = os.getcwd()
            if "dealer-themes" in current_dir:
                slug = os.path.basename(current_dir)
                logger.info(f"Auto-detected dealer slug: {slug}")
            else:
                logger.error("Could not auto-detect dealer slug. Please specify with --slug or run from dealer-themes directory")
                sys.exit(1)
        
        # Auto-detect branch if not provided
        if not branch:
            try:
                import subprocess
                branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
                logger.info(f"Using current branch: {branch}")
            except Exception as e:
                logger.error(f"Could not determine current branch: {e}")
                sys.exit(1)
        
        # Handle draft/publish logic - default to published unless draft is explicitly requested
        if draft:
            draft = True
        else:
            draft = False
        
        # Override config reviewers/labels if specified
        if reviewers:
            config.git.default_reviewers = [r.strip() for r in reviewers.split(',')]
        if labels:
            config.git.default_labels = [l.strip() for l in labels.split(',')]
        
        logger.step(f"Creating GitHub PR for {slug} on branch {branch}")
        
        # Push branch first
        if not git_ops.push_branch(branch):
            logger.warning("Failed to push branch, but continuing with PR creation")
        
        # Create the PR
        result = git_ops.create_pr(slug, branch, draft)
        
        if result['success']:
            logger.success(f"✅ Pull request created: {result['pr_url']}")
            logger.info(f"Title: {result['title']}")
            logger.info(f"Branch: {result['branch']}")
            if draft:
                logger.info("📝 Created as draft - remember to publish when ready")
        else:
            logger.error(f"❌ PR creation failed: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

# Alias: `sbm pr`
cli.add_command(create_pr, name='pr')


@cli.command()
@click.argument('slug')
@click.option('--prod', '-p', is_flag=True, help='Use production database for Docker container')
@click.pass_context
def monitor(ctx, slug, prod):
    """
    Monitor the 'just start' process for a dealer theme.
    
    This command will start and monitor 'just start {slug}' and wait
    for the Docker container to be fully ready.
    
    SLUG: Dealer theme slug (e.g., 'friendlycdjrofgeneva')
    
    Examples:
        sbm monitor friendlycdjrofgeneva
        sbm monitor chryslerofportland
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']
    
    try:
        from sbm.core.git_operations import GitOperations
        git_ops = GitOperations(config)
        
        result = git_ops.monitor_just_start(slug, prod)
        
        if result['success']:
            logger.success("Docker container is ready!")
            duration = result.get('duration', 0)
            logger.info(f"Startup completed in {duration:.1f} seconds")
            logger.info(f"You can now run: sbm migrate {slug}")
        else:
            logger.error(f"Docker startup failed: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    try:
        # Check if first argument looks like a dealer slug (no dashes, not a command)
        import sys
        if len(sys.argv) > 1:
            first_arg = sys.argv[1]
            # If it's not a known command and doesn't start with -, treat as slug for auto command
            known_commands = ['auto', 'setup', 'migrate', 'validate', 'status', 'config-info', 'doctor', 'create-pr', 'pr', 'monitor', '--help', '-h', '--version', 'prod']
            if first_arg not in known_commands and not first_arg.startswith('-'):
                # Check if second argument is 'prod' - if so, add -p flag
                if len(sys.argv) > 2 and sys.argv[2] == 'prod':
                    # Remove 'prod' and add -p flag: slug prod -> auto slug -p
                    sys.argv.pop(2)  # Remove 'prod'
                    sys.argv.insert(1, 'auto')  # Insert 'auto' before slug
                    sys.argv.append('-p')  # Add -p flag at the end
                else:
                    # Insert 'auto' command before the slug
                    sys.argv.insert(1, 'auto')
        
        cli()
    except KeyboardInterrupt:
        console.print("\n❌ Operation cancelled by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        sys.exit(1)


if __name__ == '__main__':
    main() 
