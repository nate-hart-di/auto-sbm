"""
Command execution utility for the SBM tool.

This module provides functions for executing shell commands with proper error handling
and real-time output.
"""

import subprocess
import threading
import os
import logging

logger = logging.getLogger(__name__)


def execute_interactive_command(command, error_message="Command failed", cwd=None, suppress_output=False, progress_tracker=None, task_id=None):
    """
    Execute an interactive shell command that may require user input.
    This allows commands like 'just start' to prompt for passwords and receive input.
    
    Args:
        command (str): Command to execute
        error_message (str): Message to display on error
        cwd (str, optional): The working directory for the command. Defaults to None.
        suppress_output (bool): Whether to suppress verbose output (default: False)
        progress_tracker: Optional Rich progress tracker
        task_id: Optional task ID for progress updates
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not suppress_output:
            print(f"Executing interactive command: {command}")
        
        if suppress_output and progress_tracker and task_id:
            # Run with output suppression and progress updates
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Monitor process while updating progress
            import time
            import select
            import sys
            
            while process.poll() is None:
                # Update progress periodically
                if progress_tracker and task_id:
                    progress_tracker.update_indeterminate_task(task_id, "Building Docker containers...")
                
                # Check for AWS/interactive prompts in output (Unix systems only)
                try:
                    if hasattr(select, 'select'):  # Unix systems
                        ready, _, _ = select.select([process.stdout], [], [], 0.1)
                        if ready:
                            line = process.stdout.readline()
                            if line and any(keyword in line.lower() for keyword in ['password', 'login', 'credentials', 'aws', 'mfa']):
                                # Interactive prompt detected - switch to interactive mode
                                print(f"\n🔐 Authentication required for: {command}")
                                print("Switching to interactive mode...")
                                process.terminate()
                                return execute_interactive_command(command, error_message, cwd, suppress_output=False)
                except (ImportError, OSError):
                    # Fall back to basic monitoring on systems without select
                    pass
                
                time.sleep(0.5)
            
            result_code = process.wait()
        else:
            # Standard interactive execution
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                # Don't redirect stdin/stdout/stderr - let the command interact directly with terminal
            )
            result_code = result.returncode
        
        if result_code != 0:
            logger.error(f"{error_message} (exit code: {result_code})")
            return False
            
        return True
        
    except KeyboardInterrupt:
        print("\nCommand interrupted by user.")
        return False
    except FileNotFoundError:
        logger.error(f"Command not found: {command.split()[0]}")
        return False
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return False


def execute_command(command, error_message="Command failed", wait_for_completion=True, cwd=None):
    """
    Execute a shell command and handle errors.
    Show real-time output to the user.
    
    Args:
        command (str): Command to execute
        error_message (str): Message to display on error
        wait_for_completion (bool): If True, waits for the command to complete. If False, runs in background.
        cwd (str, optional): The working directory for the command. Defaults to None.
        
    Returns:
        tuple: (bool, list[str], list[str], subprocess.Popen or None) - 
               (True if successful, stdout lines, stderr lines, process object if not waiting)
    """
    stdout_output = []
    stderr_output = []
    process = None
    try:
        print(f"Executing: {command}")
        
        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd
        )
        
        # Threads to read stdout and stderr
        def read_pipe(pipe, output_list):
            for line in iter(pipe.readline, ''):
                print(line, end='')
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
                raise subprocess.CalledProcessError(process.returncode, command, "".join(stdout_output), "".join(stderr_output))
            
            return True, stdout_output, stderr_output, None
        else:
            # For background processes, return immediately with the process object
            return True, stdout_output, stderr_output, process
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}")
        logger.error(f"Error output:\n{e.stderr}")
        return False, stdout_output, stderr_output, None
    except KeyboardInterrupt:
        print("\nCommand interrupted by user.")
        if process:
            process.terminate()
            process.wait()
        return False, stdout_output, stderr_output, None
    except FileNotFoundError:
        logger.error(f"Command not found: {command.split()[0]}")
        return False, stdout_output, stderr_output, None
