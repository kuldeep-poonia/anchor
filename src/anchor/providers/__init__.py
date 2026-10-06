"""AI intent providers and factory for ANCHOR."""

import os

from anchor.providers.base import IntentProvider, ProviderError
from anchor.providers.local import LocalProvider
from anchor.providers.nebius import NebiusProvider

from anchor.workspace.paths import Workspace

__all__ = [
    "IntentProvider",
    "LocalProvider",
    "NebiusProvider",
    "ProviderError",
    "get_provider",
]


def get_provider(
    api_key: str | None = None,
    workspace: Workspace | None = None,
) -> IntentProvider:
    """
    Get configured intent provider based on environment and credentials.

    If NEBIUS_API_KEY is available, returns NebiusProvider (NVIDIA Nemotron).
    Otherwise returns LocalProvider (fully deterministic, no credentials required).
    """
    key = api_key or os.getenv("NEBIUS_API_KEY", "").strip()
    if key:
        return NebiusProvider(api_key=key)
    return LocalProvider(workspace=workspace)
