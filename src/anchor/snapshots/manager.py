"""Lightweight local snapshot and rollback manager for atomic reversibility."""

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from anchor.actions.models import Action, ActionType
from anchor.workspace.paths import Workspace, WorkspaceBoundaryError


class SnapshotError(Exception):
    """Raised when snapshot creation or rollback encounters an error."""


class FileState(BaseModel):
    """Previous state of a file prior to action execution."""
    model_config = ConfigDict(extra="forbid")

    rel_path: str
    existed: bool
    backup_file: str | None = None
    sha256: str | None = None


class SnapshotManifest(BaseModel):
    """Metadata manifest describing an ANCHOR recovery checkpoint."""
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    action_id: str
    action_type: str
    target: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    files: list[FileState] = Field(default_factory=list)


def _compute_sha256(path: Path) -> str:
    """Compute sha256 checksum of a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class SnapshotManager:
    """Manages pre-mutation checkpoints and state restorations."""

    def __init__(self, workspace: Workspace, snapshot_dir: Path | None = None) -> None:
        self.workspace = workspace
        self.snapshot_dir = snapshot_dir or (self.workspace.root / ".anchor" / "snapshots")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(
        self,
        action: Action,
        affected_paths: list[str] | None = None,
    ) -> str:
        """
        Create a point-in-time snapshot of files affected by an action.

        Returns snapshot_id.
        """
        paths_to_track: list[str] = []
        if affected_paths:
            paths_to_track.extend(affected_paths)
        elif action.type in {ActionType.WRITE_FILE, ActionType.DELETE_FILE}:
            paths_to_track.append(action.target)

        snapshot_id = f"snap_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}"
        snap_path = self.snapshot_dir / snapshot_id
        files_backup_dir = snap_path / "files"
        files_backup_dir.mkdir(parents=True, exist_ok=True)

        tracked_states: list[FileState] = []

        for idx, p in enumerate(paths_to_track):
            try:
                resolved = self.workspace.resolve(p)
            except WorkspaceBoundaryError as err:
                raise SnapshotError(f"Cannot snapshot path outside workspace: {p}") from err

            rel_posix = self.workspace.relative(p)

            if resolved.exists() and resolved.is_file():
                backup_name = f"backup_{idx}"
                dest = files_backup_dir / backup_name
                shutil.copy2(resolved, dest)
                sha = _compute_sha256(resolved)
                tracked_states.append(
                    FileState(
                        rel_path=rel_posix,
                        existed=True,
                        backup_file=backup_name,
                        sha256=sha,
                    )
                )
            else:
                # File does not exist yet (will be created by action)
                tracked_states.append(
                    FileState(
                        rel_path=rel_posix,
                        existed=False,
                        backup_file=None,
                        sha256=None,
                    )
                )

        manifest = SnapshotManifest(
            snapshot_id=snapshot_id,
            action_id=action.id,
            action_type=action.type.value,
            target=action.target,
            files=tracked_states,
        )

        manifest_file = snap_path / "manifest.json"
        manifest_file.write_text(
            json.dumps(manifest.model_dump(), indent=2),
            encoding="utf-8",
        )

        # Update latest pointer
        latest_file = self.snapshot_dir / "LATEST"
        latest_file.write_text(snapshot_id, encoding="utf-8")

        return snapshot_id

    def restore_snapshot(self, snapshot_id: str | None = None) -> bool:
        """
        Restore workspace state to specified or most recent snapshot.

        Enforces strict workspace containment for all restored paths.
        """
        target_id = snapshot_id
        if not target_id:
            latest_file = self.snapshot_dir / "LATEST"
            if not latest_file.exists():
                return False
            target_id = latest_file.read_text(encoding="utf-8").strip()

        snap_path = self.snapshot_dir / target_id
        manifest_file = snap_path / "manifest.json"
        if not manifest_file.exists():
            raise SnapshotError(f"Snapshot manifest not found for {target_id}")

        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest = SnapshotManifest(**data)
        except Exception as err:
            raise SnapshotError(f"Corrupted snapshot manifest: {err}") from err

        files_backup_dir = snap_path / "files"

        # Rollback each recorded file
        for state in manifest.files:
            # Enforce path containment before modifying
            try:
                target_path = self.workspace.resolve(state.rel_path)
            except WorkspaceBoundaryError as err:
                raise SnapshotError(
                    f"Refusing to restore path outside workspace: {state.rel_path}"
                ) from err

            if state.existed:
                # File previously existed: restore backup
                if not state.backup_file:
                    continue
                backup_path = files_backup_dir / state.backup_file
                if not backup_path.exists():
                    raise SnapshotError(
                        f"Missing backup file {state.backup_file} for {state.rel_path}"
                    )

                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target_path)
            else:
                # File was newly created by the action: remove it
                if target_path.exists():
                    if target_path.is_file():
                        target_path.unlink()
                    elif target_path.is_dir():
                        shutil.rmtree(target_path)

        return True

    def list_snapshots(self) -> list[str]:
        """List all available snapshot IDs sorted by creation time."""
        if not self.snapshot_dir.exists():
            return []
        entries = []
        for item in self.snapshot_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                entries.append(item.name)
        entries.sort()
        return entries
