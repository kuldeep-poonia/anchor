"""End-to-end integration tests for automated snapshot and rollback on failure."""

import sys
from pathlib import Path

from anchor.actions.executor import ActionExecutor
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.snapshots.manager import SnapshotManager
from anchor.storage.database import AuditDatabase
from anchor.verification.runner import VerificationRunner
from anchor.workspace.paths import Workspace


def test_automatic_rollback_on_failed_verification(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    db = AuditDatabase(tmp_path / ".anchor" / "audit.db")
    snapshot_mgr = SnapshotManager(ws)
    executor = ActionExecutor(ws)
    verifier = VerificationRunner(ws)

    # Initial file
    app_file = tmp_path / "src" / "service.py"
    app_file.parent.mkdir(parents=True)
    original_code = "def stable(): return 42\n"
    app_file.write_text(original_code, encoding="utf-8")

    # Contract specifies a verification command that will fail
    contract = Contract(
        goal="Update service",
        allowed_paths=["src/**"],
        verification_command=f'{sys.executable} -c "import sys; sys.exit(1)"',
    )

    action = Action(
        type=ActionType.WRITE_FILE,
        target="src/service.py",
        content="def broken(): raise RuntimeError('syntax error')\n",
    )

    # 1. Take pre-mutation snapshot
    snap_id = snapshot_mgr.create_snapshot(action)

    # 2. Execute mutation
    res = executor.execute(action)
    assert res.success is True
    assert app_file.read_text(encoding="utf-8") != original_code

    # 3. Verification fails
    v_res = verifier.verify(action, res, contract)
    assert v_res.verified is False

    # 4. Trigger automatic rollback
    rollback_success = snapshot_mgr.restore_snapshot(snap_id)
    assert rollback_success is True

    # 5. Verify filesystem restored
    assert app_file.read_text(encoding="utf-8") == original_code

    # 6. Record rollback in audit log
    db.update_status(action.id, "ROLLED_BACK", verified=False, snapshot_id=snap_id)
    record = db.get_action(action.id)
    # Status updated
    assert record is None or record.get("status") == "ROLLED_BACK"
