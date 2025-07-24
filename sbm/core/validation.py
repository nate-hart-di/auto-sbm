"""
Validation module for the SBM tool.

This module provides validation functions for PHP and other files,
as well as compilation status tracking for accurate reporting.
"""

import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from sbm.utils.logger import logger


class CompilationStatus(Enum):
    """Enumeration of compilation status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class CompilationAttempt:
    """Data class representing a single compilation attempt."""
    attempt_number: int
    timestamp: float
    status: CompilationStatus
    errors: list[str]
    warnings: list[str]
    duration: Optional[float] = None
    error_types: Optional[list[str]] = None


class CompilationValidator:
    """
    Track and validate compilation attempts for accurate status reporting.

    This class separates retry attempts from final compilation status,
    ensuring we only report the true final outcome of compilation processes.
    """

    def __init__(self) -> None:
        """Initialize compilation validator."""
        self._compilation_history: list[CompilationAttempt] = []
        self._final_state: Optional[CompilationStatus] = None
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

    def start_compilation_tracking(self) -> None:
        """Begin tracking a new compilation process."""
        self._start_time = time.time()
        self._final_state = None
        self._compilation_history.clear()
        logger.debug("Started compilation status tracking")

    def track_compilation_attempt(
        self,
        attempt: int,
        status: CompilationStatus,
        errors: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        error_types: Optional[list[str]] = None
    ) -> None:
        """
        Track a single compilation attempt.

        Args:
            attempt: Attempt number (1-based)
            status: Current compilation status
            errors: List of error messages
            warnings: List of warning messages
            error_types: List of error types for categorization
        """
        current_time = time.time()
        duration = None

        if self._compilation_history:
            # Calculate duration since last attempt
            last_attempt = self._compilation_history[-1]
            duration = current_time - last_attempt.timestamp

        compilation_attempt = CompilationAttempt(
            attempt_number=attempt,
            timestamp=current_time,
            status=status,
            errors=errors or [],
            warnings=warnings or [],
            duration=duration,
            error_types=error_types or []
        )

        self._compilation_history.append(compilation_attempt)
        logger.debug(f"Tracked compilation attempt {attempt}: {status.value}")

        # Update final state logic
        if status in [CompilationStatus.SUCCESS, CompilationStatus.FAILED]:
            self._final_state = status
            self._end_time = current_time

    def get_final_status(self) -> Optional[CompilationStatus]:
        """
        Get the true final compilation status.

        Returns:
            Final compilation status or None if still in progress
        """
        return self._final_state

    def is_compilation_successful(self) -> bool:
        """
        Check if compilation ultimately succeeded.

        Returns:
            True if final status is success, False otherwise
        """
        return self._final_state == CompilationStatus.SUCCESS

    def get_attempt_count(self) -> int:
        """Get total number of compilation attempts."""
        return len(self._compilation_history)

    def get_retry_count(self) -> int:
        """Get number of retry attempts (excluding first attempt)."""
        return max(0, len(self._compilation_history) - 1)

    def get_compilation_summary(self) -> dict[str, Any]:
        """
        Get comprehensive compilation summary.

        Returns:
            Dictionary with compilation statistics and history
        """
        if not self._compilation_history:
            return {
                "status": "not_started",
                "attempts": 0,
                "retries": 0,
                "duration": 0.0,
                "final_status": None
            }

        total_duration = 0.0
        if self._start_time:
            end_time = self._end_time or time.time()
            total_duration = end_time - self._start_time

        # Count error types across all attempts
        all_error_types = set()
        total_errors = 0
        total_warnings = 0

        for attempt in self._compilation_history:
            all_error_types.update(attempt.error_types or [])
            total_errors += len(attempt.errors)
            total_warnings += len(attempt.warnings)

        return {
            "status": self._final_state.value if self._final_state else "in_progress",
            "attempts": len(self._compilation_history),
            "retries": self.get_retry_count(),
            "duration": total_duration,
            "final_status": self._final_state,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "error_types": list(all_error_types),
            "success": self.is_compilation_successful()
        }

    def get_last_attempt(self) -> Optional[CompilationAttempt]:
        """Get the most recent compilation attempt."""
        return self._compilation_history[-1] if self._compilation_history else None

    def reset(self) -> None:
        """Reset compilation tracking for a new process."""
        self._compilation_history.clear()
        self._final_state = None
        self._start_time = None
        self._end_time = None


def validate_php_syntax(file_path: str) -> bool:
    """
    Validate PHP syntax in a file.

    Args:
        file_path (str): Path to the PHP file

    Returns:
        bool: True if syntax is valid, False otherwise
    """
    file_path_obj = Path(file_path)
    logger.info(f"Validating PHP syntax for {file_path_obj.name}")

    if not file_path_obj.exists():
        logger.error(f"File not found: {file_path}")
        return False

    # First check brace count
    with file_path_obj.open(encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Count braces
    opening_count = content.count("{")
    closing_count = content.count("}")

    logger.info(f"PHP brace count: {opening_count} opening, {closing_count} closing")

    if opening_count != closing_count:
        logger.warning(
            f"Unbalanced braces in {os.path.basename(file_path)}: "
            f"{opening_count} opening, {closing_count} closing"
        )

        # If we have more opening than closing braces, try to fix it
        if opening_count > closing_count:
            missing = opening_count - closing_count
            logger.info(f"Adding {missing} missing closing braces")

            # Create a backup
            backup_path = Path(f"{file_path}.bak")
            with backup_path.open("w") as f:
                f.write(content)

            # Add missing closing braces
            with file_path_obj.open("w") as f:
                f.write(content + "\n" + "}" * missing + "\n?>")

            logger.info(f"Fixed PHP file by adding {missing} closing braces")

    # If php command is available, use it for syntax validation
    try:
        result = subprocess.run(
            f"php -l {file_path}", check=False, shell=True, capture_output=True, text=True
        )

        if "No syntax errors detected" in result.stdout:
            logger.info(f"PHP syntax validation passed for {os.path.basename(file_path)}")
            return True
        logger.error(
            f"PHP syntax validation failed for {os.path.basename(file_path)}: {result.stderr}"
        )
        return False

    except Exception as e:
        logger.warning(f"Could not run PHP syntax check (php -l): {e}")
        logger.info("Skipping PHP syntax validation, only brace count was checked")

        # Return True if braces are balanced (or were fixed)
        return opening_count == closing_count or opening_count > closing_count


def validate_theme_files(slug: str, theme_dir: str) -> bool:
    """
    Validate important files in a dealer theme.

    Args:
        slug (str): Dealer theme slug
        theme_dir (str): Path to the dealer theme directory

    Returns:
        bool: True if all validations pass, False otherwise
    """
    logger.info(f"Validating theme files for {slug}")

    success = True

    theme_dir_path = Path(theme_dir)
    
    # Validate functions.php if it exists
    functions_php = theme_dir_path / "functions.php"
    if functions_php.exists() and not validate_php_syntax(str(functions_php)):
        logger.error(f"functions.php validation failed for {slug}")
        success = False

    # Validate header.php if it exists
    header_php = theme_dir_path / "header.php"
    if header_php.exists() and not validate_php_syntax(str(header_php)):
        logger.error(f"header.php validation failed for {slug}")
        success = False

    # Validate footer.php if it exists
    footer_php = theme_dir_path / "footer.php"
    if footer_php.exists() and not validate_php_syntax(str(footer_php)):
        logger.error(f"footer.php validation failed for {slug}")
        success = False

    # Validate Site Builder files
    sb_files = ["sb-inside.scss", "sb-home.scss", "sb-vdp.scss", "sb-vrp.scss"]

    from sbm.scss.validator import validate_scss_syntax

    for file in sb_files:
        file_path = theme_dir_path / file
        if file_path.exists() and not validate_scss_syntax(str(file_path)):
            logger.error(f"{file} validation failed for {slug}")
            success = False

    return success
