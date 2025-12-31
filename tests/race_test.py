#!/usr/bin/env python3
"""
Race condition tests for file-tmux-file.

Tests scenarios where panes/windows change during operation.

Usage:
    python race_test.py <output_dir>

Tests:
    pane_close_pending  - Close pane with pending input
    rapid_create_close  - Rapidly create and close panes
    rename_during_poll  - Rename session while running
    all                 - Run all tests
"""

import subprocess
import sys
import time
from pathlib import Path


def run_tmux(cmd: str) -> str:
    """Run a tmux command and return output."""
    result = subprocess.run(
        ["tmux"] + cmd.split(),
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def test_pane_close_pending(output_dir: Path):
    """Create pane, queue input, close pane before processing."""
    print("=== PANE CLOSE WITH PENDING INPUT ===")

    # Create a new window
    run_tmux("new-window -n race-test-1")
    time.sleep(1.5)  # Wait for snapshot to pick it up

    # Find the pane dir
    pane_dirs = list(output_dir.glob("*/*/race-test-1/../*"))
    if not pane_dirs:
        # Try finding by window name in content
        for session_dir in output_dir.iterdir():
            if not session_dir.is_dir():
                continue
            for window_dir in session_dir.iterdir():
                if not window_dir.is_dir():
                    continue
                for pane_dir in window_dir.iterdir():
                    content = pane_dir / "content.txt"
                    if content.exists() and "race-test-1" in content.read_text():
                        pane_dirs = [pane_dir]
                        break

    if not pane_dirs:
        print("  Could not find race-test-1 pane dir, trying generic approach...")
        # Just use the newest window dir
        all_dirs = sorted(output_dir.glob("*/*/*"), key=lambda p: p.stat().st_mtime)
        if all_dirs:
            pane_dirs = [all_dirs[-1]]

    if pane_dirs:
        input_file = pane_dirs[0] / "input.txt"
        print(f"  Writing pending input to {input_file}")
        input_file.write_text("This message should never be delivered\n")

        # Immediately close the window
        run_tmux("kill-window -t race-test-1")
        print("  Closed window immediately after queueing input")

        # Wait and check cleanup
        time.sleep(2)

        if pane_dirs[0].exists():
            print("  FAIL: Pane directory still exists after close")
        else:
            print("  PASS: Pane directory was cleaned up")
    else:
        print("  SKIP: Could not locate pane directory")


def test_rapid_create_close(output_dir: Path):
    """Rapidly create and close windows to stress cleanup."""
    print("=== RAPID CREATE/CLOSE ===")

    for i in range(10):
        window_name = f"rapid-{i}"
        run_tmux(f"new-window -n {window_name}")
        time.sleep(0.1)  # Tiny delay
        run_tmux(f"kill-window -t {window_name}")
        print(f"  Created and killed window {i+1}/10")

    time.sleep(2)  # Let cleanup run

    # Check for any stale rapid-* dirs
    stale = list(output_dir.glob("*/*/rapid-*"))
    if stale:
        print(f"  WARN: Found {len(stale)} stale directories")
    else:
        print("  PASS: No stale directories found")


def test_many_panes(output_dir: Path):
    """Create many panes and verify all are captured."""
    print("=== MANY PANES TEST ===")

    # Create a window with multiple panes
    run_tmux("new-window -n many-panes")
    time.sleep(0.5)

    # Split into 4 panes
    for _ in range(3):
        run_tmux("split-window -t many-panes")
        time.sleep(0.2)

    run_tmux("select-layout -t many-panes tiled")
    time.sleep(2)  # Let snapshots happen

    # Check that all panes were captured
    pane_count = 0
    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir():
            continue
        for window_dir in session_dir.iterdir():
            if not window_dir.is_dir():
                continue
            for pane_dir in window_dir.iterdir():
                content = pane_dir / "content.txt"
                if content.exists() and "many-panes" in content.read_text():
                    pane_count += 1

    print(f"  Found {pane_count} panes for many-panes window")
    if pane_count >= 4:
        print("  PASS: All panes captured")
    else:
        print("  WARN: Expected 4 panes")

    # Cleanup
    run_tmux("kill-window -t many-panes")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    test_name = sys.argv[2] if len(sys.argv) > 2 else "all"

    if not output_dir.exists():
        print(f"Error: Output directory {output_dir} does not exist")
        sys.exit(1)

    tests = {
        'pane_close_pending': test_pane_close_pending,
        'rapid_create_close': test_rapid_create_close,
        'many_panes': test_many_panes,
    }

    if test_name == 'all':
        for name, test_func in tests.items():
            print()
            try:
                test_func(output_dir)
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(1)
    elif test_name in tests:
        tests[test_name](output_dir)
    else:
        print(f"Unknown test: {test_name}")
        print(f"Available: {', '.join(tests.keys())}, all")
        sys.exit(1)


if __name__ == '__main__':
    main()
