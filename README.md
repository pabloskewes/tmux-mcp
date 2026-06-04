# tmux-mcp

MCP server for tmux. Gives AI agents visibility into and control over your tmux sessions.

## Tools

| Tool              | What it does                                                |
| ----------------- | ----------------------------------------------------------- |
| `list_sessions`   | List all sessions + attach commands                         |
| `create_session`  | Start a new detached session                                |
| `kill_session`    | Kill a session                                              |
| `attach_hint`     | Get the command to open a session in your terminal          |
| `read_pane`       | Read last N lines from a pane                               |
| `snapshot_pane`   | Record current scroll position (before launching a process) |
| `read_pane_since` | Read only what appeared after a snapshot                    |
| `grep_pane`       | Search scrollback for a pattern                             |
| `send_keys`       | Send a command or keystrokes to a pane                      |

## Install

```bash
uv sync
```

## Run

```bash
uv run tmux-mcp
```

## Connect

```json
{
  "mcpServers": {
    "tmux": {
      "command": "uv",
      "args": ["--directory", "/path/to/tmux-mcp", "run", "tmux-mcp"]
    }
  }
}
```

## Reading output

**Last N lines** — simple, good for interactive sessions:

```
read_pane(session="work", lines=200)
```

**Snapshot + read since** — use when the agent launches a process itself.
Captures exactly what was printed, nothing before:

```
snap = snapshot_pane(session="work")          # → {line_count: 1432}
send_keys(session="work", keys="make")
# ... later ...
read_pane_since(session="work", line_count=1432)
```

**Grep** — use when you know what you're looking for:

```
grep_pane(session="work", pattern="error")
```

Calls system `grep` when available (regex + context lines), falls back to Python otherwise.
