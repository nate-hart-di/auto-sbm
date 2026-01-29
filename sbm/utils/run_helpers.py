"""
Shared helper functions for run filtering and classification.

This module provides a single source of truth for determining whether a run
should be counted in stats, preventing duplicate and divergent logic across
the codebase.
"""

from sbm.utils.constants import PR_STATE_MERGED, RUN_STATUS_SUCCESS


def is_complete_run(run: dict) -> bool:
    """
    Return True if a run represents a completed, non-superseded merged PR.

    A run is considered complete if:
    1. Status is "success"
    2. PR was merged (has merged_at OR pr_state is MERGED)
    3. NOT superseded by a later migration

    Args:
        run: Run dictionary with status, merged_at, pr_state, superseded fields

    Returns:
        True if run should be counted in stats, False otherwise

    Examples:
        >>> is_complete_run({"status": "success", "merged_at": "2026-01-15T10:00:00Z"})
        True

        >>> is_complete_run({"status": "success", "merged_at": "2026-01-15T10:00:00Z", "superseded": True})
        False

        >>> is_complete_run({"status": "failed", "merged_at": "2026-01-15T10:00:00Z"})
        False

        >>> is_complete_run({"status": "success", "pr_state": "OPEN"})
        False
    """
    # Exclude superseded runs (remigrations)
    if run.get("superseded"):
        return False

    # Must be successful run
    if run.get("status") != RUN_STATUS_SUCCESS:
        return False

    # Must have been merged
    if run.get("merged_at"):
        return True

    return run.get("pr_state", "").upper() == PR_STATE_MERGED
