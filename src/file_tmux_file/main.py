"""CLI entry point and main loop."""

import argparse
import atexit
import fcntl
import os
import sys
import time
from pathlib import Path

from .tmux import list_panes
from .snapshot import write_snapshot, get_pane_dir
from .input_queue import process_input_queue
from .cleanup import cleanup_stale


def acquire_lock(output_dir: Path) -> int:
    """Acquire exclusive lock to prevent multiple instances. Returns fd."""
    lock_file = output_dir / ".lock"
    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        print(f"Error: Another instance is already running (lockfile: {lock_file})", file=sys.stderr)
        sys.exit(1)
    # Write PID to lock file
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    return fd


def release_lock(fd: int) -> None:
    """Release the lock."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Continuous tmux snapshot and input queue tool"
    )
    parser.add_argument(
        "-d", "--dir",
        type=Path,
        default=Path("tmux"),
        help="Output directory (default: ./tmux)"
    )
    parser.add_argument(
        "-s", "--scrollback",
        type=int,
        default=500,
        help="Lines of scrollback to capture (default: 500)"
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=500,
        help="Poll interval in milliseconds (default: 500)"
    )

    args = parser.parse_args()
    output_dir: Path = args.dir
    scrollback: int = args.scrollback
    interval_sec: float = args.interval / 1000.0

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Acquire lock to prevent multiple instances
    lock_fd = acquire_lock(output_dir)
    atexit.register(release_lock, lock_fd)

    print(f"file-tmux-file running: dir={output_dir}, scrollback={scrollback}, interval={args.interval}ms")
    print("Press Ctrl+C to stop")

    try:
        while True:
            # Get current panes
            panes = list_panes()

            # Snapshot each pane and process input queues
            for pane in panes:
                pane_dir = write_snapshot(pane, output_dir, scrollback)
                input_file = pane_dir / "input.txt"
                process_input_queue(pane.pane_id, input_file)

            # Cleanup stale directories
            cleanup_stale(output_dir, panes)

            # Sleep
            time.sleep(interval_sec)

    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
