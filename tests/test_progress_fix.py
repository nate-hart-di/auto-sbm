#!/usr/bin/env python3
"""Test script to verify click.confirm visibility fix."""

import sys
import os
sys.path.insert(0, '/Users/nathanhart/auto-sbm')

# Activate the venv programmatically
import subprocess
venv_path = '/Users/nathanhart/auto-sbm/.venv'
activate_script = os.path.join(venv_path, 'bin', 'activate_this.py')

# Set up environment similar to how SBM runs
os.environ['VIRTUAL_ENV'] = venv_path
sys.path.insert(0, os.path.join(venv_path, 'lib', 'python3.13', 'site-packages'))

import click
from sbm.utils.timer import start_migration_timer, patch_click_confirm_for_timing, restore_click_confirm
from sbm.ui.progress import MigrationProgress

def test_click_in_progress_context():
    """Test click.confirm inside a progress context - this should fail in the old code"""
    print("=== Testing click.confirm inside progress context ===")
    
    # Set up timer and patching like SBM does
    timer = start_migration_timer("test-theme")
    original_confirm = patch_click_confirm_for_timing()
    
    try:
        progress_tracker = MigrationProgress(show_speed=False)
        
        # This simulates what was happening in the broken code
        with progress_tracker.progress_context():
            print("Inside progress context...")
            result = click.confirm("Can you see this prompt inside progress context?")
            print(f"Result: {result}")
            
    finally:
        restore_click_confirm(original_confirm)

def test_click_outside_progress_context():
    """Test click.confirm outside progress context - this should work"""
    print("\n=== Testing click.confirm outside progress context ===")
    
    # Set up timer and patching like SBM does
    timer = start_migration_timer("test-theme")
    original_confirm = patch_click_confirm_for_timing()
    
    try:
        progress_tracker = MigrationProgress(show_speed=False)
        
        # Run progress context but don't do interactive stuff inside it
        with progress_tracker.progress_context():
            print("Inside progress context... doing non-interactive work")
            # Simulate work
            import time
            time.sleep(0.5)
        
        # Interactive prompts outside progress context
        print("Outside progress context...")
        result = click.confirm("Can you see this prompt outside progress context?")
        print(f"Result: {result}")
        
    finally:
        restore_click_confirm(original_confirm)

if __name__ == "__main__":
    print("Testing click.confirm visibility with progress context")
    print("=" * 55)
    
    test_click_in_progress_context()
    test_click_outside_progress_context()
    
    print("\nAll tests completed!")
