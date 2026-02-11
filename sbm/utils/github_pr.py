"""
Centralized GitHub PR metadata management.

Single source of truth for fetching and enriching PR data across the application.
Used by: PR creation, stats sync, daily updates, and migration scripts.
"""

import json
import subprocess
import time
from typing import Optional

from .logger import logger


class GitHubPRManager:
    """Manages GitHub PR metadata fetching and enrichment."""

    @staticmethod
    def fetch_pr_metadata(pr_url: str, max_retries: int = 3) -> Optional[dict]:
        """
        Fetch PR metadata from GitHub using gh CLI with retry logic.

        This is the single source of truth for PR metadata fetching.
        Extracted from migrate_pr_timestamps.py for reusability.

        Args:
            pr_url: GitHub PR URL
            max_retries: Maximum retry attempts for transient failures

        Returns:
            dict with created_at, merged_at, closed_at, state, author or None if error
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting: sleep between requests to avoid hitting API limits
                if attempt > 0:
                    # Exponential backoff on retries: 2s, 4s, 8s
                    backoff = 2**attempt
                    logger.debug(f"Retry {attempt}/{max_retries} after {backoff}s...")
                    time.sleep(backoff)
                else:
                    # Rate limit all requests (GitHub API allows ~5000 req/hr)
                    time.sleep(0.5)

                result = subprocess.run(
                    [
                        "gh",
                        "pr",
                        "view",
                        pr_url,
                        "--json",
                        "createdAt,mergedAt,closedAt,state,author",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                data = json.loads(result.stdout)

                # Validate and extract fields
                def validate_timestamp(ts: Optional[str]) -> Optional[str]:
                    if not ts:
                        return None
                    # Basic validation: check if it looks like ISO format
                    if len(ts) >= 19 and "T" in ts:
                        return ts
                    logger.warning(f"Invalid timestamp format: {ts}")
                    return None

                # Extract author login
                author = None
                if data.get("author") and isinstance(data["author"], dict):
                    author = data["author"].get("login")

                return {
                    "created_at": validate_timestamp(data.get("createdAt")),
                    "merged_at": validate_timestamp(data.get("mergedAt")),
                    "closed_at": validate_timestamp(data.get("closedAt")),
                    "state": data.get("state"),  # OPEN, CLOSED, MERGED
                    "author": author,
                }

            except subprocess.TimeoutExpired:
                if attempt == max_retries - 1:
                    logger.warning(
                        f"Timeout fetching {pr_url} after {max_retries} attempts"
                    )
                    return None
                continue

            except subprocess.CalledProcessError as e:
                # Don't retry on 404 (PR not found) or auth errors
                stderr_str = str(e.stderr) if e.stderr else ""
                if "404" in stderr_str or "authentication" in stderr_str.lower():
                    logger.warning(f"Permanent error for {pr_url}: {stderr_str}")
                    return None
                if attempt == max_retries - 1:
                    logger.warning(
                        f"Error fetching {pr_url} after {max_retries} attempts: {stderr_str}"
                    )
                    return None
                continue

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Unexpected error for {pr_url}: {e}")
                    return None
                continue

        return None

    @staticmethod
    def fetch_pr_additions(pr_url: str, max_retries: int = 2) -> Optional[int]:
        """
        Fetch the additions count from a GitHub PR.

        This provides the GitHub-sourced line count which matches what GitHub
        displays on the PR, unlike the local SCSS line count.

        Includes retry logic because GitHub may not have computed diff stats
        immediately after PR creation.

        Args:
            pr_url: GitHub PR URL
            max_retries: Maximum retry attempts (default 2)

        Returns:
            Number of additions, or None if fetch failed
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(2**attempt)

                result = subprocess.run(
                    ["gh", "pr", "view", pr_url, "--json", "additions"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                data = json.loads(result.stdout)
                additions = data.get("additions")
                if isinstance(additions, int):
                    logger.debug(f"PR additions for {pr_url}: {additions}")
                    return additions
                # additions field missing or wrong type — retry
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.debug(f"Could not fetch PR additions for {pr_url}: {e}")
                    return None
        return None

    @staticmethod
    def enrich_run_with_pr_data(run: dict, force_refresh: bool = False) -> dict:
        """
        Add or update PR metadata fields on a run dictionary.

        This method is used to ensure runs have complete PR data:
        - When creating new runs (force_refresh=True)
        - When updating stale runs (force_refresh=True)
        - When displaying stats (force_refresh=False, only if missing)

        Args:
            run: Run dictionary (modified in place)
            force_refresh: If True, fetch from GitHub even if data exists

        Returns:
            Updated run dictionary
        """
        pr_url = run.get("pr_url")
        if not pr_url:
            return run

        # Check if we need to fetch
        needs_fetch = force_refresh or not run.get("created_at") or not run.get("pr_author")

        if not needs_fetch:
            return run

        # Fetch metadata from GitHub
        logger.debug(f"Fetching PR metadata for {pr_url}")
        metadata = GitHubPRManager.fetch_pr_metadata(pr_url)

        if metadata:
            # Update run with fetched data
            run["created_at"] = metadata["created_at"]
            run["merged_at"] = metadata["merged_at"]
            run["closed_at"] = metadata["closed_at"]
            run["pr_state"] = metadata["state"]

            # Update pr_author if available
            if metadata["author"]:
                run["pr_author"] = metadata["author"]

            logger.debug(f"Updated PR metadata for {pr_url}: {metadata['state']}")
        else:
            logger.warning(f"Failed to fetch PR metadata for {pr_url}")

        return run

    @staticmethod
    def should_refresh_pr_data(run: dict) -> bool:
        """
        Determine if a run's PR data should be refreshed.

        Refresh if:
        - PR state is OPEN (might have been merged/closed)
        - Missing created_at (incomplete data)
        - Has pr_url but no pr_state (legacy data)

        Args:
            run: Run dictionary to check

        Returns:
            True if PR data should be refreshed
        """
        pr_url = run.get("pr_url")
        if not pr_url:
            return False

        # Missing critical data
        if not run.get("created_at"):
            return True
        if not run.get("pr_author"):
            return True

        # PR is still open - might have been merged
        pr_state = run.get("pr_state", "").upper()
        if pr_state == "OPEN":
            return True

        # Has PR URL but no state (legacy data)
        if not pr_state:
            return True

        return False


# Convenience functions for backward compatibility
def fetch_pr_metadata(pr_url: str) -> Optional[dict]:
    """Fetch PR metadata from GitHub. Convenience wrapper."""
    return GitHubPRManager.fetch_pr_metadata(pr_url)


def fetch_pr_additions(pr_url: str) -> Optional[int]:
    """Fetch PR additions count from GitHub. Convenience wrapper."""
    return GitHubPRManager.fetch_pr_additions(pr_url)


def enrich_run_with_pr_data(run: dict, force_refresh: bool = False) -> dict:
    """Enrich run with PR data. Convenience wrapper."""
    return GitHubPRManager.enrich_run_with_pr_data(run, force_refresh)
