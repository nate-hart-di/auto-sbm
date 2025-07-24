"""
Command execution utility for the SBM tool.

This module provides functions for executing shell commands with proper error handling
and real-time output.
"""

import logging
import subprocess
import threading
from typing import Optional, TextIO

logger = logging.getLogger(__name__)


def execute_interactive_command(
    command: str,
    error_message: str = "Command failed",
    cwd: Optional[str] = None,
    suppress_output: bool = False,
) -> Optional[bool]:
    """
    Execute an interactive shell command that may require user input.
    This allows commands like 'just start' to prompt for passwords and receive input.

    Args:
        command (str): Command to execute
        error_message (str): Message to display on error
        cwd (str, optional): The working directory for the command. Defaults to None.
        suppress_output (bool): Whether to suppress verbose output (default: False)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not suppress_output:
            pass

        if suppress_output:
            # Simple suppressed execution
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            result_code = process.wait()
        else:
            # Standard interactive execution with full output
            result = subprocess.run(
                command,
                check=False,
                shell=True,
                cwd=cwd,
                # Don't redirect stdin/stdout/stderr - let the command interact
                # directly with terminal
            )
            result_code = result.returncode

        if result_code != 0:
            logger.error("%s (exit code: %s)", error_message, result_code)
            return False

        return True

    except KeyboardInterrupt:
        return False
    except FileNotFoundError:
        logger.exception("Command not found: %s", command.split()[0])
        return False
    except Exception as e:
        logger.exception("Command execution failed: %s", e)
        return False


def execute_command(
    command: str,
    _error_message: str = "Command failed",
    wait_for_completion: bool = True,
    cwd: Optional[str] = None,
) -> tuple[bool, list[str], list[str], Optional[subprocess.Popen[str]]]:
    """
    Execute a shell command and handle errors.
    Show real-time output to the user.

    Args:
        command (str): Command to execute
        error_message (str): Message to display on error
        wait_for_completion (bool): If True, waits for the command to complete.
            If False, runs in background.
        cwd (str, optional): The working directory for the command. Defaults to None.

    Returns:
        tuple: (bool, list[str], list[str], subprocess.Popen or None) -
               (True if successful, stdout lines, stderr lines, process object if not waiting)
    """
    stdout_output = []
    stderr_output = []
    process = None
    try:

        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
        )

        # Threads to read stdout and stderr
        def read_pipe(pipe: TextIO, output_list: list[str]) -> None:
            for line in iter(pipe.readline, ""):
                output_list.append(line)
            pipe.close()

        stdout_thread = threading.Thread(target=read_pipe, args=(process.stdout, stdout_output))
        stderr_thread = threading.Thread(target=read_pipe, args=(process.stderr, stderr_output))

        stdout_thread.start()
        stderr_thread.start()

        if wait_for_completion:
            stdout_thread.join()
            stderr_thread.join()
            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, command, "".join(stdout_output), "".join(stderr_output)
                )

            return True, stdout_output, stderr_output, None
        # For background processes, return immediately with the process object
        return True, stdout_output, stderr_output, process

    except subprocess.CalledProcessError as e:
        logger.exception("Command failed: %s", command)
        logger.exception("Error output:\n%s", e.stderr)
        return False, stdout_output, stderr_output, None
    except KeyboardInterrupt:
        if process:
            process.terminate()
            process.wait()
        return False, stdout_output, stderr_output, None
    except FileNotFoundError:
        logger.exception("Command not found: %s", command.split()[0])
        return False, stdout_output, stderr_output, None
