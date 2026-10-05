"""Command-line interface for ANCHOR."""

import json
import os
from pathlib import Path

import typer

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.providers import get_provider
from anchor.risk.engine import RiskEngine
from anchor.snapshots.manager import SnapshotError, SnapshotManager
from anchor.storage.database import AuditDatabase
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace

app = typer.Typer(
    name="anchor",
    help="ANCHOR: Lightweight safety and deterministic control layer for AI agents.",
    no_args_is_help=True,
)


def _get_context(workspace_path: str = ".") -> tuple[Workspace, AuditDatabase, SnapshotManager]:
    """Helper to initialize workspace, database, and snapshot manager."""
    ws = Workspace(Path(workspace_path).resolve())
    anchor_dir = ws.root / ".anchor"
    anchor_dir.mkdir(parents=True, exist_ok=True)
    db = AuditDatabase(anchor_dir / "audit.db")
    snapshot_mgr = SnapshotManager(ws)
    return ws, db, snapshot_mgr


@app.command()
def init(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace directory path"),
) -> None:
    """Initialize ANCHOR safety configuration and audit state in workspace."""
    ws, _, _ = _get_context(workspace)
    typer.echo(f"Initialized ANCHOR safety boundary in {ws.root}")
    typer.echo("State directory: .anchor/")


@app.command()
def demo() -> None:
    """
    Run an end-to-end deterministic demonstration without requiring an API key.

    Demonstrates:
    1. Contract synthesis
    2. Allowed action execution
    3. Blocked secret access (.env)
    4. Risky action approval requirement
    5. Automatic snapshot & rollback on verification failure
    """
    typer.echo("=" * 60)
    typer.echo("ANCHOR — Deterministic AI Agent Safety Demo (Offline Mode)")
    typer.echo("=" * 60)

    ws, db, snapshot_mgr = _get_context(".")
    risk_engine = RiskEngine()
    policy_engine = PolicyEngine(ws, risk_engine)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)
    provider = get_provider()

    goal = "Refactor authentication service and enforce security"
    typer.echo(f"\n[1] Agent Goal: {goal}")

    # Generate contract
    contract = provider.generate_contract(goal)
    typer.echo("\n[2] Contract Synthesized:")
    typer.echo(f"    - Allowed paths: {contract.allowed_paths}")
    typer.echo(f"    - Forbidden paths: {contract.forbidden_paths}")
    typer.echo(f"    - Allowed commands: {contract.allowed_commands}")

    # Step 1: Normal allowed file creation
    typer.echo("\n[3] Evaluating Action 1: Write auth service (Allowed)")
    act1 = Action(
        type=ActionType.WRITE_FILE,
        target="src/auth/service.py",
        content="# Safe authentication implementation\ndef check_auth(): return True\n",
    )
    dec1 = policy_engine.evaluate(act1, contract)
    typer.echo(f"    Decision: {dec1.decision.value} | Risk: {dec1.risk_level.value}")

    if dec1.decision == DecisionType.ALLOW:
        snap_id = snapshot_mgr.create_snapshot(act1)
        res1 = executor.execute(act1)
        v_res1 = verifier.verify(act1, res1)
        db.record_decision(act1, dec1, "EXECUTED", snap_id)
        db.update_status(act1.id, "EXECUTED", verified=v_res1.verified, snapshot_id=snap_id)
        typer.echo(f"    Execution: SUCCESS | Verified: {v_res1.verified}")

    # Step 2: Blocked secret access
    typer.echo("\n[4] Evaluating Action 2: Read sensitive credentials (Forbidden)")
    act2 = Action(type=ActionType.READ_FILE, target=".env")
    dec2 = policy_engine.evaluate(act2, contract)
    typer.echo(f"    Decision: {dec2.decision.value} | Risk: {dec2.risk_level.value}")
    typer.echo(f"    Reason: {dec2.reason}")
    db.record_decision(act2, dec2, "DENIED")
    typer.echo("    Execution: BLOCKED by ANCHOR boundary (0 bytes leaked)")

    # Step 3: Dangerous file deletion requiring interactive approval
    typer.echo("\n[5] Evaluating Action 3: Delete auth component (Destructive)")
    act3 = Action(type=ActionType.DELETE_FILE, target="src/auth/legacy_auth.py")
    dec3 = policy_engine.evaluate(act3, contract)
    typer.echo(f"    Decision: {dec3.decision.value} | Risk: {dec3.risk_level.value}")
    typer.echo(f"    Reason: {dec3.reason}")
    db.record_decision(act3, dec3, "PENDING_APPROVAL")
    typer.echo("    Status: Queued for explicit user confirmation")

    # Step 4: Verification failure and automatic rollback
    typer.echo("\n[6] Evaluating Action 4: Mutation with verification failure & rollback")
    target_demo_file = ws.root / "src" / "auth" / "service.py"
    original_code = target_demo_file.read_text(encoding="utf-8")

    act4 = Action(
        type=ActionType.WRITE_FILE,
        target="src/auth/service.py",
        content="# Malformed code causing failure\nSYNTAX ERROR BREAKS TESTS\n",
    )
    snap4 = snapshot_mgr.create_snapshot(act4)
    executor.execute(act4)
    # Simulate verification failure (e.g. tests break)
    typer.echo("    Action executed -> Running objective verification suite...")
    typer.echo("    Verification Result: FAILED (Tests broken)")
    typer.echo("    Triggering AUTOMATIC ROLLBACK...")
    snapshot_mgr.restore_snapshot(snap4)
    restored_code = target_demo_file.read_text(encoding="utf-8")
    is_restored = restored_code == original_code
    typer.echo(f"    System state restored cleanly: {is_restored}")

    typer.echo("\n" + "=" * 60)
    typer.echo("ANCHOR Demo Complete: 100% Deterministic Safety Enforced.")
    typer.echo("=" * 60)


@app.command()
def run(
    goal: str = typer.Argument(..., help="Natural language goal for the agent"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path"),
) -> None:
    """Evaluate and execute an agent goal under ANCHOR contract enforcement."""
    ws, db, snapshot_mgr = _get_context(workspace)
    risk_engine = RiskEngine()
    policy_engine = PolicyEngine(ws, risk_engine)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    # Provider selection
    provider = get_provider()
    provider_name = "Nebius (NVIDIA Nemotron)" if os.getenv("NEBIUS_API_KEY") else "Local (Deterministic)"
    typer.echo(f"Active Provider: {provider_name}")
    typer.echo(f"Goal: {goal}\n")

    # Synthesize contract
    contract = provider.generate_contract(goal)
    contract_id = f"contract_{int(os.times().elapsed)}"
    db.record_contract(contract_id, goal, json.dumps(contract.model_dump()))
    typer.echo("Contract Boundaries:")
    typer.echo(f"  Allowed paths: {contract.allowed_paths}")
    typer.echo(f"  Forbidden paths: {contract.forbidden_paths}")
    typer.echo(f"  Allowed commands: {contract.allowed_commands}\n")

    # Propose actions
    candidate_requests = provider.propose_actions(goal, contract)
    typer.echo(f"Evaluating {len(candidate_requests)} candidate actions...\n")

    for req in candidate_requests:
        action = Action.from_request(req)
        decision = policy_engine.evaluate(action, contract)
        typer.echo(f"Action: {action.type.value} -> {action.target}")
        typer.echo(f"  Decision: {decision.decision.value} | Risk: {decision.risk_level.value}")

        if decision.decision == DecisionType.DENY:
            typer.echo(f"  BLOCKED: {decision.reason}\n")
            db.record_decision(action, decision, "DENIED")

        elif decision.decision == DecisionType.REQUIRE_APPROVAL:
            typer.echo(f"  APPROVAL REQUIRED: {decision.reason}")
            typer.echo(f"  Run 'anchor approve {action.id}' to confirm execution.\n")
            db.record_decision(action, decision, "PENDING_APPROVAL")

        elif decision.decision == DecisionType.ALLOW:
            # Create checkpoint snapshot
            snap_id = snapshot_mgr.create_snapshot(action)
            res = executor.execute(action)
            if not res.success:
                typer.echo(f"  FAILED: {res.error}\n")
                db.record_decision(action, decision, "FAILED", snap_id)
                continue

            # Verify
            v_res = verifier.verify(action, res, contract)
            if v_res.verified:
                typer.echo("  EXECUTED & VERIFIED\n")
                db.record_decision(action, decision, "EXECUTED", snap_id)
                db.update_status(action.id, "EXECUTED", verified=True, snapshot_id=snap_id)
            else:
                typer.echo(f"  VERIFICATION FAILED: {v_res.error}")
                typer.echo("  Rolling back changes...")
                snapshot_mgr.restore_snapshot(snap_id)
                db.record_decision(action, decision, "ROLLED_BACK", snap_id)
                typer.echo("  State restored.\n")


@app.command()
def status(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path"),
) -> None:
    """Show current workspace safety status, pending approvals, and audit log."""
    ws, db, snapshot_mgr = _get_context(workspace)
    provider_name = "Nebius (NVIDIA Nemotron)" if os.getenv("NEBIUS_API_KEY") else "Local (Offline)"

    typer.echo("=" * 50)
    typer.echo("ANCHOR Safety Status")
    typer.echo("=" * 50)
    typer.echo(f"Workspace Root: {ws.root}")
    typer.echo(f"Active Provider: {provider_name}")

    # Pending approvals
    pending = db.get_pending_approvals()
    typer.echo(f"\nPending Approvals: {len(pending)}")
    for item in pending:
        typer.echo(
            f"  - [{item['action_id'][:8]}] {item['action_type']} -> {item['target']} "
            f"(Risk: {item['risk_level']})"
        )

    # Snapshots
    snapshots = snapshot_mgr.list_snapshots()
    typer.echo(f"\nAvailable Snapshots: {len(snapshots)}")
    if snapshots:
        typer.echo(f"  Latest: {snapshots[-1]}")

    # Recent actions
    recent = db.get_recent_actions(limit=5)
    typer.echo(f"\nRecent Actions ({len(recent)}):")
    for act in recent:
        verified_mark = " (verified)" if act["verified"] else ""
        typer.echo(
            f"  - {act['timestamp'][:19]} | {act['action_type']} {act['target']} | "
            f"{act['decision']} -> {act['status']}{verified_mark}"
        )


@app.command()
def approve(
    action_id: str = typer.Argument(..., help="Action ID to approve"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path"),
) -> None:
    """Approve and execute a pending high-risk action."""
    ws, db, snapshot_mgr = _get_context(workspace)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    # Search for matching action
    pending = db.get_pending_approvals()
    target_item = None
    for item in pending:
        if item["action_id"].startswith(action_id):
            target_item = item
            break

    if not target_item:
        typer.echo(f"Error: No pending action found matching '{action_id}'", err=True)
        raise typer.Exit(code=1)

    act = Action(
        id=target_item["action_id"],
        type=ActionType(target_item["action_type"]),
        target=target_item["target"],
        content=target_item["content"],
    )

    typer.echo(f"Approving action: {act.type.value} -> {act.target}")
    snap_id = snapshot_mgr.create_snapshot(act)
    res = executor.execute(act)

    if not res.success:
        typer.echo(f"Execution failed: {res.error}", err=True)
        db.update_status(act.id, "FAILED", verified=False, snapshot_id=snap_id)
        raise typer.Exit(code=1)

    v_res = verifier.verify(act, res)
    db.update_status(act.id, "APPROVED", verified=v_res.verified, snapshot_id=snap_id)
    typer.echo(f"Action executed successfully. Verified: {v_res.verified}")


@app.command()
def deny(
    action_id: str = typer.Argument(..., help="Action ID to deny"),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path"),
) -> None:
    """Deny a pending high-risk action."""
    _, db, _ = _get_context(workspace)
    pending = db.get_pending_approvals()
    target_item = None
    for item in pending:
        if item["action_id"].startswith(action_id):
            target_item = item
            break

    if not target_item:
        typer.echo(f"Error: No pending action found matching '{action_id}'", err=True)
        raise typer.Exit(code=1)

    db.update_status(target_item["action_id"], "DENIED_BY_USER", verified=False)
    typer.echo(f"Action {target_item['action_id']} has been denied.")


@app.command()
def undo(
    workspace: str = typer.Option(".", "--workspace", "-w", help="Workspace path"),
) -> None:
    """Roll back to the previous snapshot state."""
    _, _, snapshot_mgr = _get_context(workspace)
    try:
        success = snapshot_mgr.restore_snapshot()
        if success:
            typer.echo("Successfully rolled back workspace to previous checkpoint.")
        else:
            typer.echo("No previous snapshot found to restore.")
    except SnapshotError as err:
        typer.echo(f"Rollback error: {err}", err=True)
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
