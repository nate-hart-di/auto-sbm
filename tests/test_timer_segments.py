#!/usr/bin/env python3
"""Test script to verify timer segment functionality."""

import time

from sbm.utils.timer import finish_migration_timer, start_migration_timer, timer_segment


def test_timer_segments():
    """Test that timer segments are tracked correctly."""
    print("Testing timer segments...")

    # Start migration timer
    timer = start_migration_timer("test-theme")

    # Test individual segments
    with timer_segment("Test Operation 1"):
        time.sleep(0.1)  # Simulate work

    with timer_segment("Test Operation 2"):
        time.sleep(0.05)  # Simulate work

    with timer_segment("Test Operation 3"):
        time.sleep(0.03)  # Simulate work

    # Finish and print summary
    finish_migration_timer()

    print("\nTimer segments test completed!")


if __name__ == "__main__":
    test_timer_segments()
