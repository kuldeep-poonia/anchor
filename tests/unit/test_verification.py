"""Unit tests for independent verification engine."""

import sys
from pathlib import Path

from anchor.actions.executor import ActionResult
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def test_verify_written_file_exists(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws)

    f = tmp_path / "src" / "app.py"
    f.parent.mkdir(parents=True)
    f.write_text("print(1)", encoding="utf-8")

    action = Action(type=ActionType.WRITE_FILE, target="src/app.py", content="print(1)")
    res = ActionResult(action_id=action.id, success=True, output="wrote file")

    v_res = runner.verify(action, res)
    assert v_res.verified is True


def test_verify_fails_if_file_missing(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws)

    # Action claimed success, but file was not actually written to disk
    action = Action(type=ActionType.WRITE_FILE, target="src/ghost.py", content="content")
    res = ActionResult(action_id=action.id, success=True, output="claimed wrote")

    v_res = runner.verify(action, res)
    assert v_res.verified is False
    assert "does not exist" in (v_res.error or "")


def test_verify_with_passing_command(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws)

    action = Action(type=ActionType.RUN_COMMAND, target="dummy")
    res = ActionResult(action_id=action.id, success=True)
    contract = Contract(
        goal="Test passing verification",
        verification_command=f'{sys.executable} -c "import sys; sys.exit(0)"',
    )

    v_res = runner.verify(action, res, contract)
    assert v_res.verified is True
    assert v_res.exit_code == 0


def test_verify_with_failing_command(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws)

    action = Action(type=ActionType.RUN_COMMAND, target="dummy")
    res = ActionResult(action_id=action.id, success=True)
    contract = Contract(
        goal="Test failing verification",
        verification_command=f'{sys.executable} -c "import sys; sys.exit(1)"',
    )

    v_res = runner.verify(action, res, contract)
    assert v_res.verified is False
    assert v_res.exit_code == 1
