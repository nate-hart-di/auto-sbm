"""
Subprocess UI integration for the SBM CLI tool.

This module provides high-level interfaces for tracking subprocess operations
with Rich UI integration, building on the enhanced MigrationProgress class.
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .console import get_console
from .progress import MigrationProgress

logger = logging.getLogger(__name__)


@dataclass
class SubprocessResult:
    """Result of a tracked subprocess operation."""

    success: bool
    returncode: int
    duration: float
    stdout_lines: List[str]
    stderr_lines: List[str]
    task_id: Optional[int] = None


class SubprocessTracker:
    """
    High-level subprocess tracking with Rich UI integration.

    This class provides a convenient interface for running subprocess operations
    with real-time progress tracking and Rich UI feedback.
    """

    def __init__(self, progress_tracker: Optional[MigrationProgress] = None):
        """
        Initialize subprocess tracker.

        Args:
            progress_tracker: Optional MigrationProgress instance for tracking
        """
        self.progress_tracker = progress_tracker
        self.console = get_console()
        self.active_tasks: Dict[str, int] = {}

    def track_command(
        self,
        command: List[str],
        description: str,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        output_processor: Optional[Callable[[str], None]] = None,
    ) -> SubprocessResult:
        """
        Track a subprocess command with Rich UI progress.

        Args:
            command: Command list to execute
            description: Description for progress display
            cwd: Working directory for command
            timeout: Maximum time to wait for completion
            output_processor: Optional function to process output lines

        Returns:
            SubprocessResult with execution details
        """
        start_time = time.time()

        if self.progress_tracker:
            # Use enhanced progress tracking
            task_id = self.progress_tracker.track_subprocess(
                command=command,
                description=description,
                cwd=cwd,
                progress_callback=output_processor,
            )

            # Wait for completion
            success = self.progress_tracker.wait_for_subprocess_completion(timeout=timeout)

            duration = time.time() - start_time

            return SubprocessResult(
                success=success,
                returncode=0 if success else 1,
                duration=duration,
                stdout_lines=[],  # Lines are processed via callback
                stderr_lines=[],
                task_id=task_id,
            )
        # Fallback to direct execution
        return self._execute_direct(command, description, cwd, timeout, output_processor)

    def track_docker_startup(self, theme_slug: str, timeout: float = 300.0) -> SubprocessResult:
        """
        Track Docker startup with specialized progress monitoring.

        Args:
            theme_slug: Theme slug for Docker startup
            timeout: Maximum time to wait for startup

        Returns:
            SubprocessResult with Docker startup details
        """

        def docker_output_processor(line: str):
            """Process Docker output for meaningful progress updates."""
            line_lower = line.strip().lower()

            if "pulling" in line_lower and "image" in line_lower:
                self.console.print_docker_status("Pulling Docker image...")
            elif "creating" in line_lower and "container" in line_lower:
                self.console.print_docker_status("Creating containers...")
            elif "starting" in line_lower:
                self.console.print_docker_status("Starting services...")
            elif "ready" in line_lower or "listening" in line_lower:
                self.console.print_docker_status("Services are ready")

        return self.track_command(
            command=["just", "start", theme_slug, "prod"],
            description=f"Starting Docker environment for {theme_slug}",
            timeout=timeout,
            output_processor=docker_output_processor,
        )

    def track_aws_authentication(
        self,
        account_profile: str = "inventory-non-prod-423154430651-developer",
        timeout: float = 120.0,
    ) -> SubprocessResult:
        """
        Track AWS SAML authentication with specialized progress monitoring.

        Args:
            account_profile: AWS account profile for authentication
            timeout: Maximum time to wait for authentication

        Returns:
            SubprocessResult with AWS authentication details
        """

        def aws_output_processor(line: str):
            """Process AWS output for meaningful progress updates."""
            line_lower = line.strip().lower()

            if "please authenticate" in line_lower:
                self.console.print_aws_status("Opening browser for authentication...")
            elif "authentication successful" in line_lower:
                self.console.print_aws_status("Authentication successful")
            elif "retrieving" in line_lower and "token" in line_lower:
                self.console.print_aws_status("Retrieving session tokens...")
            elif "assuming role" in line_lower:
                self.console.print_aws_status("Assuming AWS role...")
            elif "credentials saved" in line_lower:
                self.console.print_aws_status("Credentials configured")

        return self.track_command(
            command=["saml2aws", "login", "-a", account_profile],
            description="AWS SAML authentication",
            timeout=timeout,
            output_processor=aws_output_processor,
        )

    def track_git_operation(
        self, git_command: List[str], description: str, timeout: float = 60.0
    ) -> SubprocessResult:
        """
        Track Git operations with specialized progress monitoring.

        Args:
            git_command: Git command list (e.g., ["git", "clone", "..."])
            description: Description for progress display
            timeout: Maximum time to wait for completion

        Returns:
            SubprocessResult with Git operation details
        """

        def git_output_processor(line: str):
            """Process Git output for meaningful progress updates."""
            line_lower = line.strip().lower()

            if "cloning" in line_lower:
                self.console.print_status("Cloning repository...", "git")
            elif "receiving objects" in line_lower:
                self.console.print_status("Downloading objects...", "git")
            elif "resolving deltas" in line_lower:
                self.console.print_status("Processing changes...", "git")
            elif "checkout" in line_lower or "switched to" in line_lower:
                self.console.print_status("Switching branch...", "git")

        return self.track_command(
            command=git_command,
            description=description,
            timeout=timeout,
            output_processor=git_output_processor,
        )

    def _execute_direct(
        self,
        command: List[str],
        description: str,
        cwd: Optional[str],
        timeout: Optional[float],
        output_processor: Optional[Callable[[str], None]],
    ) -> SubprocessResult:
        """
        Direct subprocess execution fallback without Rich progress tracking.

        Args:
            command: Command list to execute
            description: Description for logging
            cwd: Working directory
            timeout: Execution timeout
            output_processor: Optional output processor

        Returns:
            SubprocessResult with execution details
        """
        import subprocess

        start_time = time.time()

        try:
            self.console.print_info(f"Executing: {description}")

            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd
            )

            stdout_lines = []
            stderr_lines = []

            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break

                if output:
                    line = output.strip()
                    stdout_lines.append(line)

                    if output_processor:
                        output_processor(line)

            # Get remaining stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                stderr_lines = stderr_output.strip().split("\n")

            returncode = process.wait()
            duration = time.time() - start_time

            success = returncode == 0

            if success:
                self.console.print_success(f"{description} completed")
            else:
                self.console.print_error(f"{description} failed (exit code: {returncode})")

            return SubprocessResult(
                success=success,
                returncode=returncode,
                duration=duration,
                stdout_lines=stdout_lines,
                stderr_lines=stderr_lines,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.console.print_error(f"{description} error: {e!s}")

            return SubprocessResult(
                success=False,
                returncode=-1,
                duration=duration,
                stdout_lines=[],
                stderr_lines=[str(e)],
            )


def create_subprocess_tracker(
    progress_tracker: Optional[MigrationProgress] = None,
) -> SubprocessTracker:
    """
    Factory function to create a subprocess tracker.

    Args:
        progress_tracker: Optional MigrationProgress instance

    Returns:
        Configured SubprocessTracker instance
    """
    return SubprocessTracker(progress_tracker)
