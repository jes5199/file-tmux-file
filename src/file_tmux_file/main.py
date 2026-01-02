"""CLI entry point and main loop."""

import argparse
import atexit
import fcntl
import os
import sys
import time
from pathlib import Path

from .tmux import list_panes, sanitize_name
from .snapshot import write_snapshot
from .input_queue import process_input_queue
from .cleanup import (
    cleanup_stale,
    migrate_old_format,
    load_window_mapping,
    save_window_mapping,
    get_or_create_window_dir,
)


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

    # Run migration on first iteration
    needs_migration = True

    # Session mappings: session_name -> {window_id -> dir_name}
    session_mappings: dict[str, dict[str, str]] = {}

    try:
        while True:
            # Get current panes
            panes = list_panes()

            # Run migration on startup (converts old numeric dirs to new format)
            if needs_migration:
                session_mappings = migrate_old_format(output_dir, panes)
                needs_migration = False

            # Group panes by session for efficient processing
            panes_by_session: dict[str, list] = {}
            for pane in panes:
                if pane.session not in panes_by_session:
                    panes_by_session[pane.session] = []
                panes_by_session[pane.session].append(pane)

            # Process each session
            mappings_changed: dict[str, bool] = {}

            for session_name, session_panes in panes_by_session.items():
                session_dir = output_dir / sanitize_name(session_name)
                session_dir.mkdir(parents=True, exist_ok=True)

                # Load mapping if not already loaded
                if session_name not in session_mappings:
                    session_mappings[session_name] = load_window_mapping(session_dir)

                mapping = session_mappings[session_name]
                session_changed = False

                # Process each pane in this session
                for pane in session_panes:
                    # Get or create window directory, handling renames
                    window_dir_name, changed = get_or_create_window_dir(pane, output_dir, mapping)
                    if changed:
                        session_changed = True

                    # Write snapshot and process input
                    pane_dir = write_snapshot(pane, output_dir, scrollback, window_dir_name)
                    input_file = pane_dir / "input.txt"
                    process_input_queue(pane.pane_id, input_file)

                mappings_changed[session_name] = session_changed

            # Cleanup stale directories
            cleanup_stale(output_dir, panes, session_mappings)

            # Save updated mappings
            for session_name, changed in mappings_changed.items():
                if changed:
                    session_dir = output_dir / sanitize_name(session_name)
                    if session_dir.exists():
                        save_window_mapping(session_dir, session_mappings[session_name])

            # Sleep
            time.sleep(interval_sec)

    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
