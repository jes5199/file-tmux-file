"""Process input queue files.

Message format:
- Single newline within text: sent as Shift+Enter (soft newline, no submit)
- Double newline (blank line) or EOF after newline: submits the message
- Text without trailing newline: buffered until next poll

Example:
    Hello
    World

    (blank line above triggers submit of "Hello\\nWorld")
"""

from pathlib import Path
from .tmux import send_keys, send_enter, send_soft_newline


# Track pending content from previous poll
_pending_content: dict[str, str] = {}


def process_input_queue(pane_id: str, input_file: Path) -> None:
    """Process input.txt, sending content to pane."""
    if not input_file.exists():
        return

    content = input_file.read_text()
    if not content:
        # Check if we have pending content from last poll - send it now
        if pane_id in _pending_content:
            pending = _pending_content.pop(pane_id)
            _send_message(pane_id, pending, submit=True)
        return

    # Check for submit signal: double newline or trailing newline at EOF
    # Split on double newline to find complete messages
    messages = content.split('\n\n')

    if len(messages) > 1:
        # We have at least one complete message (before a blank line)
        # Send all complete messages
        for msg in messages[:-1]:
            if msg.strip():  # Don't send empty messages
                # Prepend any pending content to first message
                if pane_id in _pending_content:
                    msg = _pending_content.pop(pane_id) + '\n' + msg
                _send_message(pane_id, msg, submit=True)

        # Handle remaining content after last blank line
        remaining = messages[-1]
        if remaining:
            _pending_content[pane_id] = remaining
            input_file.write_text(remaining)
        else:
            _pending_content.pop(pane_id, None)
            input_file.write_text("")
    else:
        # No double newline - buffer the content
        # Check if content ends with single newline (ready for more input)
        if content.endswith('\n'):
            # Accumulate with any pending content
            if pane_id in _pending_content:
                _pending_content[pane_id] += '\n' + content.rstrip('\n')
            else:
                _pending_content[pane_id] = content.rstrip('\n')
            input_file.write_text("")
        else:
            # No trailing newline - check if unchanged from last poll
            pending = _pending_content.get(pane_id)
            if pending and content == pending:
                # Unchanged - send it now
                _pending_content.pop(pane_id)
                _send_message(pane_id, content, submit=True)
                input_file.write_text("")
            else:
                # New or modified content - buffer it
                _pending_content[pane_id] = content


def _send_message(pane_id: str, message: str, submit: bool = False) -> None:
    """Send a message to a pane, using soft newlines for internal line breaks."""
    lines = message.split('\n')
    for i, line in enumerate(lines):
        send_keys(pane_id, line)
        if i < len(lines) - 1:
            # More lines to come - soft newline
            send_soft_newline(pane_id)
    if submit:
        send_enter(pane_id)


def clear_pending(pane_id: str) -> None:
    """Clear any pending content for a pane."""
    _pending_content.pop(pane_id, None)
