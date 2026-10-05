"""Adversarial security tests for policy bypass vectors."""

from pathlib import Path

from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.workspace.paths import Workspace


def test_relative_disguised_forbidden_path(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Work on project",
        allowed_paths=["src/**", "**"],
        forbidden_paths=[".env"],
    )
    # Attempting to read .env disguised via relative components
    action = Action(type=ActionType.READ_FILE, target="src/../.env")
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.DENY


def test_command_chaining_bypass_attempt(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Run tests",
        allowed_commands=["pytest"],
    )
    # Attempting to execute an allowed command chained with a malicious one
    action = Action(type=ActionType.RUN_COMMAND, target="pytest && rm -rf /")
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.DENY


def test_agent_cannot_bypass_approval_with_metadata(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)
    contract = Contract(
        goal="Code refactor",
        allowed_paths=["src/**"],
        destructive_requires_approval=True,
    )
    # Agent sets metadata claiming pre-approval or no destructive action
    action = Action(
        type=ActionType.DELETE_FILE,
        target="src/critical.py",
        metadata={"pre_approved": True, "user_confirmed": True, "bypass_policy": True},
    )
    decision = engine.evaluate(action, contract)
    assert decision.decision == DecisionType.REQUIRE_APPROVAL
