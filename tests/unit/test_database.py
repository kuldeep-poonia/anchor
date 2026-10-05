"""Unit tests for SQLite audit database."""

from pathlib import Path

from anchor.actions.models import Action, ActionType
from anchor.policy.engine import DecisionType, PolicyDecision
from anchor.risk.engine import RiskLevel
from anchor.storage.database import AuditDatabase


def test_record_and_get_action(tmp_path: Path) -> None:
    db = AuditDatabase(tmp_path / "audit.db")

    action = Action(type=ActionType.WRITE_FILE, target="src/app.py", content="code")
    decision = PolicyDecision(
        action_id=action.id,
        decision=DecisionType.ALLOW,
        risk_level=RiskLevel.LOW,
        reason="Conforms to policy",
        target="src/app.py",
    )

    db.record_decision(action, decision, status="EXECUTED", snapshot_id="snap_123")
    record = db.get_action(action.id)

    assert record is not None
    assert record["action_id"] == action.id
    assert record["decision"] == "ALLOW"
    assert record["status"] == "EXECUTED"
    assert record["snapshot_id"] == "snap_123"


def test_pending_approvals_workflow(tmp_path: Path) -> None:
    db = AuditDatabase(tmp_path / "audit.db")

    action = Action(type=ActionType.DELETE_FILE, target="src/dangerous.py")
    decision = PolicyDecision(
        action_id=action.id,
        decision=DecisionType.REQUIRE_APPROVAL,
        risk_level=RiskLevel.CRITICAL,
        reason="Destructive delete",
        target="src/dangerous.py",
    )

    db.record_decision(action, decision, status="PENDING_APPROVAL")
    pending = db.get_pending_approvals()

    assert len(pending) == 1
    assert pending[0]["action_id"] == action.id

    # Update status on approval
    db.update_status(action.id, status="APPROVED", verified=True)
    assert len(db.get_pending_approvals()) == 0

    updated = db.get_action(action.id)
    assert updated is not None
    assert updated["status"] == "APPROVED"
    assert updated["verified"] == 1
