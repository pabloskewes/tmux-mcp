"""
tmux-mcp — MCP server for tmux session management.

Tools
-----
list_sessions       → see all tmux sessions + attach commands
create_session      → start a new named session
kill_session        → destroy a session
attach_hint         → get the command to open a session in a terminal

read_pane           → read last N lines from a pane
snapshot_pane       → record current position (use before launching a process)
read_pane_since     → read only what appeared after a snapshot
grep_pane           → search scrollback for a pattern

send_keys           → send a command or keystrokes to a pane
"""

from __future__ import annotations

from fastmcp import FastMCP

from . import tmux as t

mcp = FastMCP(
    name="tmux-mcp",
    instructions=(
        "Control tmux sessions from an AI agent. "
        "Use snapshot_pane before launching long-running processes, "
        "then read_pane_since to get exactly what was printed. "
        "Use attach_hint to tell the user which terminal to open."
    ),
)


# ── session management ────────────────────────────────────────────────────────


@mcp.tool
def list_sessions() -> list[dict]:
    """List all active tmux sessions with status and attach commands."""
    sessions = t.list_sessions()
    return [
        {
            "name": s.name,
            "windows": s.windows,
            "attached": s.attached,
            "attach_cmd": s.attach_cmd,
        }
        for s in sessions
    ]


@mcp.tool
def create_session(name: str, cwd: str | None = None) -> dict:
    """
    Create a new detached tmux session.

    Args:
        name: Session name (no spaces).
        cwd:  Starting directory (defaults to current directory).
    """
    s = t.create_session(name, cwd)
    return {
        "name": s.name,
        "attach_cmd": s.attach_cmd,
        "message": f"Session '{name}' created.",
    }


@mcp.tool
def kill_session(name: str) -> dict:
    """
    Kill a tmux session and all its panes.

    Args:
        name: Session name to kill.
    """
    t.kill_session(name)
    return {"message": f"Session '{name}' killed."}


@mcp.tool
def attach_hint(session: str) -> dict:
    """
    Return the terminal command(s) to open a session as a human.
    Use this to tell the user where to look at a running process.

    Args:
        session: Session name.
    """
    return t.attach_hint(session)


# ── reading ───────────────────────────────────────────────────────────────────


@mcp.tool
def read_pane(session: str, pane_index: int = 0, lines: int = 200) -> str:
    """
    Read the last N lines from a pane (includes scrollback).

    Args:
        session:    Session name.
        pane_index: Pane index within the active window (default 0).
        lines:      How many lines to read from the bottom (default 200, max ~5000).
    """
    return t.read_pane(session, pane_index, lines)


@mcp.tool
def snapshot_pane(session: str, pane_index: int = 0) -> dict:
    """
    Record the current scroll position of a pane.
    Call this before launching a process, then use read_pane_since() to get only
    what was printed after the snapshot.

    Args:
        session:    Session name.
        pane_index: Pane index (default 0).

    Returns a snapshot dict — pass it back to read_pane_since.
    """
    snap = t.snapshot_pane(session, pane_index)
    return {
        "session": snap.session,
        "pane_id": snap.pane_id,
        "line_count": snap.line_count,
    }


@mcp.tool
def read_pane_since(
    session: str,
    line_count: int,
    pane_index: int = 0,
    max_lines: int = 5000,
) -> str:
    """
    Read only the output that appeared after a snapshot was taken.
    Ideal for capturing the output of a specific command without noise.

    Args:
        session:    Session name.
        line_count: The line_count value returned by snapshot_pane.
        pane_index: Pane index (default 0).
        max_lines:  Safety cap to avoid huge outputs (default 5000).
    """
    snap = t.PaneSnapshot(
        session=session,
        pane_id="",  # resolved fresh inside read_pane_since
        line_count=line_count,
    )
    return t.read_pane_since(snap, pane_index, max_lines)


@mcp.tool
def grep_pane(
    session: str,
    pattern: str,
    pane_index: int = 0,
    lines: int = 5000,
) -> str:
    """
    Search scrollback for a pattern. Returns matching lines with 2 lines of context.
    Useful for finding errors in long build/server output without reading everything.

    Args:
        session:    Session name.
        pattern:    Search string (passed to grep; supports basic regex).
        pane_index: Pane index (default 0).
        lines:      How much scrollback to search (default 5000).
    """
    return t.grep_pane(session, pattern, pane_index, lines)


# ── writing ───────────────────────────────────────────────────────────────────


@mcp.tool
def send_keys(
    session: str,
    keys: str,
    pane_index: int = 0,
    press_enter: bool = True,
) -> dict:
    """
    Send keys or a command to a pane.

    Args:
        session:     Session name.
        keys:        Text or command to send.
        pane_index:  Pane index (default 0).
        press_enter: Whether to press Enter after sending (default True).
                     Set False for raw key sequences like Ctrl-C.
    """
    t.send_keys(session, keys, pane_index, press_enter)
    enter_note = " + Enter" if press_enter else ""
    return {"message": f"Sent to {session}[{pane_index}]: {keys!r}{enter_note}"}
