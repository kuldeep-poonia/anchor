"""Deterministic local intent provider requiring no external API key."""

import re

from anchor.actions.models import ActionRequest, ActionType
from anchor.contracts.models import Contract
from anchor.providers.base import IntentProvider


class LocalProvider(IntentProvider):
    """
    Offline deterministic provider for development, tests, and credential-free demo.

    Analyzes goal keywords using deterministic heuristics to construct contracts.
    """

    def generate_contract(self, goal: str) -> Contract:
        """Derive bounded contract from goal keywords deterministically."""
        cleaned_goal = goal.strip()
        lower_goal = cleaned_goal.lower()

        allowed_paths: list[str] = []
        forbidden_paths: list[str] = [".env", ".env*", "secrets/**", "credentials*"]
        allowed_commands: list[str] = ["pytest", "ruff check", "git diff", "git status"]
        verification_cmd: str | None = None

        # Inspect keywords to scope allowed boundaries
        if "auth" in lower_goal or "login" in lower_goal:
            allowed_paths.extend(["src/auth/**", "tests/test_auth.py", "tests/**"])
            verification_cmd = "pytest -q"
        elif "test" in lower_goal:
            allowed_paths.extend(["tests/**", "src/**"])
            verification_cmd = "pytest"
        elif "doc" in lower_goal or "readme" in lower_goal:
            allowed_paths.extend(["docs/**", "README.md", "*.md"])
        elif "cleanup" in lower_goal or "delete" in lower_goal:
            allowed_paths.extend(["src/**", "tests/**", "temp/**"])
        else:
            allowed_paths.extend(["src/**", "tests/**"])

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
        lower_goal = goal.lower()
        actions: list[ActionRequest] = []

        # 1. Permitted action
        if "auth" in lower_goal:
            actions.append(
                ActionRequest(
                    type=ActionType.WRITE_FILE,
                    target="src/auth/login.py",
                    content="# Authentication service\ndef authenticate(token: str) -> bool:\n    return len(token) > 8\n",
                    metadata={"step": "implement auth logic"},
                )
            )
        else:
            actions.append(
                ActionRequest(
                    type=ActionType.WRITE_FILE,
                    target="src/app.py",
                    content="# Application entry\ndef main():\n    print('Hello Anchor')\n",
                    metadata={"step": "implement entrypoint"},
                )
            )

        # 2. Blocked forbidden access demonstration
        actions.append(
            ActionRequest(
                type=ActionType.READ_FILE,
                target=".env",
                metadata={"step": "attempt read secrets"},
            )
        )

        # 3. High-risk destructive deletion requiring approval
        actions.append(
            ActionRequest(
                type=ActionType.DELETE_FILE,
                target="src/legacy.py",
                metadata={"step": "cleanup obsolete code"},
            )
        )

        return actions
