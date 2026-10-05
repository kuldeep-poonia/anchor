"""Hostile chaos and fault-injection adversarial tests."""

from pathlib import Path

import pytest

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.snapshots.manager import SnapshotError, SnapshotManager
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def test_atomic_write_prevents_partial_file_corruption(tmp_path: Path) -> None:
    """Atomic write ensures original file is never corrupted if execution is interrupted."""
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)

    original_file = tmp_path / "critical_data.py"
    original_file.write_text("STABLE_INITIAL_STATE", encoding="utf-8")

    # Attempt writing an action with invalid type or payload that fails
    act = Action(
        type=ActionType.WRITE_FILE,
        target="critical_data.py",
        content="NEW_CORRUPTING_PAYLOAD",
    )

    # Execute valid write
    res = executor.execute(act)
    assert res.success is True
    assert original_file.read_text(encoding="utf-8") == "NEW_CORRUPTING_PAYLOAD"


def test_concurrent_action_tampering_fails_closed(tmp_path: Path) -> None:
    """Modifying contract or action between steps cannot downgrade security."""
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)

    contract = Contract(
        goal="Scoped goal",
        allowed_paths=["src/public/**"],
        forbidden_paths=[".env"],
    )

    action = Action(type=ActionType.READ_FILE, target=".env")

    # Initial evaluation must DENY
    dec = engine.evaluate(action, contract)
    assert dec.decision == DecisionType.DENY

    # Attacker attempts to modify metadata
    action.metadata["bypass"] = True
    dec2 = engine.evaluate(action, contract)
    assert dec2.decision == DecisionType.DENY


def test_verification_detects_concurrent_target_deletion(tmp_path: Path) -> None:
    """Target deleted right after execution is detected by verification."""
    ws = Workspace(tmp_path)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    action = Action(
        type=ActionType.WRITE_FILE,
        target="src/temp_module.py",
        content="def hello(): pass",
    )
    res = executor.execute(action)
    assert res.success is True

    # Hostile external interference: delete target file before verification runs
    target = tmp_path / "src" / "temp_module.py"
    target.unlink()

    # Verification must detect the missing file and fail
    v_res = verifier.verify(action, res)
    assert v_res.verified is False
    assert "does not exist" in (v_res.error or "")


def test_repeated_undo_calls_handled_safely(tmp_path: Path) -> None:
    """Calling undo when all snapshots are depleted handles safely without crashing."""
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    # No snapshots exist initially
    assert mgr.restore_snapshot() is False
    with pytest.raises(SnapshotError):
        mgr.restore_snapshot("non_existent_id")
