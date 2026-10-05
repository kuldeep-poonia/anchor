"""Deterministic policy engine enforcing security rules and boundaries."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.risk.engine import RiskEngine, RiskLevel
from anchor.workspace.paths import InvalidPathError, Workspace, WorkspaceBoundaryError


class DecisionType(str, Enum):
    """Possible outcomes of policy evaluation."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicyDecision(BaseModel):
    """Result of policy evaluation for an action."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    decision: DecisionType
    risk_level: RiskLevel
    reason: str
    target: str = Field(default="")


class PolicyEngine:
    """Evaluates candidate actions using strict deterministic rules."""

    def __init__(self, workspace: Workspace, risk_engine: RiskEngine | None = None) -> None:
        self.workspace = workspace
        self.risk_engine = risk_engine or RiskEngine()

    def evaluate(self, action: Action, contract: Contract) -> PolicyDecision:
        """
        Evaluate an action against the contract and workspace boundaries.

        Evaluation precedence:
        1. Workspace boundary validation (hard DENY)
        2. Contract forbidden rules (hard DENY)
        3. Contract allowed rules (DENY if not explicitly allowed - fail closed)
        4. Destructive / risk approval check (REQUIRE_APPROVAL)
        5. ALLOW
        """
        risk = self.risk_engine.calculate_risk(action, self.workspace, contract)

        # 1. Workspace boundary validation for file operations
        if action.type in {ActionType.READ_FILE, ActionType.WRITE_FILE, ActionType.DELETE_FILE}:
            try:
                self.workspace.resolve(action.target)
            except WorkspaceBoundaryError:
                return PolicyDecision(
                    action_id=action.id,
                    decision=DecisionType.DENY,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Target path '{action.target}' escapes the workspace boundary",
                    target=action.target,
                )
            except InvalidPathError as err:
                return PolicyDecision(
                    action_id=action.id,
                    decision=DecisionType.DENY,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Target path is invalid: {err}",
                    target=action.target,
                )

            rel_path = self.workspace.relative(action.target)

            # 2. Forbidden path check
            if contract.is_path_forbidden(rel_path):
                return PolicyDecision(
                    action_id=action.id,
                    decision=DecisionType.DENY,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Path '{rel_path}' violates forbidden contract rules",
                    target=rel_path,
                )

            # 3. Allowed path check (fail closed)
            if not contract.is_path_allowed(rel_path):
                return PolicyDecision(
                    action_id=action.id,
                    decision=DecisionType.DENY,
                    risk_level=risk,
                    reason=f"Path '{rel_path}' is not permitted by allowed paths in contract",
                    target=rel_path,
                )

        # 4. Command validation
        elif action.type == ActionType.RUN_COMMAND:
            if not contract.is_command_allowed(action.target):
                return PolicyDecision(
                    action_id=action.id,
                    decision=DecisionType.DENY,
                    risk_level=risk,
                    reason=f"Command '{action.target}' is not permitted by allowed commands",
                    target=action.target,
                )

        # 5. Destructive operations approval check
        if action.type == ActionType.DELETE_FILE and contract.destructive_requires_approval:
            return PolicyDecision(
                action_id=action.id,
                decision=DecisionType.REQUIRE_APPROVAL,
                risk_level=risk,
                reason="Destructive file deletion requires interactive user approval",
                target=action.target,
            )

        # 6. Critical risk approval check
        if risk == RiskLevel.CRITICAL:
            return PolicyDecision(
                action_id=action.id,
                decision=DecisionType.REQUIRE_APPROVAL,
                risk_level=risk,
                reason=f"Action carries {risk.value} risk and requires user approval",
                target=action.target,
            )

        # 7. Allowed
        return PolicyDecision(
            action_id=action.id,
            decision=DecisionType.ALLOW,
            risk_level=risk,
            reason="Action conforms to contract policies and safety limits",
            target=action.target,
        )
