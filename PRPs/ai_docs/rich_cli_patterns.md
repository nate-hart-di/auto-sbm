# Rich CLI Implementation Patterns for SBM Tool

## Core Rich Components for SBM Enhancement

### 1. Progress Tracking Patterns

**Multi-Step Migration Progress:**
```python
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

class MigrationProgress:
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
        )
    
    def run_migration(self, theme_name: str):
        with self.progress:
            overall_task = self.progress.add_task(f"[cyan]Migrating {theme_name}", total=6)
            
            # Step 1: Git Operations
            step_task = self.progress.add_task("Setting up Git branch", total=100)
            self.execute_git_operations(step_task)
            self.progress.update(overall_task, advance=1)
            
            # Step 2: Docker Environment  
            step_task = self.progress.add_task("Starting Docker environment", total=100)
            self.execute_docker_startup(step_task)
            self.progress.update(overall_task, advance=1)
            
            # Continue for all 6 steps...
```

**File Processing Progress:**
```python
from rich.progress import track

def process_scss_files(file_paths: List[str]):
    for file_path in track(file_paths, description="Processing SCSS files..."):
        transform_scss_file(file_path)
```

### 2. Status Display Patterns

**Status Panel Creation:**
```python
from rich.panel import Panel
from rich.console import Console

console = Console()

def show_migration_status(theme_name: str, step: str, status: str):
    status_icons = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌", 
        "in_progress": "⏳"
    }
    
    panel = Panel(
        f"[bold blue]Theme:[/] {theme_name}\n"
        f"[bold green]Step:[/] {step}\n"
        f"[bold]Status:[/] {status_icons[status]} {status}",
        title="Migration Status",
        border_style="cyan"
    )
    console.print(panel)
```

### 3. Error Display Enhancement

**Rich Error Panels:**
```python
from rich.panel import Panel
from rich.syntax import Syntax

def show_compilation_error(error_info: dict):
    error_panel = Panel(
        f"[bold red]SCSS Compilation Error[/]\n\n"
        f"[bold]File:[/] {error_info['file']}\n"
        f"[bold]Line:[/] {error_info['line']}\n"
        f"[bold]Error:[/] {error_info['message']}\n\n"
        f"[dim]Attempting automatic fix...[/]",
        title="Compilation Error",
        border_style="red"
    )
    console.print(error_panel)
```

### 4. Docker Integration Patterns

**Docker Log Monitoring:**
```python
from rich.live import Live
from rich.table import Table

def monitor_docker_logs():
    table = Table(title="Docker Container Status")
    table.add_column("Container", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Logs", style="white")
    
    with Live(table, refresh_per_second=2) as live:
        # Update table with Docker status
        for log_line in stream_docker_logs():
            table.add_row("gulp", "Running", log_line)
            live.update(table)
```

### 5. Interactive Review Interface

**Manual Review Panel:**
```python
from rich.prompt import Confirm
from rich.table import Table

def manual_review_interface(theme_name: str, files: List[str]):
    table = Table(title=f"Files to Review - {theme_name}")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Lines", style="white")
    
    for file_path in files:
        line_count = count_lines(file_path)
        status = "✅ Ready" if line_count > 0 else "⚠️ Empty"
        table.add_row(file_path, status, str(line_count))
    
    console.print(table)
    
    return Confirm.ask(
        "[bold cyan]Continue with migration after review?[/]",
        default=True
    )
```

## Critical Implementation Notes

### Logger Integration
```python
import logging
from rich.logging import RichHandler

# Replace existing logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
```

### Console Initialization
```python
from rich.console import Console

# Global console instance
console = Console()

# For testing
console = Console(file=StringIO(), force_terminal=False)
```

### Theming Configuration
```python
from rich.theme import Theme

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green"
})
console = Console(theme=custom_theme)
```

## Best Practices for SBM Integration

1. **Preserve Existing Patterns**: Use `click.echo()` for simple messages, Rich for complex displays
2. **Graceful Fallbacks**: Always provide no-color fallbacks for CI/CD environments
3. **Performance**: Use transient progress bars for better terminal performance
4. **Testing**: Use StringIO redirection for testing Rich output
5. **Configuration**: Respect `--verbose` flag for detailed vs. simplified output

## Environment Considerations

- **CI/CD**: Rich automatically detects CI environments and disables fancy output
- **Terminal Support**: Rich gracefully degrades on unsupported terminals
- **Color Themes**: Use colorblind-friendly patterns with shapes and symbols
- **Performance**: Rich is highly optimized but test with large outputs