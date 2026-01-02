# Window Title in Filename Design

Add window titles to directory names and handle renames gracefully.

## Directory Structure

**New format:**
```
tmux/
├── my-session/
│   ├── windows.json              # {"@0": "0-bash", "@1": "1-vim"}
│   ├── 0-bash/
│   │   └── 0/
│   │       ├── content.txt
│   │       └── input.txt
│   └── 1-vim/
│       └── 0/
│           ├── content.txt
│           └── input.txt
```

**Naming rules:**
- Window directories: `{index}-{sanitized_name}` (e.g., `0-bash`, `2-my_project`)
- Sanitization: same as existing `sanitize_name()` - replace non-word chars with `_`
- Pane directories: unchanged (just the pane index)

## Window Identity

Use tmux's unique window ID (`@0`, `@1`, etc.) to track windows across renames and reorders.

**Mapping file:** `tmux/session/windows.json`
```json
{"@0": "0-bash", "@1": "1-vim"}
```

## Rename Detection & Handling

**On each loop iteration:**
1. Load `windows.json` for each session (create if missing)
2. For each active window, check if its ID exists in the mapping
   - **New window**: Create directory with current name, add to mapping
   - **Existing window, same name**: No action needed
   - **Existing window, different name**: Rename directory, update mapping
3. Save `windows.json` if changed

**Edge case:** If target directory already exists (collision), delete the stale one first then rename.

## Cleanup & Migration

**Startup migration (old to new format):**
1. For each session directory, check for old-style numeric window dirs (`0/`, `1/`, etc.)
2. Query tmux for current windows in that session
3. Match by window index: rename `0/` to `0-{current_window_name}/`
4. Create initial `windows.json` with the mappings
5. Delete any old-style dirs that don't match an active window

**Ongoing cleanup:**
- Window dirs in filesystem but not in `windows.json` with a matching active window ID: delete
- Window IDs in `windows.json` but no longer in tmux: remove from mapping, delete directory
- Empty session directories: delete

**Order of operations:**
1. Migration (if needed)
2. Process active panes (snapshots, input)
3. Cleanup stale directories
4. Save updated mappings

## Implementation Changes

**Files to modify:**

1. **`tmux.py`** - Add `window_id` field to `Pane` dataclass

2. **`snapshot.py`** - Update `get_pane_dir()` to use `{index}-{name}` format

3. **`cleanup.py`** - Refactor to handle mappings and renames

4. **`main.py`** - Add migration step before main loop

**New helper functions:**
- `load_window_mapping(session_dir) -> dict`
- `save_window_mapping(session_dir, mapping)`
- `migrate_old_format(output_dir, active_panes)`
- `get_window_dir_name(window_index, window_name) -> str`
