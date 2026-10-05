"""Unit tests for SnapshotManager and rollback operations."""

from pathlib import Path

from anchor.actions.models import Action, ActionType
from anchor.snapshots.manager import SnapshotManager
from anchor.workspace.paths import Workspace


def test_rollback_modified_file(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    # Initial file
    auth_file = tmp_path / "src" / "auth.py"
    auth_file.parent.mkdir(parents=True)
    auth_file.write_text("ORIGINAL_CONTENT", encoding="utf-8")

    # Action that modifies file
    action = Action(
        type=ActionType.WRITE_FILE,
        target="src/auth.py",
        content="MUTATED_CONTENT",
    )

    # Create pre-execution snapshot
    snap_id = mgr.create_snapshot(action)
    assert snap_id is not None

    # Mutate file
    auth_file.write_text("MUTATED_CONTENT", encoding="utf-8")
    assert auth_file.read_text(encoding="utf-8") == "MUTATED_CONTENT"

    # Restore snapshot
    success = mgr.restore_snapshot(snap_id)
    assert success is True
    assert auth_file.read_text(encoding="utf-8") == "ORIGINAL_CONTENT"


def test_rollback_newly_created_file(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    new_file = tmp_path / "src" / "new_feature.py"
    assert not new_file.exists()

    action = Action(
        type=ActionType.WRITE_FILE,
        target="src/new_feature.py",
        content="NEW_FILE",
    )

    snap_id = mgr.create_snapshot(action)

    # File created
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.write_text("NEW_FILE", encoding="utf-8")
    assert new_file.exists()

    # Rollback should delete newly created file
    mgr.restore_snapshot(snap_id)
    assert not new_file.exists()


def test_rollback_deleted_file(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    target_file = tmp_path / "src" / "delete_me.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("DO_NOT_LOSE_ME", encoding="utf-8")

    action = Action(type=ActionType.DELETE_FILE, target="src/delete_me.py")
    snap_id = mgr.create_snapshot(action)

    # Simulate deletion
    target_file.unlink()
    assert not target_file.exists()

    # Rollback should restore deleted file
    mgr.restore_snapshot(snap_id)
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "DO_NOT_LOSE_ME"
