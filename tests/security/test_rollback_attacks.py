"""Adversarial security tests for snapshot and rollback attacks."""

import json
from pathlib import Path

import pytest

from anchor.actions.models import Action, ActionType
from anchor.snapshots.manager import SnapshotError, SnapshotManager
from anchor.workspace.paths import Workspace


def test_rejects_snapshot_outside_workspace(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    action = Action(type=ActionType.WRITE_FILE, target="../outside.txt")
    with pytest.raises(SnapshotError, match="outside workspace"):
        mgr.create_snapshot(action)


def test_rejects_manifest_path_escape_attack(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    # Legitimate snapshot
    legit_file = tmp_path / "valid.txt"
    legit_file.write_text("valid", encoding="utf-8")
    action = Action(type=ActionType.WRITE_FILE, target="valid.txt")
    snap_id = mgr.create_snapshot(action)

    # Attacker tampers with manifest to inject an external escape path
    manifest_path = mgr.snapshot_dir / snap_id / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["files"].append({
        "rel_path": "../../escaped_attack.txt",
        "existed": False,
        "backup_file": None,
        "sha256": None,
    })
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    # Restore must reject tampering and prevent writing outside workspace
    with pytest.raises(SnapshotError, match="outside workspace"):
        mgr.restore_snapshot(snap_id)


def test_handles_corrupt_manifest_gracefully(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    mgr = SnapshotManager(ws)

    f = tmp_path / "app.py"
    f.write_text("print(1)", encoding="utf-8")
    snap_id = mgr.create_snapshot(Action(type=ActionType.WRITE_FILE, target="app.py"))

    # Corrupt manifest
    manifest_path = mgr.snapshot_dir / snap_id / "manifest.json"
    manifest_path.write_text("{corrupt json...", encoding="utf-8")

    with pytest.raises(SnapshotError, match="Corrupted snapshot manifest"):
        mgr.restore_snapshot(snap_id)
