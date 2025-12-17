"""
Process management utilities for SBM.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .logger import logger

# Project root for CWD resolution
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()


def run_background_task(cmd_list: list[str]) -> None:
    """
    Fire-and-forget background process.
    Spawns a new process that is decoupled from the current terminal session.
    
    Args:
        cmd_list: Command to run as a list of strings
    """
    try:
        # Use subprocess.DEVNULL to avoid file descriptor leaks
        # We don't need to manually open/close os.devnull
        subprocess.Popen(
            cmd_list,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            # Unix-specific: detach from controlling terminal
            start_new_session=True,
            # Close file descriptors to avoid leaking them to child
            close_fds=True
        )
    except Exception as e:
        logger.debug(f"Failed to spawn background task: {e}")
