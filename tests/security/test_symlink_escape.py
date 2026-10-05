"""Security adversarial tests for symlink escapes."""

import os
from pathlib import Path

import pytest

from anchor.workspace.paths import Workspace, WorkspaceBoundaryError


def test_rejects_symlink_pointing_outside(tmp_path: Path) -> None:
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.env"
    secret_file.write_text("API_KEY=leak", encoding="utf-8")

    link_path = ws_dir / "leak_link"
    try:
        os.symlink(str(secret_file), str(link_path))
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted or supported in this environment")

    ws = Workspace(ws_dir)
    with pytest.raises(WorkspaceBoundaryError):
        ws.resolve("leak_link")


def test_rejects_symlink_directory_escape(tmp_path: Path) -> None:
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret_file = outside_dir / "target.txt"
    secret_file.write_text("outside", encoding="utf-8")

    link_dir = ws_dir / "outside_link"
    try:
        os.symlink(str(outside_dir), str(link_dir), target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted or supported in this environment")

    ws = Workspace(ws_dir)
    with pytest.raises(WorkspaceBoundaryError):
        ws.resolve("outside_link/target.txt")
