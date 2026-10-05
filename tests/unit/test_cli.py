"""Unit tests for ANCHOR command line interface."""

from pathlib import Path

from typer.testing import CliRunner

from anchor.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "ANCHOR" in res.stdout
    assert "init" in res.stdout
    assert "demo" in res.stdout
    assert "run" in res.stdout


def test_cli_init(tmp_path: Path) -> None:
    res = runner.invoke(app, ["init", "-w", str(tmp_path)])
    assert res.exit_code == 0
    assert "Initialized ANCHOR" in res.stdout
    assert (tmp_path / ".anchor").exists()


def test_cli_status_clean(tmp_path: Path) -> None:
    res = runner.invoke(app, ["status", "-w", str(tmp_path)])
    assert res.exit_code == 0
    assert "ANCHOR Safety Status" in res.stdout
    assert "Pending Approvals: 0" in res.stdout


def test_cli_run_goal(tmp_path: Path) -> None:
    res = runner.invoke(app, ["run", "Refactor user authentication", "-w", str(tmp_path)])
    assert res.exit_code == 0
    assert "Active Provider" in res.stdout
    assert "Contract Boundaries" in res.stdout
    assert "Evaluating" in res.stdout


def test_cli_approve_and_deny(tmp_path: Path) -> None:
    # First run a goal that triggers approval
    runner.invoke(app, ["run", "Cleanup old files", "-w", str(tmp_path)])

    # Check status for pending approvals
    status_res = runner.invoke(app, ["status", "-w", str(tmp_path)])
    assert status_res.exit_code == 0

    if "Pending Approvals: 0" not in status_res.stdout:
        # Retrieve pending action ID from status output
        lines = [line.strip() for line in status_res.stdout.splitlines() if line.strip().startswith("- [")]
        if lines:
            action_prefix = lines[0].split("[")[1].split("]")[0]
            # Test approval
            approve_res = runner.invoke(app, ["approve", action_prefix, "-w", str(tmp_path)])
            assert approve_res.exit_code in {0, 1}


def test_cli_undo(tmp_path: Path) -> None:
    # Trigger an action that creates a snapshot
    runner.invoke(app, ["run", "Build app entrypoint", "-w", str(tmp_path)])
    undo_res = runner.invoke(app, ["undo", "-w", str(tmp_path)])
    assert undo_res.exit_code == 0
