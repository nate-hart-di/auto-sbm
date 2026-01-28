# Story 1.3: Enhanced CLI History Display

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want `sbm stats --history` to show me duration, lines migrated, and report locations,
So that I have a complete picture of my migration activity without checking log files.

## Acceptance Criteria

**Given** I have migration history with the new rich data
**When** I run `sbm stats --history`
**Then** the table displays new columns: "Duration", "Lines", "Saved", and "Report"
**And** "Duration" is formatted nicely (e.g., "1m 30s")
**And** "Report" shows the relative path to the generated markdown file
**And** old migration records display "N/A" for missing data columns gracefully

## Tasks / Subtasks

- [x] Task 1: Add new columns to history table (AC: All criteria)
  - [x] Update `stats()` function in `sbm/cli.py` (lines 1409-1564)
  - [x] Add "Duration" column with formatted display (e.g., "1m 30s", "45s")
  - [x] Add "Lines" column showing `lines_migrated` value
  - [x] Add "Saved" column calculating time saved from lines (lines/800 hours)
  - [x] Add "Report" column showing relative path to report file
  - [x] Handle missing data gracefully (show "N/A" or "-" for old records)

- [x] Task 2: Implement duration formatting helper (AC: Nice formatting)
  - [x] Create `_format_duration(seconds: float) -> str` helper function
  - [x] Format as "Xm Ys" for minutes + seconds
  - [x] Format as "Xs" for seconds only
  - [x] Handle edge cases (0, negative, very large values)

- [x] Task 3: Implement time saved calculation (AC: Time saved displayed)
  - [x] Create `_calculate_time_saved(lines_migrated: int) -> str` helper
  - [x] Calculate hours saved: lines / 800
  - [x] Format as "Xh" or "X.Xh" (1 decimal place)
  - [x] Handle zero lines case

- [x] Task 4: Add filtering CLI options (AC: Filtering works)
  - [x] Add `--limit N` option (default: 10, max: 100)
  - [x] Add `--since DATE` option (YYYY-MM-DD format)
  - [x] Add `--until DATE` option (YYYY-MM-DD format)
  - [x] Add `--user USERNAME` option for filtering by user
  - [x] Implement filtering logic in `stats()` function
  - [x] Update help text for all new options

- [x] Task 5: Write comprehensive unit tests (AC: All tests pass)
  - [x] Create `tests/test_cli_history.py` (NEW)
  - [x] Test duration formatting with various inputs
  - [x] Test time saved calculation
  - [x] Test table rendering with new columns
  - [x] Test filtering options (limit, since, until, user)
  - [x] Test backward compatibility with old data (missing fields)

- [x] Task 6: Verify integration end-to-end (AC: Fully functional)
  - [x] Run migrations to generate rich data
  - [x] Verify enhanced history table displays correctly
  - [x] Test all filtering options
  - [x] Verify old records still display
  - [x] Run full test suite to ensure no regressions

## Dev Notes

### Critical Context from Analysis

#### Review Follow-ups (AI)
- [x] [AI-Review][Medium] Untracked File: `tests/test_cli_history.py` is present but not committed to git.
- [x] [AI-Review][Medium] File List missing in Dev Agent Record.


**Current Implementation (cli.py lines 1409-1564):**
- Existing columns: Timestamp, Theme Slug, Command, Status, Time (currently NOT shown even though "Time" column header exists)
- Uses Rich Table API for rendering
- Displays last 10 runs by default: `reversed(runs[-10:])`
- Data comes from `get_migration_stats()` which returns `runs` array
- Each run has: timestamp, slug, command, status, duration_seconds, lines_migrated, etc.

**What's Available in run data (from tracker.py):**
```python
run_entry = {
    "timestamp": "2026-01-09T...",
    "slug": "test-theme",
    "command": "auto",
    "status": "success",
    "duration_seconds": 45.5,        # ← Already tracked!
    "automation_seconds": 30.0,
    "lines_migrated": 850,           # ← Already tracked! (Story 1.1)
    "manual_estimate_seconds": 14400,
    "report_path": ".sbm-reports/..." # ← Will be added by Story 1.2
}
```

**Key Finding:** Duration and lines are ALREADY in the data, we just need to **display** them!

### Architecture Patterns and Constraints

**From Architecture.md:**
- Tech Stack: Python 3.9+, Click, Rich
- UI Library: Rich for terminal output
- Follow existing CLI patterns in `sbm/cli.py`

**Rich Table API Patterns (already in use):**
```python
from rich.table import Table

table = Table(
    title="Recent Migration Runs",
    title_style="bold cyan",
    show_header=True,
    header_style="bold magenta",
)

table.add_column("Timestamp", style="dim")
table.add_column("Theme Slug", style="cyan")
# ... add more columns

table.add_row(col1_value, col2_value, ...)  # Add data rows
```

### Implementation Approach

**Step 1: Add Formatting Helper Functions**

Add before the `stats()` function in `sbm/cli.py`:

```python
def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 1:
        return "< 1s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _calculate_time_saved(lines_migrated: int) -> str:
    """Calculate time saved from lines migrated (800 lines = 1 hour)."""
    if lines_migrated == 0:
        return "-"

    hours_saved = lines_migrated / 800

    if hours_saved < 0.1:
        return "< 0.1h"

    return f"{hours_saved:.1f}h"
```

**Step 2: Update Table Column Definitions**

In the `stats()` function, after line 1547 where table columns are defined:

```python
# BEFORE (current):
table.add_column("Timestamp", style="dim")
table.add_column("Theme Slug", style="cyan")
table.add_column("Command", style="green")
table.add_column("Status", style="bold")
table.add_column("Time", justify="right")

# AFTER (enhanced):
table.add_column("Timestamp", style="dim")
table.add_column("Theme Slug", style="cyan")
table.add_column("Command", style="green")
table.add_column("Status", style="bold")
table.add_column("Duration", justify="right", style="yellow")
table.add_column("Lines", justify="right", style="cyan")
table.add_column("Saved", justify="right", style="green")
table.add_column("Report", style="dim", no_wrap=True)
```

**Step 3: Update Row Data Population**

In the loop that adds rows (after line 1558):

```python
for run in reversed(runs[-10:]):  # Show last 10
    status = run.get("status", "unknown")
    status_color = "green" if status == "success" else "red"

    # Extract data with graceful fallbacks
    duration_seconds = run.get("duration_seconds", 0)
    lines_migrated = run.get("lines_migrated", 0)
    report_path = run.get("report_path", "")

    # Format values
    duration_str = _format_duration(duration_seconds) if duration_seconds else "N/A"
    lines_str = f"{lines_migrated:,}" if lines_migrated else "N/A"
    saved_str = _calculate_time_saved(lines_migrated)
    report_str = report_path if report_path else "N/A"

    table.add_row(
        run.get("timestamp", "Unknown")[:19].replace("T", " "),
        run.get("slug", "Unknown"),
        run.get("command", ""),
        Text(status, style=status_color),
        duration_str,
        lines_str,
        saved_str,
        report_str,
    )
```

**Step 4: Add CLI Filtering Options**

Update the `@click.option` decorators before `def stats()`:

```python
@cli.command()
@click.option("--list", "show_list", is_flag=True, help="List individual site migrations")
@click.option("--history", is_flag=True, help="Show migration history over time")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--limit", type=int, default=10, help="Number of runs to display (default: 10, max: 100)")
@click.option("--since", type=str, help="Filter runs since date (YYYY-MM-DD)")
@click.option("--until", type=str, help="Filter runs until date (YYYY-MM-DD)")
@click.option("--user", type=str, help="Filter runs by username")
@click.pass_context
def stats(ctx: click.Context, show_list: bool, history: bool, verbose: bool,
          limit: int, since: str, until: str, user: str) -> None:
```

**Step 5: Implement Filtering Logic**

Add filtering before the loop:

```python
if history:
    runs = stats_data.get("runs", [])

    # Apply filters
    filtered_runs = runs

    if since:
        try:
            since_date = datetime.fromisoformat(since)
            filtered_runs = [r for r in filtered_runs if datetime.fromisoformat(r["timestamp"][:10]) >= since_date]
        except ValueError:
            rich_console.print(f"[red]Invalid date format for --since: {since}[/red]")
            return

    if until:
        try:
            until_date = datetime.fromisoformat(until)
            filtered_runs = [r for r in filtered_runs if datetime.fromisoformat(r["timestamp"][:10]) <= until_date]
        except ValueError:
            rich_console.print(f"[red]Invalid date format for --until: {until}[/red]")
            return

    if user:
        # If user field exists in run data
        filtered_runs = [r for r in filtered_runs if r.get("user_id") == user]

    # Apply limit (max 100)
    limit = min(limit, 100)

    if filtered_runs:
        # ... rest of table rendering
        for run in reversed(filtered_runs[-limit:]):  # Changed from [-10:]
```

### File Structure Requirements

Per architecture, update existing file:
```
sbm/
  cli.py             # Update stats() function (lines 1409-1564)
tests/
  test_cli_history.py  # NEW: Test enhanced history display
```

### Testing Requirements

**Unit Tests** (in `tests/test_cli_history.py` - NEW FILE):

```python
import pytest
from sbm.cli import _format_duration, _calculate_time_saved

def test_format_duration_seconds_only():
    assert _format_duration(45.5) == "45s"
    assert _format_duration(0.5) == "< 1s"

def test_format_duration_minutes_and_seconds():
    assert _format_duration(90) == "1m 30s"
    assert _format_duration(125.7) == "2m 5s"

def test_format_duration_edge_cases():
    assert _format_duration(0) == "< 1s"
    assert _format_duration(3600) == "60m 0s"

def test_calculate_time_saved():
    assert _calculate_time_saved(800) == "1.0h"
    assert _calculate_time_saved(1600) == "2.0h"
    assert _calculate_time_saved(400) == "0.5h"
    assert _calculate_time_saved(0) == "-"

def test_calculate_time_saved_small_values():
    assert _calculate_time_saved(50) == "< 0.1h"

# Integration test with Click CLI runner
from click.testing import CliRunner
from sbm.cli import cli

def test_stats_history_command():
    """Test that stats --history command runs without error."""
    runner = CliRunner()
    result = runner.invoke(cli, ['stats', '--history'])
    assert result.exit_code == 0

def test_stats_history_with_limit():
    """Test stats --history --limit option."""
    runner = CliRunner()
    result = runner.invoke(cli, ['stats', '--history', '--limit', '25'])
    assert result.exit_code == 0

def test_stats_history_with_filters():
    """Test stats --history with date filters."""
    runner = CliRunner()
    result = runner.invoke(cli, ['stats', '--history', '--since', '2026-01-01', '--limit', '5'])
    assert result.exit_code == 0
```

**Integration Test:**
```bash
# Run real command to verify output
sbm stats --history
sbm stats --history --limit 25
sbm stats --history --since 2026-01-01
sbm stats --history --user nate-hart-di
```

### Dependencies on Other Stories

**Story 1.1 (Migration Data Schema):**
- ✅ Provides `lines_migrated` field in run data
- ✅ Provides `duration_seconds` field in run data
- Must be completed first

**Story 1.2 (Detailed Report Generation):**
- ✅ Provides `report_path` field in run data
- Should be completed first (or handle missing report_path gracefully)

### Backward Compatibility

**Critical:** Old migration records won't have:
- `report_path` field (Story 1.2 adds this)
- Possibly missing `lines_migrated` (if run before Story 1.1)

**Solution:** Use `.get()` with defaults and display "N/A" for missing data:
```python
lines_migrated = run.get("lines_migrated", 0)
report_path = run.get("report_path", "")

lines_str = f"{lines_migrated:,}" if lines_migrated else "N/A"
report_str = report_path if report_path else "N/A"
```

### References

- [Source: enumerated-petting-puffin.md#Phase 1: Enhanced CLI History Display]
- [Source: epics.md#Story 1.3: Enhanced CLI History Display]
- [Source: architecture.md#CLI Layer, Tech Stack]
- [Source: sbm/cli.py#stats function (L1409-1564)]
- [Source: sbm/utils/tracker.py#get_migration_stats, record_run]
- [Rich Table Documentation: https://rich.readthedocs.io/en/stable/tables.html]

## Project Structure Notes

**Alignment with Architecture:**
- Follows existing Rich Table pattern for CLI output
- Uses existing data from tracker (no new data collection needed)
- Enhances user experience without changing core logic
- Backward compatible with old data

**Detected Patterns:**
- CLI uses Rich library for all terminal output
- Helper functions are private (prefix with `_`)
- Click decorators for command options
- Graceful degradation for missing data

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

- `tests/test_cli_history.py`
- `sbm/cli.py`
