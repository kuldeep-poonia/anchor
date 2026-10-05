"""Safe path resolution and workspace boundary protection."""

import os
import re
from pathlib import Path


class SecurityError(Exception):
    """Base security exception for ANCHOR."""


class WorkspaceBoundaryError(SecurityError):
    """Raised when an operation attempts to escape the configured workspace."""


class InvalidPathError(ValueError):
    """Raised when a path is structurally invalid or contains malicious patterns."""


# Windows reserved device names
RESERVED_DEVICE_NAMES = {
    "AUX",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "CON",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
    "NUL",
    "PRN",
}


def _check_windows_reserved(path_str: str) -> None:
    """Check for Windows reserved device names."""
    parts = re.split(r"[\\/]", path_str)
    for part in parts:
        stem = part.split(".")[0].upper()
        if stem in RESERVED_DEVICE_NAMES:
            raise InvalidPathError(f"Path references reserved device name: {stem}")


def _check_stream_names(path_str: str) -> None:
    """Detect NTFS alternate data streams."""
    # Allow standard Windows drive letter like C: at start
    remainder = path_str
    if len(remainder) >= 2 and remainder[1] == ":":
        remainder = remainder[2:]
    if ":" in remainder:
        raise InvalidPathError("Path contains illegal alternate data stream colon")


def resolve_safe_path(workspace_root: str | Path, raw_path: str | Path) -> Path:
    """
    Resolve a target path safely inside the workspace boundary.

    Enforces:
    - No null bytes
    - No alternate data streams
    - No reserved device names
    - Canonical path resolution to defeat symlink escapes
    - Strict is_relative_to containment verification
    """
    path_str = str(raw_path)

    # Reject null bytes
    if "\x00" in path_str:
        raise InvalidPathError("Path contains null byte")

    # Reject stream names
    _check_stream_names(path_str)

    # Reject reserved device names
    _check_windows_reserved(path_str)

    canonical_root = Path(workspace_root).resolve()
    target = Path(path_str)

    if target.is_absolute():
        candidate = target
    else:
        candidate = canonical_root / target

    # Resolve symlinks and canonical path
    if candidate.exists():
        resolved = candidate.resolve()
    else:
        # For paths that do not exist yet, find deepest existing ancestor
        # and ensure no parent escape occurs
        curr = candidate
        missing_parts = []
        while not curr.exists() and curr != curr.parent:
            missing_parts.append(curr.name)
            curr = curr.parent

        if curr.exists():
            resolved_ancestor = curr.resolve()
            resolved = resolved_ancestor
            for part in reversed(missing_parts):
                resolved = resolved / part
        else:
            resolved = candidate.resolve()

    # Normalize lexical path
    normalized = Path(os.path.normpath(str(resolved)))

    # Verify canonical containment
    try:
        normalized.relative_to(canonical_root)
    except ValueError:
        raise WorkspaceBoundaryError(
            f"Target path '{raw_path}' escapes workspace boundary '{canonical_root}'"
        ) from None

    return normalized


class Workspace:
    """Encapsulates workspace root directory and enforces file boundary rules."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root = Path(root_dir).resolve()
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, target: str | Path) -> Path:
        """Resolve target path safely within workspace."""
        return resolve_safe_path(self.root, target)

    def relative(self, target: str | Path) -> str:
        """Return canonical relative POSIX path for policy matching."""
        safe_path = self.resolve(target)
        rel = safe_path.relative_to(self.root)
        return rel.as_posix()

    def contains(self, target: str | Path) -> bool:
        """Return True if target resolves strictly inside workspace."""
        try:
            self.resolve(target)
            return True
        except (WorkspaceBoundaryError, InvalidPathError):
            return False
