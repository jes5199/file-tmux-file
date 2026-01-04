"""Clean up stale directories and manage window mappings."""

import json
from pathlib import Path
from .tmux import Pane, sanitize_name, get_window_dir_name


def load_window_mapping(session_dir: Path) -> dict[str, str]:
    """Load window ID to directory name mapping from windows.json."""
    mapping_file = session_dir / "windows.json"
    if mapping_file.exists():
        try:
            return json.loads(mapping_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_window_mapping(session_dir: Path, mapping: dict[str, str]) -> None:
    """Save window ID to directory name mapping to windows.json."""
    mapping_file = session_dir / "windows.json"
    mapping_file.write_text(json.dumps(mapping, indent=2) + "\n")


def get_or_create_window_dir(
    pane: Pane, output_dir: Path, mapping: dict[str, str]
) -> tuple[str, bool]:
    """
    Get the window directory name for a pane, handling renames.

    Returns (window_dir_name, mapping_changed).
    """
    session_dir = output_dir / sanitize_name(pane.session)
    new_dir_name = get_window_dir_name(pane.window_index, pane.window_name)

    if pane.window_id in mapping:
        old_dir_name = mapping[pane.window_id]
        if old_dir_name == new_dir_name:
            # No rename needed
            return new_dir_name, False

        # Window was renamed - rename directory
        old_dir = session_dir / old_dir_name
        new_dir = session_dir / new_dir_name

        if old_dir.exists():
            # If target exists (collision), remove it first
            if new_dir.exists() and new_dir != old_dir:
                _remove_dir_recursive(new_dir)
            old_dir.rename(new_dir)

        mapping[pane.window_id] = new_dir_name
        return new_dir_name, True
    else:
        # New window
        mapping[pane.window_id] = new_dir_name
        return new_dir_name, True


def cleanup_stale(
    output_dir: Path,
    active_panes: list[Pane],
    session_mappings: dict[str, dict[str, str]]
) -> None:
    """Remove directories for panes/windows that no longer exist."""
    if not output_dir.exists():
        return

    # Build set of active paths
    active_session_dirs: set[Path] = set()
    active_window_dirs: set[Path] = set()
    active_pane_dirs: set[Path] = set()

    # Group panes by session to get active window IDs per session
    active_window_ids: dict[str, set[str]] = {}

    for pane in active_panes:
        session_name = sanitize_name(pane.session)
        session_dir = output_dir / session_name
        active_session_dirs.add(session_dir)

        if pane.session not in active_window_ids:
            active_window_ids[pane.session] = set()
        active_window_ids[pane.session].add(pane.window_id)

        # Get window dir from mapping
        mapping = session_mappings.get(pane.session, {})
        window_dir_name = mapping.get(pane.window_id, get_window_dir_name(pane.window_index, pane.window_name))

        window_dir = session_dir / window_dir_name
        active_window_dirs.add(window_dir)

        pane_dir = window_dir / str(pane.pane_index)
        active_pane_dirs.add(pane_dir)

    # Clean up stale window IDs from mappings
    for session_name, mapping in session_mappings.items():
        active_ids = active_window_ids.get(session_name, set())
        stale_ids = [wid for wid in mapping if wid not in active_ids]
        for wid in stale_ids:
            del mapping[wid]

    # Walk the tree and find stale directories
    stale_session_dirs: list[Path] = []
    stale_pane_dirs: list[Path] = []
    stale_window_dirs: list[Path] = []

    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir() or session_dir.name.startswith('.'):
            continue

        if session_dir not in active_session_dirs:
            # Entire session is stale
            stale_session_dirs.append(session_dir)
            continue

        for window_dir in session_dir.iterdir():
            if not window_dir.is_dir():
                continue

            if window_dir not in active_window_dirs:
                # Entire window is stale
                stale_window_dirs.append(window_dir)
            else:
                # Check for stale panes within active window
                for pane_dir in window_dir.iterdir():
                    if not pane_dir.is_dir():
                        continue
                    if pane_dir not in active_pane_dirs:
                        stale_pane_dirs.append(pane_dir)

    # Remove stale directories (order: panes, windows, sessions)
    for pane_dir in stale_pane_dirs:
        _remove_dir_recursive(pane_dir)

    for window_dir in stale_window_dirs:
        _remove_dir_recursive(window_dir)

    for session_dir in stale_session_dirs:
        _remove_dir_recursive(session_dir)

    # Clean up empty parent directories
    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir() or session_dir.name.startswith('.'):
            continue
        # Check if only windows.json remains or directory is empty
        contents = list(session_dir.iterdir())
        non_json_contents = [c for c in contents if c.name != "windows.json"]
        if not non_json_contents:
            _remove_dir_recursive(session_dir)


def migrate_old_format(output_dir: Path, active_panes: list[Pane]) -> dict[str, dict[str, str]]:
    """
    Migrate old numeric-only window directories to new format.

    Returns the session mappings that were created/updated.
    """
    if not output_dir.exists():
        return {}

    # Group active panes by session
    panes_by_session: dict[str, list[Pane]] = {}
    for pane in active_panes:
        if pane.session not in panes_by_session:
            panes_by_session[pane.session] = []
        panes_by_session[pane.session].append(pane)

    session_mappings: dict[str, dict[str, str]] = {}

    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir() or session_dir.name.startswith('.'):
            continue

        # Load existing mapping
        mapping = load_window_mapping(session_dir)

        # Find the session name (reverse lookup from sanitized name)
        session_name = None
        for pane in active_panes:
            if sanitize_name(pane.session) == session_dir.name:
                session_name = pane.session
                break

        if session_name is None:
            # Session no longer exists, will be cleaned up
            continue

        session_panes = panes_by_session.get(session_name, [])

        # Build index -> window info map from active panes
        index_to_window: dict[int, Pane] = {}
        for pane in session_panes:
            if pane.window_index not in index_to_window:
                index_to_window[pane.window_index] = pane

        # Check for old-style numeric directories
        for window_dir in list(session_dir.iterdir()):
            if not window_dir.is_dir():
                continue

            dir_name = window_dir.name

            # Check if it's an old-style numeric-only directory
            if dir_name.isdigit():
                window_index = int(dir_name)

                if window_index in index_to_window:
                    # Migrate to new format
                    pane = index_to_window[window_index]
                    new_dir_name = get_window_dir_name(pane.window_index, pane.window_name)
                    new_dir = session_dir / new_dir_name

                    if new_dir.exists() and new_dir != window_dir:
                        _remove_dir_recursive(new_dir)

                    window_dir.rename(new_dir)
                    mapping[pane.window_id] = new_dir_name
                else:
                    # Old window no longer exists, delete it
                    _remove_dir_recursive(window_dir)

        session_mappings[session_name] = mapping
        save_window_mapping(session_dir, mapping)

    return session_mappings


def _remove_dir_recursive(path: Path) -> None:
    """Remove a directory and all its contents."""
    if path.is_dir():
        for child in path.iterdir():
            _remove_dir_recursive(child)
        path.rmdir()
    else:
        path.unlink()
