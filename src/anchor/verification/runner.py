"""Independent verification engine enforcing objective ground truth."""

import os
import shlex
import subprocess
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from anchor.actions.executor import SENSITIVE_ENV_VARS, ActionResult
from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.workspace.paths import Workspace, WorkspaceBoundaryError

DEFAULT_VERIFY_TIMEOUT_SECONDS = 30.0


class VerificationResult(BaseModel):
    """Objective result of post-execution verification."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    verified: bool
    command: str | None = None
    exit_code: int | None = None
    output: str = ""
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class VerificationRunner:
    """Executes objective verification independent of agent claims."""

    def __init__(
        self,
        workspace: Workspace,
        default_timeout: float = DEFAULT_VERIFY_TIMEOUT_SECONDS,
    ) -> None:
        self.workspace = workspace
        self.default_timeout = default_timeout

    def verify(
        self,
        action: Action,
        action_result: ActionResult,
        contract: Contract | None = None,
    ) -> VerificationResult:
        """
        Verify action results objectively.

        Agent claims are ignored. Checks disk state and executes
        verification commands if defined in the contract.
        """
        # If action execution itself failed, verification fails
        if not action_result.success:
            return VerificationResult(
                verified=False,
                error=f"Action execution failed: {action_result.error}",
            )

        # File state verification
        if action.type == ActionType.WRITE_FILE:
            try:
                target_path = self.workspace.resolve(action.target)
                if not target_path.exists():
                    return VerificationResult(
                        verified=False,
                        error=f"Expected written file does not exist: {action.target}",
                    )
                if action.content is not None and not target_path.is_file():
                    return VerificationResult(
                        verified=False,
                        error=f"Target exists but is not a regular file: {action.target}",
                    )
            except WorkspaceBoundaryError as err:
                return VerificationResult(
                    verified=False,
                    error=f"Path boundary violation during verification: {err}",
                )

        elif action.type == ActionType.DELETE_FILE:
            try:
                target_path = self.workspace.resolve(action.target)
                if target_path.exists():
                    return VerificationResult(
                        verified=False,
                        error=f"File still exists after deletion: {action.target}",
                    )
            except WorkspaceBoundaryError as err:
                return VerificationResult(
                    verified=False,
                    error=f"Path boundary violation during verification: {err}",
                )

        # Run contract verification command if specified
        if contract and contract.verification_command:
            return self._run_verification_command(contract.verification_command)

        # Default verification succeeded
        return VerificationResult(
            verified=True,
            output="Action verified against filesystem expectations",
        )

    def _run_verification_command(self, cmd_string: str) -> VerificationResult:
        """Execute independent verification subprocess."""
        clean_env = os.environ.copy()
        for var in SENSITIVE_ENV_VARS:
            clean_env.pop(var, None)

        try:
            raw_parts = shlex.split(cmd_string, posix=False)
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
                timeout=self.default_timeout,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )

            is_verified = proc.returncode == 0
            return VerificationResult(
                verified=is_verified,
                command=cmd_string,
                exit_code=proc.returncode,
                output=proc.stdout,
                error=proc.stderr if not is_verified else None,
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                verified=False,
                command=cmd_string,
                exit_code=-1,
                error=f"Verification command timed out after {self.default_timeout}s",
            )
        except (OSError, ValueError) as err:
            return VerificationResult(
                verified=False,
                command=cmd_string,
                exit_code=1,
                error=f"Verification runner error: {err}",
            )
