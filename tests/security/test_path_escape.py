"""Security adversarial tests for path traversal and workspace boundary escapes."""

from pathlib import Path

import pytest

from anchor.workspace.paths import Workspace, WorkspaceBoundaryError


def test_rejects_parent_traversal(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(WorkspaceBoundaryError):
        ws.resolve("../outside.txt")


def test_rejects_deep_parent_traversal(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(WorkspaceBoundaryError):
        ws.resolve("src/../../../../etc/passwd")


def test_rejects_absolute_path_outside_workspace(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    outside = tmp_path.parent / "sensitive_outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(WorkspaceBoundaryError):
        ws.resolve(str(outside))


def test_contains_returns_false_for_escapes(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    assert ws.contains("../escaped.py") is False
    assert ws.contains("a/b/../../../../escape") is False
