"""Contract models governing allowed and forbidden boundaries for agents."""

import re
import shlex
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Default protected paths that are forbidden unless explicitly exempted
DEFAULT_FORBIDDEN_PATTERNS = [
    ".env*",
    "*.env",
    ".git/**",
    ".git*",
    ".anchor/**",
    "*.pem",
    "*.key",
    "*id_rsa*",
    "*id_ed25519*",
    "secrets/**",
    "**/secrets/**",
    "*credentials*",
]

# Shell operators that can be used for hidden command execution
SHELL_OPERATORS = ["&&", "||", ";", "|", "`", "$(", ">", "<", "\n"]


def pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert glob pattern with support for recursive wildcards to regex."""
    clean = pattern.replace("\\", "/").strip().lstrip("/")
    # Escape regex special characters
    escaped = re.escape(clean)
    # Replace escaped wildcards with regex equivalents
    escaped = escaped.replace(r"\*\*", ".*")
    escaped = escaped.replace(r"\*", r"[^/]*")
    escaped = escaped.replace(r"\?", r"[^/]")
    return re.compile(rf"^{escaped}$", re.IGNORECASE)


def match_path(path: str, pattern: str) -> bool:
    """Match a normalized posix relative path against a glob pattern."""
    norm_path = path.replace("\\", "/").strip().lstrip("/")
    norm_pat = pattern.replace("\\", "/").strip().lstrip("/")

    # Handle directory prefix wildcard
    if norm_pat.endswith("/**"):
        prefix = norm_pat[:-3].rstrip("/")
        if norm_path == prefix or norm_path.startswith(f"{prefix}/"):
            return True

    # Handle exact name or extension pattern
    regex = pattern_to_regex(norm_pat)
    if regex.match(norm_path):
        return True

    # Also match basename if pattern does not contain slashes
    if "/" not in norm_pat:
        filename = PurePosixPath(norm_path).name
        if pattern_to_regex(norm_pat).match(filename):
            return True

    return False


class Contract(BaseModel):
    """Declarative safety contract defining boundaries for agent actions."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    goal: str = Field(..., min_length=1, max_length=2000)
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    allowed_commands: list[str] = Field(default_factory=list)
    destructive_requires_approval: bool = Field(default=True)
    verification_command: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("allowed_paths", "forbidden_paths")
    @classmethod
    def validate_patterns(cls, patterns: list[str]) -> list[str]:
        cleaned: list[str] = []
        for p in patterns:
            if "\x00" in p:
                raise ValueError("Path pattern contains illegal null byte")
            stripped = p.strip()
            if not stripped:
                continue
            if ".." in stripped.split("/"):
                raise ValueError(f"Traversal pattern not allowed in contract: {p}")
            cleaned.append(stripped)
        return cleaned

    def get_all_forbidden_patterns(self) -> list[str]:
        """Combine user forbidden paths with default safety patterns."""
        combined = list(DEFAULT_FORBIDDEN_PATTERNS)
        for p in self.forbidden_paths:
            if p not in combined:
                combined.append(p)
        return combined

    def is_path_forbidden(self, rel_path: str) -> bool:
        """Return True if path matches any forbidden pattern."""
        for pattern in self.get_all_forbidden_patterns():
            if match_path(rel_path, pattern):
                return True
        return False

    def is_path_allowed(self, rel_path: str) -> bool:
        """
        Check if path is permitted.

        Precedence rule:
        Forbidden paths always override allowed paths.
        If allowed_paths is empty, fail closed (deny).
        """
        # Forbidden check always comes first
        if self.is_path_forbidden(rel_path):
            return False

        if not self.allowed_paths:
            return False

        for pattern in self.allowed_paths:
            if match_path(rel_path, pattern):
                return True

        return False

    def is_command_allowed(self, command: str) -> bool:
        """
        Verify if a command is permitted.

        Rejects hidden chaining operators unless exact command matches allowlist.
        """
        stripped = command.strip()
        if not stripped:
            return False

        # Parse command into executable name and arguments
        try:
            parts = shlex.split(stripped, posix=False)
        except ValueError:
            return False

        if not parts:
            return False

        binary_name = PurePosixPath(parts[0].replace("\\", "/")).name.lower()

        # Check for shell operators in command line
        has_operator = any(op in stripped for op in SHELL_OPERATORS)

        for allowed in self.allowed_commands:
            allowed_stripped = allowed.strip()
            # Exact command match
            if stripped == allowed_stripped:
                return True

            # If command contains unapproved operators, block it
            if has_operator:
                continue

            # Prefix or binary match
            allowed_parts = shlex.split(allowed_stripped, posix=False)
            if allowed_parts:
                allowed_binary = PurePosixPath(allowed_parts[0].replace("\\", "/")).name.lower()
                if binary_name == allowed_binary and (
                    len(allowed_parts) == 1 or stripped.startswith(allowed_stripped)
                ):
                    return True

        return False
