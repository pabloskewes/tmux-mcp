from __future__ import annotations

import pytest

from tmux_mcp import tmux


class Result:
    def __init__(self, stdout: list[str]) -> None:
        self.stdout = stdout


class Pane:
    pane_id = "%1"

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def cmd(self, *args: str) -> Result:
        assert args[:3] == ("capture-pane", "-p", "-S")
        return Result(self.lines)


def test_read_pane_since_returns_lines_after_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    pane = Pane(["prompt"])

    monkeypatch.setattr(tmux, "_get_pane", lambda *args: pane)

    snapshot = tmux.snapshot_pane("work")
    pane.lines = ["prompt", "build output", "done"]

    assert tmux.read_pane_since(snapshot) == "build output\ndone"


def test_read_pane_since_caps_to_last_max_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    pane = Pane(["prompt"])

    monkeypatch.setattr(tmux, "_get_pane", lambda *args: pane)

    snapshot = tmux.snapshot_pane("work")
    pane.lines = ["prompt", "one", "two", "three"]

    assert tmux.read_pane_since(snapshot, max_lines=2) == "two\nthree"


def test_get_pane_rejects_negative_index(monkeypatch: pytest.MonkeyPatch) -> None:
    class Window:
        panes = [object()]

    class Session:
        active_window = Window()
        windows = [active_window]

    monkeypatch.setattr(tmux, "_get_session", lambda *args: Session())

    with pytest.raises(ValueError, match="Pane index -1 out of range"):
        tmux._get_pane(object(), "work", pane_index=-1)
