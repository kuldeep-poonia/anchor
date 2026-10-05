"""Unit tests for ActionExecutor."""

import sys
from pathlib import Path

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.workspace.paths import Workspace


def test_write_and_read_file(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)

    write_act = Action(
        type=ActionType.WRITE_FILE,
        target="src/test.txt",
        content="Hello Anchor!",
    )
    res = executor.execute(write_act)
    assert res.success is True
    assert (tmp_path / "src" / "test.txt").read_text(encoding="utf-8") == "Hello Anchor!"

    read_act = Action(type=ActionType.READ_FILE, target="src/test.txt")
    read_res = executor.execute(read_act)
    assert read_res.success is True
    assert read_res.output == "Hello Anchor!"


def test_delete_file(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)

    target = tmp_path / "remove_me.txt"
    target.write_text("delete this", encoding="utf-8")

    del_act = Action(type=ActionType.DELETE_FILE, target="remove_me.txt")
    res = executor.execute(del_act)
    assert res.success is True
    assert not target.exists()


def test_run_command_success(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)

    cmd_act = Action(
        type=ActionType.RUN_COMMAND,
        target=sys.executable,
        args=["-c", "print('Command Ran Successfully')"],
    )
    res = executor.execute(cmd_act)
    assert res.success is True
    assert "Command Ran Successfully" in res.output
    assert res.exit_code == 0


def test_run_command_timeout(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws, default_timeout=0.5)

    cmd_act = Action(
        type=ActionType.RUN_COMMAND,
        target=sys.executable,
        args=["-c", "import time; time.sleep(2)"],
    )
    res = executor.execute(cmd_act)
    assert res.success is False
    assert "timed out" in (res.error or "")
