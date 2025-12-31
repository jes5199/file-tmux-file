"""Process input queue files.

Simple line-based protocol:
- Each line is sent followed by Enter (submits the line)
- Lines starting with / are commands:
  - /literal <text> - send text WITHOUT Enter (for partial input)
  - /key <name> - send tmux key (e.g., /key C-c, /key Escape)
  - /clear - clear input buffer (Ctrl+U)
  - /cancel - send Ctrl+C
  - /escape - send Escape

Example:
    echo hello
    (sends "echo hello" + Enter)

    /literal partial text
    (sends "partial text" without Enter)

    /key C-c
    (sends Ctrl+C)
"""

from pathlib import Path
from .tmux import send_keys, send_enter, send_key


def process_input_queue(pane_id: str, input_file: Path) -> None:
    """Process input.txt, sending each line to the pane."""
    if not input_file.exists():
        return

    content = input_file.read_text()
    if not content:
        return

    # Process each line
    lines = content.split('\n')

    # Track if file ends with newline (last element will be empty string)
    has_trailing_newline = content.endswith('\n')
    if has_trailing_newline and lines and lines[-1] == '':
        lines = lines[:-1]  # Remove empty trailing element

    processed_count = 0
    for i, line in enumerate(lines):
        is_last = (i == len(lines) - 1)

        # Skip empty lines
        if not line:
            processed_count += 1
            continue

        if line.startswith('/'):
            # Command
            _process_command(pane_id, line)
            processed_count += 1
        else:
            # Regular text - send with Enter if line is complete
            if is_last and not has_trailing_newline:
                # Last line without newline - leave it for next poll
                break
            send_keys(pane_id, line)
            send_enter(pane_id)
            processed_count += 1

    # Clear processed content, keep unprocessed remainder
    if processed_count == len(lines):
        input_file.write_text("")
    else:
        remaining = '\n'.join(lines[processed_count:])
        input_file.write_text(remaining)


def _process_command(pane_id: str, command: str) -> bool:
    """Process a /command line. Returns True if handled."""
    parts = command.split(None, 1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/literal":
        if arg:
            send_keys(pane_id, arg)
    elif cmd == "/key":
        if arg:
            send_key(pane_id, arg)
    elif cmd == "/clear":
        send_key(pane_id, "C-u")
    elif cmd == "/cancel":
        send_key(pane_id, "C-c")
    elif cmd == "/escape":
        send_key(pane_id, "Escape")
    elif cmd == "/enter":
        send_enter(pane_id)
    else:
        return False  # Unknown command
    return True


def clear_pending(pane_id: str) -> None:
    """Clear any pending content for a pane (no-op in simplified protocol)."""
    pass
