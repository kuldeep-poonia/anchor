"""Abstract base class and errors for AI intent providers."""

from abc import ABC, abstractmethod

from anchor.actions.models import ActionRequest
from anchor.contracts.models import Contract


class ProviderError(Exception):
    """Raised when an AI provider fails or returns unparseable content."""


class IntentProvider(ABC):
    """Abstract interface for turning natural language goals into structured contracts."""

    @abstractmethod
    def generate_contract(self, goal: str) -> Contract:
        """Synthesize a structured Contract from a natural language goal."""

    @abstractmethod
    def propose_actions(self, goal: str, contract: Contract) -> list[ActionRequest]:
        """Propose candidate actions to accomplish the goal under contract constraints."""
