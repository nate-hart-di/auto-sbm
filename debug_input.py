#!/usr/bin/env python3
"""Debug script to test input visibility issues."""

import click
import sys
import os

# Add the sbm package to path
sys.path.insert(0, '/Users/nathanhart/auto-sbm')

from sbm.utils.timer import patch_click_confirm_for_timing, restore_click_confirm

def test_normal_click():
    """Test normal click.confirm"""
    print("=== Testing normal click.confirm ===")
    result = click.confirm("This is a normal click.confirm - can you see this prompt?")
    print(f"Result: {result}")

def test_patched_click():
    """Test patched click.confirm"""
    print("\n=== Testing patched click.confirm ===")
    
    # Start a timer and patch click.confirm
    from sbm.utils.timer import start_migration_timer
    timer = start_migration_timer("debug-test")
    
    original_confirm = patch_click_confirm_for_timing()
    
    try:
        result = click.confirm("This is a patched click.confirm - can you see this prompt?")
        print(f"Result: {result}")
    finally:
        restore_click_confirm(original_confirm)

def test_manual_confirm():
    """Test manual input"""
    print("\n=== Testing manual input ===")
    try:
        response = input("Manual input test - can you see this prompt? (y/n): ")
        print(f"You entered: {response}")
    except KeyboardInterrupt:
        print("\nInterrupted")

if __name__ == "__main__":
    print("Input visibility debug test")
    print("=" * 40)
    
    test_normal_click()
    test_patched_click() 
    test_manual_confirm()
    
    print("\nAll tests completed!")
