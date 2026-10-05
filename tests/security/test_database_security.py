"""Adversarial security tests for database persistence and SQL injection resistance."""

from pathlib import Path

from anchor.actions.models import Action, ActionType
from anchor.policy.engine import DecisionType, PolicyDecision
from anchor.risk.engine import RiskLevel
from anchor.storage.database import AuditDatabase


def test_sql_injection_resistance_in_action_target(tmp_path: Path) -> None:
    db = AuditDatabase(tmp_path / "audit.db")

    malicious_target = "'; DROP TABLE audit_log; --"
    action = Action(type=ActionType.READ_FILE, target=malicious_target)
    decision = PolicyDecision(
        action_id=action.id,
        decision=DecisionType.DENY,
        risk_level=RiskLevel.CRITICAL,
        reason="Malicious target string",
        target=malicious_target,
    )

    db.record_decision(action, decision, status="DENIED")

    # Table must still exist and record must be cleanly queryable
    record = db.get_action(action.id)
    assert record is not None
    assert record["target"] == malicious_target


def test_sql_injection_in_contract_recording(tmp_path: Path) -> None:
    db = AuditDatabase(tmp_path / "audit.db")

    contract_id = "'; DELETE FROM contracts; --"
    goal = "'; UPDATE audit_log SET decision = 'ALLOW'; --"
    payload = "{}"

    db.record_contract(contract_id, goal, payload)

    # Verify no execution of malicious SQL statements
    with db._get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM contracts")
        count = cursor.fetchone()[0]
        assert count == 1
