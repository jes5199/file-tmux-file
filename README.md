# file-tmux-file

A continuous tmux monitoring and control tool that bridges tmux and the filesystem.

## What It Does

- **Captures** all tmux pane content (with scrollback) to text files
- **Sends** commands to panes via input queue files
- **Cleans up** stale directories when panes close

This enables programmatic interaction with tmux sessions through simple file operations.

## Installation

Requires Python 3.10+ and tmux.

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

## Usage

```bash
# Basic usage (creates ./tmux output directory)
file-tmux-file

# Custom output directory
file-tmux-file --dir /path/to/output

# Custom scrollback (1000 lines) and poll interval (250ms)
file-tmux-file -d ./tmux_data -s 1000 -i 250
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `-d, --dir PATH` | `./tmux` | Output directory |
| `-s, --scrollback N` | `500` | Lines of scrollback to capture |
| `-i, --interval MS` | `500` | Poll interval in milliseconds |

## Output Structure

```
tmux/
├── session-name/
│   └── window-index/
│       └── pane-index/
│           ├── content.txt   # Pane snapshot
│           └── input.txt     # Input queue
└── .lock
```

### content.txt

Contains pane content with a metadata header:

```
Session: main
Window: 0 (vim)
Pane: 0
Title: editor
---
[pane content here...]
```

### input.txt

Write commands here to send them to the pane:

```
echo "hello world"
ls -la
```

Lines ending with `\n` are sent with Enter. Incomplete lines are held until complete.

### Special Characters

Unicode, emoji, and special characters are fully supported:

```
echo "Hello 世界 🚀"
```

Text is sent via hex encoding internally, avoiding tmux escaping issues.

### Special Commands

| Command | Action |
|---------|--------|
| `/literal text` | Send text without Enter |
| `/key <name>` | Send a tmux key by name |
| `/enter` | Send Enter key |
| `/escape` | Send Escape key |
| `/clear` | Clear input buffer (Ctrl+U) |
| `/cancel` | Send Ctrl+C |

#### Key Names for `/key`

Use standard tmux key names:

- Modifiers: `C-c` (Ctrl+C), `M-x` (Alt+X), `C-M-a` (Ctrl+Alt+A)
- Special: `Enter`, `Escape`, `Tab`, `Space`, `BSpace`
- Arrows: `Up`, `Down`, `Left`, `Right`
- Function: `F1` through `F12`
- Navigation: `Home`, `End`, `PgUp`, `PgDn`

## Use Cases

- **Automation**: Programmatically control tmux from scripts
- **Monitoring**: Continuously capture pane state for logging
- **Integration**: Bridge tmux with other tools via the filesystem
- **Remote control**: Control tmux sessions over network (via NFS, rsync, etc.)

## Dependencies

None. Uses only Python standard library.

## License

MIT
