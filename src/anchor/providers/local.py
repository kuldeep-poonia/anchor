"""Deterministic local intent provider requiring no external API key."""

import re
from pathlib import Path

from anchor.actions.models import ActionRequest, ActionType
from anchor.contracts.models import Contract
from anchor.providers.base import IntentProvider
from anchor.workspace.paths import Workspace

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "create", "build", "refactor", "implement", "update", "fix", "service",
    "module", "app", "code", "file", "new", "test", "tests", "deterministic",
}


def _has_test_suite(workspace: Workspace | None) -> bool:
    """Check if workspace contains test files."""
    if not workspace or not workspace.root.exists():
        return False
    for p in workspace.root.rglob("test_*.py"):
        if ".anchor" not in p.parts and ".git" not in p.parts and ".venv" not in p.parts:
            return True
    for p in workspace.root.rglob("*_test.py"):
        if ".anchor" not in p.parts and ".git" not in p.parts and ".venv" not in p.parts:
            return True
    return False


def _extract_subject(goal: str) -> str:
    """Extract primary subject keyword from goal."""
    lower = goal.lower()
    if "auth" in lower or "login" in lower:
        return "auth"
    words = re.findall(r"[a-zA-Z]{3,}", lower)
    for w in words:
        if w not in STOP_WORDS:
            return w
    return "app"


def _generate_file_content(subject: str, target: str) -> str:
    """Synthesize dynamic, clean Python content based on goal subject."""
    if "auth" in subject or "login" in subject:
        return (
            '"""Authentication and access control service."""\n\n'
            'def authenticate(user: str, token: str) -> bool:\n'
            '    """Validate credentials safely."""\n'
            '    return bool(user and token and len(token) >= 8)\n\n'
            'def verify_permission(role: str, action: str) -> bool:\n'
            '    """Check role-based access permissions."""\n'
            '    return role == "admin" or action == "read"\n'
        )
    elif "calc" in subject:
        return (
            '"""Calculator implementation."""\n\n'
            'def add(a: float, b: float) -> float:\n'
            '    return a + b\n\n'
            'def multiply(a: float, b: float) -> float:\n'
            '    return a * b\n'
        )
    elif "weather" in subject:
        return (
            '"""Weather forecast service."""\n\n'
            'def get_forecast(city: str) -> dict[str, str]:\n'
            '    return {"city": city, "condition": "Sunny", "temp": "22C"}\n'
        )
    else:
        func_name = re.sub(r"\W+", "_", subject).strip("_") or "main"
        return (
            f'"""Module implementation for {subject}."""\n\n'
            f'def {func_name}() -> str:\n'
            f'    """Execute primary operation."""\n'
            f'    return "Success: {subject}"\n\n'
            'if __name__ == "__main__":\n'
            f'    print({func_name}())\n'
        )


class LocalProvider(IntentProvider):
    """
    Offline deterministic provider for development, tests, and credential-free demo.

    Analyzes goal keywords and workspace structure using deterministic heuristics.
    """

    def __init__(self, workspace: Workspace | None = None) -> None:
        self.workspace = workspace

    def _resolve_target_file(self, goal: str) -> tuple[str, str]:
        """
        Determine target filename and subject from goal and workspace.

        Returns (target_path, subject).
        """
        cleaned_goal = goal.strip()
        file_candidates = re.findall(r"[\w\-\./]+\.[a-zA-Z0-9]+", cleaned_goal)
        has_src = bool(self.workspace and (self.workspace.root / "src").is_dir())
        subject = _extract_subject(cleaned_goal)

        if file_candidates:
            target = file_candidates[0]
            return target, subject

        if has_src:
            if subject == "auth":
                return "src/auth/service.py", subject
            return f"src/{subject}.py", subject
        else:
            if subject == "auth":
                return "auth.py", subject
            return f"{subject}.py", subject

    def generate_contract(self, goal: str) -> Contract:
        """Derive bounded contract from goal keywords deterministically."""
        cleaned_goal = goal.strip()
        lower_goal = cleaned_goal.lower()

        target_file, subject = self._resolve_target_file(goal)
        target_path = Path(target_file)
        target_stem = target_path.stem
        target_parent = target_path.parent.as_posix()

        allowed_paths: list[str] = []
        forbidden_paths: list[str] = [".env", ".env*", "secrets/**", "credentials*"]
        allowed_commands: list[str] = ["pytest", "ruff check", "git diff", "git status"]

        # Scope allowed boundaries dynamically
        if target_parent and target_parent != ".":
            allowed_paths.extend([f"{target_parent}/**", f"{target_parent}/*"])
        else:
            allowed_paths.extend([f"{target_stem}*", f"{target_stem}.py"])

        # Also support standard tests and auth patterns for compatibility
        if subject == "auth":
            allowed_paths.extend(["src/auth/**", "auth/**", "tests/test_auth.py"])

        allowed_paths.extend(["tests/**", "test_*.py"])

        # Only run pytest if test files actually exist in the workspace
        verification_cmd: str | None = None
        if _has_test_suite(self.workspace):
            verification_cmd = "pytest -q"

        # Extract words for goal summary
        words = re.findall(r"\w+", lower_goal)
        summary = " ".join(words[:10]) if words else "agent task"

        return Contract(
            goal=summary,
            allowed_paths=allowed_paths,
            forbidden_paths=forbidden_paths,
            allowed_commands=allowed_commands,
            destructive_requires_approval=True,
            verification_command=verification_cmd,
            metadata={"provider": "local", "deterministic": True},
        )

    def propose_actions(self, goal: str, contract: Contract) -> list[ActionRequest]:
        """Propose representative actions for the goal to demonstrate enforcement."""
        target_file, subject = self._resolve_target_file(goal)
        actions: list[ActionRequest] = []

        # 1. Permitted primary action (writing/implementing target)
        content = _generate_file_content(subject, target_file)
        actions.append(
            ActionRequest(
                type=ActionType.WRITE_FILE,
                target=target_file,
                content=content,
                metadata={"step": f"implement {subject} logic in {target_file}"},
            )
        )

        # 2. Blocked forbidden access attempt (safeguarding environment secrets)
        actions.append(
            ActionRequest(
                type=ActionType.READ_FILE,
                target=".env",
                metadata={"step": "attempt read credentials for task"},
            )
        )

        # 3. High-risk destructive deletion requiring approval (within allowed boundary)
        target_path = Path(target_file)
        if target_path.parent and target_path.parent.as_posix() != ".":
            cleanup_target = f"{target_path.parent.as_posix()}/{subject}_legacy.py"
        else:
            cleanup_target = f"{subject}_legacy.py"

        actions.append(
            ActionRequest(
                type=ActionType.DELETE_FILE,
                target=cleanup_target,
                metadata={"step": f"cleanup deprecated {subject} legacy code"},
            )
        )

        return actions
