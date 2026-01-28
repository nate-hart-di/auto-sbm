# Story 1.4: History Filtering & Pagination

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want to filter my migration history by date, user, or limit,
So that I can find specific runs easily without scrolling through hundreds of entries.

## Acceptance Criteria

**Given** I have a large history of migrations
**When** I run `sbm stats --history --limit 5`
**Then** only the 5 most recent runs are shown

**When** I run `sbm stats --history --since 2024-01-01`
**Then** only runs from that date onwards are shown

**When** I run `sbm stats --history --until 2024-12-31`
**Then** only runs up to that date are shown

**When** I run `sbm stats --history --user nate-hart-di`
**Then** only runs by that specific user are shown

**And** filters can be combined (e.g., `--limit 10 --since 2024-01-01`)
**And** filtering works correctly with the enhanced table display from Story 1.3

## Tasks / Subtasks

- [x] Task 1: Add CLI filter options to `sbm stats` command (AC: All filter options available)
  - [x] Add `--limit` option (integer, default: show all)
  - [x] Add `--since` option (date string in ISO format YYYY-MM-DD)
  - [x] Add `--until` option (date string in ISO format YYYY-MM-DD)
  - [x] Add `--user` option (string, user ID or username)
  - [x] Update help text with examples

- [x] Task 2: Implement filtering logic in tracker.py (AC: Filters work correctly)
  - [x] Create `filter_runs()` helper function
  - [x] Implement date range filtering (ISO8601 parsing)
  - [x] Implement user filtering (match against user_id field)
  - [x] Implement limit/pagination (take last N entries after filtering)
  - [x] Handle edge cases (invalid dates, empty results, etc.)

- [x] Task 3: Update `get_migration_stats()` to support filters (AC: Filters applied to stats)
  - [x] Add optional filter parameters to function signature
  - [x] Apply filters before returning runs data
  - [x] Preserve backward compatibility (filters default to None = show all)

- [x] Task 4: Update CLI to pass filters to tracker (AC: CLI integration complete)
  - [x] Parse CLI options in `stats` command
  - [x] Pass filter parameters to `get_migration_stats()`
  - [x] Display filtered results in enhanced table from Story 1.3

- [x] Task 5: Write comprehensive unit tests (AC: All tests pass)
  - [x] Create `tests/test_history_filtering.py`
  - [x] Test each filter type independently
  - [x] Test combined filters
  - [x] Test edge cases (invalid dates, no matches, etc.)
  - [x] Test backward compatibility (no filters = all results)

- [x] Task 6: Integration testing (AC: End-to-end verification)
  - [x] Test filtering with real migration history
  - [x] Verify table display with filtered results
  - [x] Test all CLI option combinations
  - [x] Verify performance with large history (500+ runs)
  - [x] Run full test suite to ensure no regressions

## Dev Notes

### Critical Context from Analysis

#### Review Follow-ups (AI)
- [x] [AI-Review][Critical] Missing Tests: `tests/test_history_filtering.py` is marked as completed but does not exist in the codebase.
- [x] [AI-Review][Medium] File List missing in Dev Agent Record.


**Existing History Display (Story 1.3):**
- Enhanced CLI history table in `sbm/cli.py` (stats command)
- Uses `get_migration_stats()` to retrieve run data
- Displays: Duration, Lines, Saved, Report columns
- Located in stats command implementation
- This story adds filtering capabilities to that display

**Data Source:**
- Migration runs stored in `~/.sbm_migrations.json`
- Structure from `tracker.py:_read_tracker()`:
  ```json
  {
    "migrations": [...],
    "runs": [
      {
        "timestamp": "2024-01-15T10:30:00.000000Z",
        "slug": "dealer-theme-slug",
        "command": "auto",
        "status": "success",
        "duration_seconds": 45.3,
        "automation_seconds": 42.1,
        "lines_migrated": 850,
        "manual_estimate_seconds": 14400
      }
    ],
    "last_updated": "2024-01-15T10:30:00.000000Z"
  }
  ```
- Keep only last 500 runs (tracker.py line 186)

### Architecture Patterns and Constraints

**From Architecture.md:**
- Tech Stack: Python 3.9+, Click, Rich
- Follow existing patterns in `sbm/utils/` modules
- Use Path objects from pathlib (not string paths)
- Log with `from sbm.utils.logger import logger`
- Handle errors gracefully without crashing CLI

**Click CLI Patterns:**
- Use `@click.option()` decorators for new flags
- Type hints: `type=int`, `type=str`
- Help text with `help=` parameter
- Multiple options can be combined

**Rich Table Display:**
- Already implemented in Story 1.3
- Filter data BEFORE rendering table
- Preserve column structure and formatting

### Implementation Requirements

**1. CLI Option Specifications:**

```python
# In sbm/cli.py, stats command

@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit results to most recent N runs"
)
@click.option(
    "--since",
    type=str,
    default=None,
    help="Show runs from this date onwards (YYYY-MM-DD)"
)
@click.option(
    "--until",
    type=str,
    default=None,
    help="Show runs up to this date (YYYY-MM-DD)"
)
@click.option(
    "--user",
    type=str,
    default=None,
    help="Filter by user ID or username"
)
```

**2. Filter Function in tracker.py:**

```python
def filter_runs(
    runs: list[dict],
    limit: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    user: Optional[str] = None,
) -> list[dict]:
    """
    Filter migration runs based on provided criteria.

    Args:
        runs: List of run dictionaries from tracker
        limit: Maximum number of runs to return (most recent)
        since: ISO date string (YYYY-MM-DD) - include runs from this date onwards
        until: ISO date string (YYYY-MM-DD) - include runs up to this date
        user: User ID to filter by

    Returns:
        Filtered list of runs
    """
```

**3. Date Parsing:**
- Use `datetime.fromisoformat()` for parsing user input
- Run timestamps are in ISO8601 format with Z suffix
- Parse run timestamp: `datetime.fromisoformat(run["timestamp"].replace("Z", "+00:00"))`
- Compare date objects for date range filtering
- Handle timezone-aware comparisons (all timestamps are UTC)

**4. User Filtering:**
- Currently runs don't have user_id field in old schema
- Will need to handle backward compatibility
- Check if run has `user_id` field before filtering
- If missing, skip or use default user ID logic

**5. Filter Application Order:**
1. Date filtering (since/until)
2. User filtering
3. Sort by timestamp (most recent first)
4. Apply limit (take first N)

### Integration Points

**1. `sbm/cli.py` stats command:**
```python
@cli.command()
@click.option("--history", is_flag=True, help="Show detailed run history")
@click.option("--limit", type=int, default=None, help="Limit to N most recent")
@click.option("--since", type=str, default=None, help="From date (YYYY-MM-DD)")
@click.option("--until", type=str, default=None, help="To date (YYYY-MM-DD)")
@click.option("--user", type=str, default=None, help="Filter by user")
def stats(history: bool, limit: int, since: str, until: str, user: str):
    """Display migration statistics."""
    # Get stats with filters
    stats_data = get_migration_stats(
        limit=limit,
        since=since,
        until=until,
        user=user
    )
    # Display filtered results...
```

**2. `sbm/utils/tracker.py` modification:**
```python
def get_migration_stats(
    limit: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    user: Optional[str] = None,
) -> dict:
    """Return tracker stats with optional filtering."""
    local_data = _read_tracker()

    # Apply filters to runs
    filtered_runs = filter_runs(
        local_data.get("runs", []),
        limit=limit,
        since=since,
        until=until,
        user=user
    )

    # Calculate metrics from filtered data
    local_stats = _calculate_metrics({
        "migrations": local_data.get("migrations", []),
        "runs": filtered_runs,
        "last_updated": local_data.get("last_updated")
    })

    # Return stats with filtered runs
    return {
        "count": len(local_data.get("migrations", [])),
        "migrations": local_data.get("migrations", []),
        "runs": filtered_runs,  # Filtered
        "metrics": local_stats,
        "global_metrics": _aggregate_global_stats(),
        "last_updated": local_data.get("last_updated"),
        "path": str(TRACKER_FILE),
        "user_id": _get_user_id(),
    }
```

### Testing Strategy

**From existing test patterns:**
- Use `pytest` with `unittest.mock`
- Mock _read_tracker() to provide test data
- Test with various date formats
- Use `freezegun` if needed for timestamp testing

**Specific tests needed:**

1. **`tests/test_history_filtering.py`:**

```python
def test_filter_runs_limit():
    """Test limit filter returns correct number of runs"""

def test_filter_runs_since_date():
    """Test since date filter includes correct runs"""

def test_filter_runs_until_date():
    """Test until date filter excludes future runs"""

def test_filter_runs_date_range():
    """Test combined since/until filtering"""

def test_filter_runs_user():
    """Test user filtering matches user_id"""

def test_filter_runs_combined():
    """Test all filters work together"""

def test_filter_runs_invalid_date():
    """Test graceful handling of invalid date format"""

def test_filter_runs_empty_results():
    """Test filtering returns empty list when no matches"""

def test_filter_runs_no_filters():
    """Test no filters returns all runs (backward compatibility)"""

def test_get_migration_stats_with_filters():
    """Test get_migration_stats applies filters correctly"""
```

### Edge Cases & Error Handling

1. **Invalid Date Formats:**
   - Catch `ValueError` from `datetime.fromisoformat()`
   - Show helpful error message: "Invalid date format. Use YYYY-MM-DD"
   - Don't crash, return unfiltered or skip that filter

2. **No Matching Results:**
   - Return empty list from filter_runs()
   - Display message in CLI: "No runs match the specified filters"

3. **Limit Larger Than Available:**
   - Simply return all available runs (no error)

4. **Timezone Handling:**
   - All timestamps are UTC (Z suffix)
   - User input dates treated as UTC midnight
   - Use timezone-aware datetime comparisons

5. **Backward Compatibility:**
   - Old runs may not have user_id field
   - Skip user filter for old runs without user_id
   - Document this limitation

### File Locations

Repository root: `/Users/nathanhart/auto-sbm`
- Modify: `/Users/nathanhart/auto-sbm/sbm/utils/tracker.py`
- Modify: `/Users/nathanhart/auto-sbm/sbm/cli.py`
- New test: `/Users/nathanhart/auto-sbm/tests/test_history_filtering.py`

### Performance Considerations

- Current limit: 500 runs stored (tracker.py line 186)
- Filtering 500 items is negligible performance impact
- Date parsing could be optimized if needed (pre-parse once)
- Consider caching parsed dates if filtering becomes slow

### Latest Technology Information

**Python datetime (3.9+):**
- Use `datetime.fromisoformat()` for ISO8601 parsing
- Handle timezone with `.replace("Z", "+00:00")` for Z suffix
- Use `date()` method to compare dates without time

**Click Options:**
- Multiple `@click.option()` decorators stack
- Options can have defaults (`default=None`)
- Type validation built-in (`type=int`, `type=str`)

**pytest:**
- Use `@pytest.mark.parametrize` for testing multiple filter combinations
- Mock `_read_tracker()` to provide test fixture data

### References

- [Source: epics.md#Story 1.4: History Filtering & Pagination]
- [Source: architecture.md#Tech Stack]
- [Source: sbm/utils/tracker.py#record_run]
- [Source: sbm/utils/tracker.py#get_migration_stats]
- [Source: sbm/cli.py#stats command]
- [Source: Story 1.3: Enhanced CLI History Display (dependency)]

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

- `tests/test_history_filtering.py`
- `sbm/cli.py`
- `sbm/utils/tracker.py`
