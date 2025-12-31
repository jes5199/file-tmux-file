"""Process input queue files."""

from pathlib import Path
from .tmux import send_keys


# Track unterminated lines from previous poll
_pending_unterminated: dict[str, str] = {}


def process_input_queue(pane_id: str, input_file: Path) -> None:
    """Process input.txt, sending content to pane."""
    global _pending_unterminated

    if not input_file.exists():
        return

    content = input_file.read_text()
    if not content:
        # Check if we have a pending unterminated line from last poll
        if pane_id in _pending_unterminated:
            pending = _pending_unterminated.pop(pane_id)
            send_keys(pane_id, pending)
        return

    lines = content.split('\n')

    # Check if there's an unterminated line at the end
    has_trailing_newline = content.endswith('\n')

    if has_trailing_newline:
        # All lines are complete (last element is empty string from split)
        complete_lines = lines[:-1]  # Remove the empty string
        unterminated = None
    else:
        # Last line is unterminated
        complete_lines = lines[:-1]
        unterminated = lines[-1]

    # First, send any pending unterminated line from previous poll
    if pane_id in _pending_unterminated:
        pending = _pending_unterminated.pop(pane_id)
        send_keys(pane_id, pending)

    # Send complete lines with their newlines
    for line in complete_lines:
        send_keys(pane_id, line + '\n')

    # Handle unterminated line
    if unterminated:
        # Store for next poll
        _pending_unterminated[pane_id] = unterminated
        # Rewrite file with just the unterminated portion
        input_file.write_text(unterminated)
    else:
        # All content was sent, clear the file
        input_file.write_text("")


def clear_pending(pane_id: str) -> None:
    """Clear any pending unterminated line for a pane."""
    _pending_unterminated.pop(pane_id, None)
