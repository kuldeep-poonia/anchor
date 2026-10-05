"""Example demonstrating programmatic usage of ANCHOR by an AI coding agent."""

from pathlib import Path

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.providers import get_provider
from anchor.risk.engine import RiskEngine
from anchor.snapshots.manager import SnapshotManager
from anchor.storage.database import AuditDatabase
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def run_coding_agent() -> None:
    # 1. Initialize workspace boundary
    workspace_dir = Path("./sample_project").resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)
    ws = Workspace(workspace_dir)

    print(f"[*] ANCHOR safety boundary established at: {ws.root}")

    # 2. Initialize engines and storage
    db = AuditDatabase(ws.root / ".anchor" / "audit.db")
    snapshot_mgr = SnapshotManager(ws)
    risk_engine = RiskEngine()
    policy_engine = PolicyEngine(ws, risk_engine)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    # 3. Provider derives contract from natural language goal
    # Defaults to LocalProvider (no API key required), or NebiusProvider if NEBIUS_API_KEY is set
    provider = get_provider()
    goal = "Refactor authentication service and add unit tests"
    contract = provider.generate_contract(goal)

    print("\n[+] Contract derived for goal:")
    print(f"    - Allowed paths: {contract.allowed_paths}")
    print(f"    - Forbidden paths: {contract.forbidden_paths}")
    print(f"    - Allowed commands: {contract.allowed_commands}")

    # 4. Agent proposes actions to complete the task
    candidate_actions = [
        # Action 1: Permitted code implementation
        Action(
            type=ActionType.WRITE_FILE,
            target="src/auth/service.py",
            content="# Safe authentication implementation\ndef is_valid_user(u: str) -> bool: return bool(u)\n",
        ),
        # Action 2: Forbidden attempt to read .env secrets
        Action(
            type=ActionType.READ_FILE,
            target=".env",
        ),
        # Action 3: Dangerous file deletion
        Action(
            type=ActionType.DELETE_FILE,
            target="src/auth/service.py",
        ),
    ]

    for idx, action in enumerate(candidate_actions, 1):
        print(f"\n--- Evaluating Candidate Action {idx}: {action.type.value} -> {action.target} ---")
        decision = policy_engine.evaluate(action, contract)
        print(f"    Decision: {decision.decision.value} (Risk: {decision.risk_level.value})")

        if decision.decision == DecisionType.ALLOW:
            # Create checkpoint
            snap_id = snapshot_mgr.create_snapshot(action)
            # Execute action
            res = executor.execute(action)
            # Verify outcome
            v_res = verifier.verify(action, res)
            print(f"    Executed: {res.success} | Verified: {v_res.verified}")
            db.record_decision(action, decision, "EXECUTED", snap_id)

        elif decision.decision == DecisionType.DENY:
            print(f"    BLOCKED: {decision.reason}")
            db.record_decision(action, decision, "DENIED")

        elif decision.decision == DecisionType.REQUIRE_APPROVAL:
            print(f"    APPROVAL REQUIRED: {decision.reason}")
            db.record_decision(action, decision, "PENDING_APPROVAL")


if __name__ == "__main__":
    run_coding_agent()
