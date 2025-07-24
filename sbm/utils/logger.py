"""
Logging utilities for the SBM tool.

This module provides a centralized logging system for the SBM tool with Rich support.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any


def setup_logger(
    name: Optional[str] = None,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    use_rich: bool = True
) -> logging.Logger:
    """
    Set up and configure a logger instance with Rich support.

    Args:
        name (str, optional): Logger name. Defaults to 'sbm'.
        log_file (str, optional): Path to log file. If None, a default path is used.
        level (int, optional): Logging level. Defaults to logging.INFO.
        use_rich (bool, optional): Whether to use Rich logging handler. Defaults to True.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger name if not provided
    if name is None:
        name = "sbm"

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Handlers should only be attached to the main 'sbm' logger.
    # Child loggers will propagate messages to the main logger.
    main_logger = logging.getLogger("sbm")
    if name == "sbm" and not main_logger.handlers:
        # Create formatter for file handler
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Create console handler (Rich or standard based on use_rich parameter)
        if use_rich and not _is_ci_environment():
            try:
                from rich.logging import RichHandler

                console_handler = RichHandler(
                    rich_tracebacks=True,
                    markup=True,
                    show_path=False,
                    show_time=False,  # Rich handles time display
                    tracebacks_suppress=[
                        "click",  # Suppress Click framework tracebacks
                        "rich",  # Suppress Rich internal tracebacks
                    ],
                )
            except ImportError:
                # Fallback to standard handler if Rich is not available
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
        else:
            # Use standard console handler for CI environments or when Rich is disabled
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)

        main_logger.addHandler(console_handler)

        # Create file handler if a log file is specified or use default
        if log_file is None:
            # Create logs directory if it doesn't exist
            log_dir = Path(__file__).parent.parent.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            # Default log file name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = str(log_dir / f"sbm_{timestamp}.log")

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        main_logger.addHandler(file_handler)

    return logger


def _is_ci_environment() -> bool:
    """
    Check if running in CI/CD environment.

    Returns:
        True if in CI environment, False otherwise
    """
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "TRAVIS",
        "CIRCLECI",
        "JENKINS_URL",
        "GITLAB_CI",
    ]

    return any(os.getenv(var) for var in ci_indicators) or os.getenv("TERM") == "dumb"


def get_rich_logger(name: Optional[str] = None, config: Optional[Any] = None) -> logging.Logger:
    """
    Get a Rich-enhanced logger with configuration support.

    Args:
        name: Logger name (defaults to 'sbm')
        config: Optional Config object for Rich settings

    Returns:
        Configured logger instance
    """
    use_rich = True
    if config:
        use_rich = config.get_setting("ui", {}).get("use_rich", True)

    return setup_logger(name=name, use_rich=use_rich)


# Create a default logger for the entire package
logger = setup_logger()
