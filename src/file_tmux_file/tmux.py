"""Tmux interaction - list sessions, capture panes, send keys."""

import subprocess
import re
from dataclasses import dataclass


@dataclass
class Pane:
    session: str
    window_index: int
    window_name: str
    pane_index: int
    pane_title: str
    pane_id: str


def list_panes() -> list[Pane]:
    """List all panes across all tmux sessions."""
    try:
        result = subprocess.run(
            [
                "tmux", "list-panes", "-a",
                "-F", "#{session_name}\t#{window_index}\t#{window_name}\t#{pane_index}\t#{pane_title}\t#{pane_id}"
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        return []

    panes = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 6:
            panes.append(Pane(
                session=parts[0],
                window_index=int(parts[1]),
                window_name=parts[2],
                pane_index=int(parts[3]),
                pane_title=parts[4],
                pane_id=parts[5],
            ))
    return panes


def capture_pane(pane_id: str, scrollback: int) -> str:
    """Capture pane content with scrollback."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", pane_id, "-S", f"-{scrollback}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def send_keys(pane_id: str, text: str) -> bool:
    """Send keys to a pane. Returns True on success."""
    try:
        # Use -H to send hex codes, avoiding tmux's escaping issues
        # Convert text to hex pairs
        hex_codes = [format(ord(c), '02x') for c in text]
        cmd = ["tmux", "send-keys", "-t", pane_id, "-H"] + hex_codes
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def send_enter(pane_id: str) -> bool:
    """Send Enter key to submit input."""
    try:
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, "Enter"],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def send_soft_newline(pane_id: str) -> bool:
    """Send Shift+Enter for a soft newline (no submit)."""
    try:
        # Shift+Enter in most terminals
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, "S-Enter"],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def send_key(pane_id: str, key: str) -> bool:
    """Send an arbitrary tmux key by name (e.g., C-c, Escape, Up)."""
    try:
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, key],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def sanitize_name(name: str) -> str:
    """Sanitize session/window names for filesystem use."""
    return re.sub(r'[^\w\-.]', '_', name)
