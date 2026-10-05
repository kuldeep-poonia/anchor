"""Unit tests for deterministic risk engine."""

from pathlib import Path

from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.risk.engine import RiskEngine, RiskLevel
from anchor.workspace.paths import Workspace


def test_delete_action_is_critical(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = RiskEngine()
    action = Action(type=ActionType.DELETE_FILE, target="src/auth.py")
    assert engine.calculate_risk(action, ws) == RiskLevel.CRITICAL


def test_agent_cannot_downgrade_risk(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = RiskEngine()
    action = Action(
        type=ActionType.DELETE_FILE,
        target="src/auth.py",
        metadata={"claimed_risk": "LOW", "confidence": 1.0},
    )
    # Even if agent claims risk is LOW, engine must classify as CRITICAL!
    assert engine.calculate_risk(action, ws) == RiskLevel.CRITICAL


def test_reading_sensitive_path_is_critical(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    contract = Contract(goal="Test", allowed_paths=["**"])
    engine = RiskEngine()
    action = Action(type=ActionType.READ_FILE, target=".env")
    assert engine.calculate_risk(action, ws, contract) == RiskLevel.CRITICAL


def test_safe_test_command_is_low(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = RiskEngine()
    action = Action(type=ActionType.RUN_COMMAND, target="pytest -v")
    assert engine.calculate_risk(action, ws) == RiskLevel.LOW


def test_dangerous_system_command_is_critical(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = RiskEngine()
    action = Action(type=ActionType.RUN_COMMAND, target="rm -rf /")
    assert engine.calculate_risk(action, ws) == RiskLevel.CRITICAL
