"""
Low-level tmux helpers built on libtmux.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

import libtmux

# Keep snapshot/read_pane_since aligned with read_pane's capture window.
_MAX_CAPTURE_LINES = 5000


def get_server() -> libtmux.Server:
    return libtmux.Server()


@dataclass
class SessionInfo:
    name: str
    created: str
    windows: int
    attached: bool
    attach_cmd: str  # command the user runs to open this session


@dataclass
class PaneSnapshot:
    """Opaque reference to a pane position at a point in time."""

    session: str
    pane_id: str
    line_count: int  # total captured pane lines at snapshot time


# ── sessions ──────────────────────────────────────────────────────────────────


def list_sessions() -> list[SessionInfo]:
    server = get_server()
    results = []
    for s in server.sessions:
        results.append(
            SessionInfo(
                name=s.name,
                created=s.session_created,
                windows=len(s.windows),
                attached=bool(int(s.session_attached or 0)),
                attach_cmd=f"tmux attach -t {s.name}",
            )
        )
    return results


def create_session(name: str, cwd: str | None = None) -> SessionInfo:
    server = get_server()
    kwargs: dict = {"session_name": name, "attach": False}
    if cwd:
        kwargs["start_directory"] = cwd
    server.new_session(**kwargs)
    # re-fetch to return fresh info
    sessions = {s.name: s for s in server.sessions}
    s = sessions[name]
    return SessionInfo(
        name=s.name,
        created=s.session_created,
        windows=len(s.windows),
        attached=bool(int(s.session_attached or 0)),
        attach_cmd=f"tmux attach -t {s.name}",
    )


def kill_session(name: str) -> None:
    server = get_server()
    session = _get_session(server, name)
    session.kill()


# ── pane resolution ───────────────────────────────────────────────────────────


def _get_session(server: libtmux.Server, name: str) -> libtmux.Session:
    session = server.sessions.get(session_name=name, default=None)
    if session is None:
        raise ValueError(f"Session '{name}' not found")
    return session


def _get_pane(
    server: libtmux.Server, session_name: str, pane_index: int = 0
) -> libtmux.Pane:
    session = _get_session(server, session_name)
    window = session.active_window or session.windows[0]
    panes = window.panes
    if pane_index < 0 or pane_index >= len(panes):
        raise ValueError(
            f"Pane index {pane_index} out of range (session has {len(panes)} panes)"
        )
    return panes[pane_index]


def _capture_pane_lines(pane: libtmux.Pane, start: str = "-") -> list[str]:
    """Return captured pane lines, including scrollback and visible output."""
    result = pane.cmd("capture-pane", "-p", "-S", start)
    return list(result.stdout)


# ── reading ───────────────────────────────────────────────────────────────────


def read_pane(session: str, pane_index: int = 0, lines: int = 200) -> str:
    """Return the last N lines of a pane (visible + scrollback)."""
    server = get_server()
    pane = _get_pane(server, session, pane_index)
    # -S -<lines> means "start N lines before the bottom"
    return "\n".join(_capture_pane_lines(pane, f"-{lines}"))


def snapshot_pane(session: str, pane_index: int = 0) -> PaneSnapshot:
    """
    Record the current pane position.
    Use this before launching a process; then call read_pane_since() after.
    """
    server = get_server()
    pane = _get_pane(server, session, pane_index)
    line_count = len(_capture_pane_lines(pane, f"-{_MAX_CAPTURE_LINES}"))
    return PaneSnapshot(
        session=session,
        pane_id=pane.pane_id,
        line_count=line_count,
    )


def read_pane_since(
    snapshot: PaneSnapshot, pane_index: int = 0, max_lines: int = 5000
) -> str:
    """
    Return output added to a pane after a snapshot was taken.
    Caps at max_lines to avoid token explosions.
    """
    server = get_server()
    pane = _get_pane(server, snapshot.session, pane_index)
    lines = _capture_pane_lines(pane, f"-{_MAX_CAPTURE_LINES}")
    new_lines = lines[snapshot.line_count :]
    if not new_lines or max_lines <= 0:
        return ""
    return "\n".join(new_lines[-max_lines:])


def grep_pane(
    session: str, pattern: str, pane_index: int = 0, lines: int = 5000
) -> str:
    """
    Search the last N lines of a pane for pattern.
    Returns matching lines with 2 lines of context.
    """
    content = read_pane(session, pane_index, lines)
    try:
        result = subprocess.run(
            ["grep", "-n", "--context=2", "--", pattern],
            input=content,
            capture_output=True,
            text=True,
        )
        return result.stdout or "(no matches)"
    except FileNotFoundError:
        # fallback: pure python grep without context
        matches = [
            f"{i+1}: {line}"
            for i, line in enumerate(content.splitlines())
            if pattern.lower() in line.lower()
        ]
        return "\n".join(matches) or "(no matches)"


# ── writing ───────────────────────────────────────────────────────────────────


def send_keys(
    session: str, keys: str, pane_index: int = 0, press_enter: bool = True
) -> None:
    """Send keys to a pane. Set press_enter=False for raw key sequences."""
    server = get_server()
    pane = _get_pane(server, session, pane_index)
    pane.send_keys(keys, enter=press_enter)


# ── attach hint ───────────────────────────────────────────────────────────────


def attach_hint(session: str) -> dict:
    """
    Return the command(s) a human should run to open this session.
    Useful for agents to tell the user where to look.
    """
    server = get_server()
    _get_session(server, session)  # validate it exists
    return {
        "session": session,
        "attach_cmd": f"tmux attach -t {session}",
        "new_window_cmd": f"tmux new-window -t {session}",
        "hint": f"Run `tmux attach -t {session}` in your terminal (or open it in Ghostty/iTerm2)",
    }
