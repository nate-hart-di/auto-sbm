"""
Status constants for PR states, completion states, and run status.

These constants provide a single source of truth for all status strings
used throughout the codebase, preventing typo bugs and inconsistencies.
"""

# PR States (from GitHub API)
PR_STATE_OPEN = "OPEN"
PR_STATE_MERGED = "MERGED"
PR_STATE_CLOSED = "CLOSED"

# Completion States (internal classification)
COMPLETION_COMPLETE = "complete"
COMPLETION_IN_REVIEW = "in_review"
COMPLETION_CLOSED = "closed"
COMPLETION_SUPERSEDED = "superseded"
COMPLETION_UNKNOWN = "unknown"

# Run Status
RUN_STATUS_SUCCESS = "success"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_INVALID = "invalid"
