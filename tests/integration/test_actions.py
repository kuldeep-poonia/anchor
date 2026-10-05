"""End-to-end integration tests for multi-step agent action workflows."""

from pathlib import Path

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.risk.engine import RiskEngine
from anchor.snapshots.manager import SnapshotManager
from anchor.storage.database import AuditDatabase
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def test_full_agent_workflow(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    db = AuditDatabase(tmp_path / ".anchor" / "audit.db")
    snapshot_mgr = SnapshotManager(ws)
    risk_engine = RiskEngine()
    policy_engine = PolicyEngine(ws, risk_engine)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    contract = Contract(
        goal="Develop feature and protect secrets",
        allowed_paths=["src/**", "tests/**"],
        forbidden_paths=[".env", "secrets/**"],
        allowed_commands=["pytest"],
        destructive_requires_approval=True,
    )

    # 1. Allowed file write
    act1 = Action(
        type=ActionType.WRITE_FILE,
        target="src/calculator.py",
        content="def add(a, b): return a + b\n",
    )
    dec1 = policy_engine.evaluate(act1, contract)
    assert dec1.decision == DecisionType.ALLOW

    snap1 = snapshot_mgr.create_snapshot(act1)
    res1 = executor.execute(act1)
    assert res1.success is True
    v1 = verifier.verify(act1, res1)
    assert v1.verified is True
    db.record_decision(act1, dec1, "EXECUTED", snap1)

    # 2. Blocked forbidden read
    act2 = Action(type=ActionType.READ_FILE, target=".env")
    dec2 = policy_engine.evaluate(act2, contract)
    assert dec2.decision == DecisionType.DENY
    db.record_decision(act2, dec2, "DENIED")

    # 3. High-risk deletion requiring approval
    act3 = Action(type=ActionType.DELETE_FILE, target="src/calculator.py")
    dec3 = policy_engine.evaluate(act3, contract)
    assert dec3.decision == DecisionType.REQUIRE_APPROVAL
    db.record_decision(act3, dec3, "PENDING_APPROVAL")

    # Check pending approvals
    pending = db.get_pending_approvals()
    assert len(pending) == 1
    assert pending[0]["action_id"] == act3.id

    # Simulate user approval
    snap3 = snapshot_mgr.create_snapshot(act3)
    res3 = executor.execute(act3)
    assert res3.success is True
    v3 = verifier.verify(act3, res3)
    assert v3.verified is True
    db.update_status(act3.id, "APPROVED", verified=True, snapshot_id=snap3)

    assert len(db.get_pending_approvals()) == 0
    assert not (tmp_path / "src" / "calculator.py").exists()
