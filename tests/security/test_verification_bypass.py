"""Adversarial security tests for verification bypass attempts."""

import sys
from pathlib import Path

from anchor.actions.executor import ActionResult
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def test_ignores_agent_falsified_verification_claims(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws)

    # Agent claims in metadata that verification passed with 100% test coverage
    action = Action(
        type=ActionType.RUN_COMMAND,
        target="pytest",
        metadata={"verified": True, "claim": "all tests passed perfectly"},
    )
    # But action result had exit code 1
    res = ActionResult(
        action_id=action.id,
        success=False,
        error="Tests failed",
        exit_code=1,
    )

    v_res = runner.verify(action, res)
    assert v_res.verified is False


def test_verification_detects_failed_deletion(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws)

    # File still exists on disk
    target = tmp_path / "src" / "target.py"
    target.parent.mkdir(parents=True)
    target.write_text("still here", encoding="utf-8")

    action = Action(type=ActionType.DELETE_FILE, target="src/target.py")
    res = ActionResult(action_id=action.id, success=True, output="claimed deleted")

    v_res = runner.verify(action, res)
    assert v_res.verified is False
    assert "still exists" in (v_res.error or "")


def test_verification_handles_timeout(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    runner = VerificationRunner(ws, default_timeout=0.5)

    action = Action(type=ActionType.RUN_COMMAND, target="run")
    res = ActionResult(action_id=action.id, success=True)
    contract = Contract(
        goal="Test timeout",
        verification_command=f'{sys.executable} -c "import time; time.sleep(2)"',
    )

    v_res = runner.verify(action, res, contract)
    assert v_res.verified is False
    assert "timed out" in (v_res.error or "")
