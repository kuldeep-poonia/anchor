"""Deterministic risk classification for candidate actions."""

import shlex
from enum import Enum
from pathlib import PurePosixPath

from anchor.actions.models import Action, ActionType
from anchor.contracts.models import Contract
from anchor.workspace.paths import (
    InvalidPathError,
    Workspace,
    WorkspaceBoundaryError,
)


class RiskLevel(str, Enum):
    """Risk tiers for candidate operations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Commands that carry elevated or dangerous mutation risk
CRITICAL_COMMANDS = {
    "rm", "del", "erase", "format", "dd", "mkfs", "shutdown", "reboot",
    "kill", "pkill", "taskkill", "chmod", "chown", "curl", "wget", "nc", "ncat",
}

# Read-only or safe verification commands
SAFE_COMMANDS = {
    "pytest", "unittest", "ruff", "mypy", "flake8", "black", "isort",
    "git status", "git diff", "git log", "echo", "pwd", "ls", "dir",
}

# Critical configuration file patterns
CRITICAL_FILE_PATTERNS = {
    "pyproject.toml", "setup.py", "package.json", "requirements.txt",
    "dockerfile", "docker-compose.yml", ".gitignore",
}


class RiskEngine:
    """Evaluates risk score deterministically without relying on agent claims."""

    def calculate_risk(
        self,
        action: Action,
        workspace: Workspace,
        contract: Contract | None = None,
    ) -> RiskLevel:
        """Calculate independent risk level for an action."""
        # Agent claims about risk are deliberately ignored

        if action.type == ActionType.DELETE_FILE:
            return RiskLevel.CRITICAL

        if action.type == ActionType.READ_FILE:
            # Check if target is sensitive
            target_str = action.target.lower()
            if contract and contract.is_path_forbidden(target_str):
                return RiskLevel.CRITICAL
            if any(p in target_str for p in [".env", "secret", "token", "key", "cred"]):
                return RiskLevel.CRITICAL
            return RiskLevel.LOW

        if action.type == ActionType.WRITE_FILE:
            target_posix = action.target.replace("\\", "/").lower()
            filename = PurePosixPath(target_posix).name

            # Check if writing to sensitive configuration or workflows
            if filename in CRITICAL_FILE_PATTERNS or target_posix.startswith(".github/"):
                return RiskLevel.HIGH

            # Check if modifying an existing file vs creating a new one
            try:
                resolved = workspace.resolve(action.target)
                if resolved.exists():
                    return RiskLevel.MEDIUM
            except (WorkspaceBoundaryError, InvalidPathError, OSError):
                return RiskLevel.HIGH

            return RiskLevel.LOW

        if action.type == ActionType.RUN_COMMAND:
            return self._calculate_command_risk(action.target)

        return RiskLevel.HIGH

    def _calculate_command_risk(self, command_line: str) -> RiskLevel:
        """Classify command line execution risk."""
        stripped = command_line.strip()
        if not stripped:
            return RiskLevel.LOW

        try:
            parts = shlex.split(stripped, posix=False)
        except ValueError:
            return RiskLevel.CRITICAL

        if not parts:
            return RiskLevel.LOW

        binary = PurePosixPath(parts[0].replace("\\", "/")).name.lower()

        if binary in CRITICAL_COMMANDS:
            return RiskLevel.CRITICAL

        # Check for shell operators or redirection
        if any(op in stripped for op in ["&&", "||", ";", "|", "`", "$(", ">", "<"]):
            return RiskLevel.CRITICAL

        # Check against known safe commands
        for safe in SAFE_COMMANDS:
            if stripped == safe or stripped.startswith(f"{safe} "):
                return RiskLevel.LOW

        # Unknown commands default to HIGH risk
        return RiskLevel.HIGH
