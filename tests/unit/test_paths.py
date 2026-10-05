"""Unit tests for workspace paths and resolution."""

from pathlib import Path

import pytest

from anchor.workspace.paths import InvalidPathError, Workspace


def test_resolve_relative_path(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    resolved = ws.resolve("src/auth/login.py")
    assert resolved == (tmp_path / "src" / "auth" / "login.py").resolve()
    assert ws.relative("src/auth/login.py") == "src/auth/login.py"


def test_resolve_nested_existing_path(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    sub = tmp_path / "data"
    sub.mkdir()
    f = sub / "test.txt"
    f.write_text("content", encoding="utf-8")

    resolved = ws.resolve("data/test.txt")
    assert resolved == f.resolve()
    assert ws.contains("data/test.txt") is True


def test_rejects_null_byte_path(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(InvalidPathError):
        ws.resolve("src/file\x00.py")


def test_rejects_alternate_data_stream(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(InvalidPathError):
        ws.resolve("secret.txt:hidden")
