# file-tmux-file Design

Continuous tmux snapshot and input queue tool.

## Overview

A Python script that runs in a foreground loop, continuously:
- Snapshots all tmux panes (with scrollback) to text files
- Processes input queue files, sending their contents to tmux panes
- Cleans up files for panes that no longer exist

## Directory Structure

```
tmux/                            # default output dir (configurable)
├── my-session/                  # session name
│   ├── 0/                       # window index
│   │   ├── 0/                   # pane index
│   │   │   ├── content.txt      # snapshot with metadata header
│   │   │   └── input.txt        # input queue
│   │   └── 1/
│   │       ├── content.txt
│   │       └── input.txt
│   └── 1/
│       └── 0/
│           ├── content.txt
│           └── input.txt
└── another-session/
    └── ...
```

## File Formats

### content.txt

```
Session: my-session
Window: 0 (window-name)
Pane: 0
Title: pane-title-if-set
---
[scrollback content here]
```

### input.txt

Created empty. When content is added:
- Complete lines (ending with `\n`) are sent immediately to the pane via `tmux send-keys`
- Sent lines are deleted from the file
- Unterminated lines (no trailing `\n`) are sent on the next poll cycle

## CLI Interface

```
uv run file-tmux-file [OPTIONS]

Options:
  -d, --dir PATH        Output directory (default: ./tmux)
  -s, --scrollback N    Lines of scrollback to capture (default: 500)
  -i, --interval MS     Poll interval in milliseconds (default: 500)
  -h, --help            Show help
```

## Main Loop

```
startup:
  - parse CLI args
  - create output dir if needed

loop (every poll_interval):
  1. discover current state
     - list all tmux sessions for current user
     - for each session, list windows
     - for each window, list panes

  2. snapshot panes
     - capture content with scrollback
     - write content.txt with metadata header
     - create empty input.txt if doesn't exist

  3. process input queues
     - read complete lines from input.txt, send via tmux send-keys
     - remove sent lines from file
     - unterminated lines sent on next poll

  4. cleanup stale files
     - delete session/window/pane dirs that no longer exist

  5. sleep for poll_interval
```

Ctrl+C exits cleanly.

## Error Handling

- No tmux sessions: keep looping (sessions may appear)
- Pane disappears mid-capture: skip, cleanup handles stale files
- Pane disappears with pending input: delete dir including unprocessed input
- Input file being written while reading: only process complete lines
- Output dir unwritable: print error, keep trying
- Special chars in session/window names: sanitize to `_`

## Project Structure

```
file-tmux-file/
├── pyproject.toml
├── src/
│   └── file_tmux_file/
│       ├── __init__.py
│       ├── main.py         # CLI entry point, main loop
│       ├── tmux.py         # tmux interaction
│       ├── snapshot.py     # write content.txt
│       ├── input_queue.py  # process input.txt
│       └── cleanup.py      # remove stale directories
```

No external dependencies beyond standard library.
