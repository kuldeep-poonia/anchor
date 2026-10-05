"""Unit tests for deterministic policy engine."""

from pathlib import Path

from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.risk.engine import RiskLevel
from anchor.workspace.paths import Workspace


def test_allow_permitted_file_write(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Edit auth module",
        allowed_paths=["src/auth/**"],
    )
    action = Action(
        type=ActionType.WRITE_FILE,
        target="src/auth/login.py",
        content="def login(): pass",
    )
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.ALLOW
    assert decision.risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}


def test_deny_forbidden_file_access(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Read files",
        allowed_paths=["**"],
        forbidden_paths=[".env"],
    )
    action = Action(type=ActionType.READ_FILE, target=".env")
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.DENY
    assert decision.risk_level == RiskLevel.CRITICAL


def test_require_approval_for_destructive_deletion(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Cleanup module",
        allowed_paths=["src/**"],
        destructive_requires_approval=True,
    )
    action = Action(type=ActionType.DELETE_FILE, target="src/old.py")
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.REQUIRE_APPROVAL


def test_deny_unlisted_command(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Test suite",
        allowed_commands=["pytest"],
    )
    action = Action(type=ActionType.RUN_COMMAND, target="curl http://evil.com")
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.DENY


def test_hard_deny_workspace_escape(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Permissive contract",
        allowed_paths=["**"],
    )
    action = Action(type=ActionType.READ_FILE, target="../outside.key")
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.DENY
    assert decision.risk_level == RiskLevel.CRITICAL
    assert "escapes" in decision.reason
