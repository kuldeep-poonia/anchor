"""Adversarial security tests for command execution and containment."""

import os
import sys
from pathlib import Path

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.workspace.paths import Workspace


def test_redacts_sensitive_env_vars_from_subprocess(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)

    # Inject simulated secret into parent process
    os.environ["NEBIUS_API_KEY"] = "secret_nebius_token_123"
    try:
        cmd_act = Action(
            type=ActionType.RUN_COMMAND,
            target=sys.executable,
            args=["-c", "import os; print(os.getenv('NEBIUS_API_KEY'))"],
        )
        res = executor.execute(cmd_act)
        assert res.success is True
        # Child process must see None, not the secret!
        assert res.output.strip() == "None"
    finally:
        os.environ.pop("NEBIUS_API_KEY", None)


def test_prevents_file_write_outside_workspace(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)

    write_act = Action(
        type=ActionType.WRITE_FILE,
        target="../escaped_file.txt",
        content="malicious payload",
    )
    res = executor.execute(write_act)
    assert res.success is False
    assert "escapes" in (res.error or "").lower()
    assert not (tmp_path.parent / "escaped_file.txt").exists()


def test_caps_enormous_stdout_output(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    max_chars = 1000
    executor = ActionExecutor(ws, max_output_chars=max_chars)

    # Produce output larger than max_output_chars
    cmd_act = Action(
        type=ActionType.RUN_COMMAND,
        target=sys.executable,
        args=["-c", "print('A' * 20000)"],
    )
    res = executor.execute(cmd_act)
    assert res.success is True
    assert len(res.output) <= max_chars
