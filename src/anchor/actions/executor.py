"""Controlled action execution engine with safety boundaries."""

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from anchor.actions.models import Action, ActionType
from anchor.workspace.paths import Workspace, WorkspaceBoundaryError

DEFAULT_COMMAND_TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_CHAR_LIMIT = 500_000
MAX_READ_SIZE_BYTES = 10_000_000

# Environment variables to redact from subprocesses
SENSITIVE_ENV_VARS = {
    "NEBIUS_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
}


class ActionResult(BaseModel):
    """Structured result of executing an action."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    success: bool
    output: str = ""
    error: str | None = None
    exit_code: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionExecutor:
    """Executes validated actions within strict containment boundaries."""

    def __init__(
        self,
        workspace: Workspace,
        default_timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        max_output_chars: int = MAX_OUTPUT_CHAR_LIMIT,
    ) -> None:
        self.workspace = workspace
        self.default_timeout = default_timeout
        self.max_output_chars = max_output_chars

    def execute(self, action: Action) -> ActionResult:
        """Execute a validated action."""
        if action.type == ActionType.READ_FILE:
            return self._execute_read(action)
        if action.type == ActionType.WRITE_FILE:
            return self._execute_write(action)
        if action.type == ActionType.DELETE_FILE:
            return self._execute_delete(action)
        if action.type == ActionType.RUN_COMMAND:
            return self._execute_command(action)
        return ActionResult(
            action_id=action.id,
            success=False,
            error=f"Unsupported action type: {action.type}",
        )

    def _execute_read(self, action: Action) -> ActionResult:
        """Read file safely within workspace."""
        try:
            target_path = self.workspace.resolve(action.target)
            if not target_path.exists():
                return ActionResult(
                    action_id=action.id,
                    success=False,
                    error=f"File not found: {action.target}",
                )
            if not target_path.is_file():
                return ActionResult(
                    action_id=action.id,
                    success=False,
                    error=f"Target is not a file: {action.target}",
                )
            if target_path.stat().st_size > MAX_READ_SIZE_BYTES:
                return ActionResult(
                    action_id=action.id,
                    success=False,
                    error="File size exceeds maximum readable threshold (10 MB)",
                )

            content = target_path.read_text(encoding="utf-8", errors="replace")
            return ActionResult(
                action_id=action.id,
                success=True,
                output=content,
            )
        except (WorkspaceBoundaryError, OSError) as err:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Read failed: {err}",
            )

    def _execute_write(self, action: Action) -> ActionResult:
        """Write file atomically within workspace."""
        try:
            target_path = self.workspace.resolve(action.target)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            content = action.content or ""

            # Atomic write via temporary file in the same parent directory
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(target_path.parent),
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            # Atomic rename / replace
            os.replace(tmp_path, target_path)

            return ActionResult(
                action_id=action.id,
                success=True,
                output=f"Successfully wrote {len(content)} characters to {action.target}",
            )
        except (WorkspaceBoundaryError, OSError) as err:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Write failed: {err}",
            )

    def _execute_delete(self, action: Action) -> ActionResult:
        """Delete file or directory safely within workspace."""
        try:
            target_path = self.workspace.resolve(action.target)
            if not target_path.exists():
                return ActionResult(
                    action_id=action.id,
                    success=True,
                    output=f"Target {action.target} already absent",
                )

            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()

            return ActionResult(
                action_id=action.id,
                success=True,
                output=f"Successfully deleted {action.target}",
            )
        except (WorkspaceBoundaryError, OSError) as err:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Deletion failed: {err}",
            )

    def _execute_command(self, action: Action) -> ActionResult:
        """Execute command in controlled subprocess with timeout and sanitized environment."""
        timeout = float(action.metadata.get("timeout", self.default_timeout))

        # Build clean environment without sensitive credentials
        clean_env = os.environ.copy()
        for var in SENSITIVE_ENV_VARS:
            clean_env.pop(var, None)

        try:
            if action.args:
                cmd_args = [action.target, *action.args]
            else:
                raw_parts = shlex.split(action.target, posix=False)
                cmd_args = [
                    p[1:-1]
                    if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'"))
                    else p
                    for p in raw_parts
                ]

            proc = subprocess.run(
                cmd_args,
                cwd=str(self.workspace.root),
                env=clean_env,
                timeout=timeout,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )

            stdout = proc.stdout[:self.max_output_chars] if proc.stdout else ""
            stderr = proc.stderr[:self.max_output_chars] if proc.stderr else ""

            is_success = proc.returncode == 0
            return ActionResult(
                action_id=action.id,
                success=is_success,
                output=stdout,
                error=stderr if not is_success else None,
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Command timed out after {timeout} seconds",
                exit_code=-1,
            )
        except (OSError, ValueError) as err:
            return ActionResult(
                action_id=action.id,
                success=False,
                error=f"Command execution failed: {err}",
                exit_code=1,
            )
