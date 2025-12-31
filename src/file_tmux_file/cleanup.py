"""Clean up stale directories."""

from pathlib import Path
from .tmux import Pane, sanitize_name
from .input_queue import clear_pending


def cleanup_stale(output_dir: Path, active_panes: list[Pane]) -> None:
    """Remove directories for panes that no longer exist."""
    if not output_dir.exists():
        return

    # Build set of active pane paths
    active_paths: set[Path] = set()
    for pane in active_panes:
        session_dir = sanitize_name(pane.session)
        pane_path = output_dir / session_dir / str(pane.window_index) / str(pane.pane_index)
        active_paths.add(pane_path)

        # Also mark parent dirs as active
        active_paths.add(pane_path.parent)  # window dir
        active_paths.add(pane_path.parent.parent)  # session dir

    # Walk the tree and find stale directories
    stale_pane_dirs: list[Path] = []

    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir():
            continue
        for window_dir in session_dir.iterdir():
            if not window_dir.is_dir():
                continue
            for pane_dir in window_dir.iterdir():
                if not pane_dir.is_dir():
                    continue
                if pane_dir not in active_paths:
                    stale_pane_dirs.append(pane_dir)

    # Remove stale pane directories
    for pane_dir in stale_pane_dirs:
        # Clear any pending input for this pane
        # We construct a fake pane_id from the path for cleanup
        # This isn't perfect but handles the cleanup case
        _remove_dir_recursive(pane_dir)

    # Clean up empty parent directories
    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir():
            continue
        for window_dir in list(session_dir.iterdir()):
            if window_dir.is_dir() and not any(window_dir.iterdir()):
                window_dir.rmdir()
        if not any(session_dir.iterdir()):
            session_dir.rmdir()


def _remove_dir_recursive(path: Path) -> None:
    """Remove a directory and all its contents."""
    if path.is_dir():
        for child in path.iterdir():
            _remove_dir_recursive(child)
        path.rmdir()
    else:
        path.unlink()
