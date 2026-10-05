"""End-to-end integration tests for the verification engine."""

import sys
from pathlib import Path

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def test_verification_with_real_test_suite(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    # Create real passing test file
    test_dir = tmp_path / "tests"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "test_sample.py"
    test_file.write_text("def test_ok(): assert 1 + 1 == 2\n", encoding="utf-8")

    contract = Contract(
        goal="Run real pytest verification",
        allowed_paths=["tests/**"],
        verification_command=f"{sys.executable} -m pytest {test_file}",
    )

    action = Action(
        type=ActionType.WRITE_FILE,
        target="tests/test_sample.py",
        content="def test_ok(): assert 1 + 1 == 2\n",
    )
    res = executor.execute(action)

    v_res = verifier.verify(action, res, contract)
    assert v_res.verified is True
    assert v_res.exit_code == 0


def test_verification_with_failing_real_test(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    # Create real failing test file
    test_dir = tmp_path / "tests"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "test_fail.py"
    test_file.write_text("def test_broken(): assert 1 + 1 == 3\n", encoding="utf-8")

    contract = Contract(
        goal="Detect failed test",
        allowed_paths=["tests/**"],
        verification_command=f"{sys.executable} -m pytest {test_file}",
    )

    action = Action(
        type=ActionType.WRITE_FILE,
        target="tests/test_fail.py",
        content="def test_broken(): assert 1 + 1 == 3\n",
    )
    res = executor.execute(action)

    v_res = verifier.verify(action, res, contract)
    assert v_res.verified is False
    assert v_res.exit_code != 0
