"""
Command execution utilities for the SBM tool.

This module provides functions for executing shell commands with proper error handling
and real-time output.
"""

import subprocess
import threading


def execute_command(command, error_message="Command failed"):
    """
    Execute a shell command and handle errors.
    Show real-time output to the user.
    
    Args:
        command (str): Command to execute
        error_message (str): Message to display on error
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Executing: {command}")
        
        # Use subprocess.Popen with real-time output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Define functions to read from stdout and stderr to prevent deadlocks
        def read_output(pipe, prefix=''):
            for line in iter(pipe.readline, ''):
                print(f"{prefix}{line}", end='')
        
        # Create threads for reading stdout and stderr
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, ''))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, ''))
        
        # Start the threads
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for the command to complete
        exit_code = process.wait()
        
        # Wait for the threads to finish
        stdout_thread.join()
        stderr_thread.join()
        
        if exit_code != 0:
            print(f"ERROR: {error_message} (exit code: {exit_code})")
            return False
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {error_message}")
        print(f"Command output: {e.stderr}")
        return False
    except KeyboardInterrupt:
        print("\nCommand interrupted by user.")
        return False 
