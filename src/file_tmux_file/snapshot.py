"""Snapshot pane content to files."""

from pathlib import Path
from .tmux import Pane, capture_pane, sanitize_name


def write_snapshot(pane: Pane, output_dir: Path, scrollback: int) -> Path:
    """Write pane content to content.txt with metadata header."""
    pane_dir = get_pane_dir(pane, output_dir)
    pane_dir.mkdir(parents=True, exist_ok=True)

    content_file = pane_dir / "content.txt"
    input_file = pane_dir / "input.txt"

    # Capture pane content
    content = capture_pane(pane.pane_id, scrollback)

    # Build header
    header = f"""Session: {pane.session}
Window: {pane.window_index} ({pane.window_name})
Pane: {pane.pane_index}
Title: {pane.pane_title}
---
"""

    content_file.write_text(header + content)

    # Create empty input.txt if it doesn't exist
    if not input_file.exists():
        input_file.write_text("")

    return pane_dir


def get_pane_dir(pane: Pane, output_dir: Path) -> Path:
    """Get the directory path for a pane."""
    session_dir = sanitize_name(pane.session)
    return output_dir / session_dir / str(pane.window_index) / str(pane.pane_index)
