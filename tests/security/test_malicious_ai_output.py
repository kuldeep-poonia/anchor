"""Adversarial security tests for compromised or hallucinating AI models."""

import httpx
import pytest

from anchor.actions.models import Action, ActionType
from anchor.policy.engine import DecisionType, PolicyEngine
from anchor.providers.base import ProviderError
from anchor.providers.nebius import NebiusProvider
from anchor.workspace.paths import Workspace


def test_rejects_hallucinated_unparseable_output(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = NebiusProvider(api_key="mock_key")

    def mock_post(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "https://api.studio.nebius.ai/v1/chat/completions")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "I apologize, but as an AI I cannot..."}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(ProviderError, match="Failed to validate contract"):
        provider.generate_contract("Do work")


def test_rejects_malicious_path_traversal_in_model_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = NebiusProvider(api_key="mock_key")

    malicious_json = """
    {
      "goal": "Exploit system",
      "allowed_paths": ["../../../../etc/**"],
      "forbidden_paths": [],
      "allowed_commands": ["rm -rf /"]
    }
    """

    def mock_post(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "https://api.studio.nebius.ai/v1/chat/completions")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": malicious_json}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(ProviderError, match="Traversal pattern not allowed"):
        provider.generate_contract("Exploit")


def test_compromised_model_cannot_override_default_safety_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Even if an attacker tricks the model into allowing all paths, ANCHOR enforces boundaries."""
    provider = NebiusProvider(api_key="mock_key")

    # Attacker got the model to output a fully permissive contract
    permissive_json = """
    {
      "goal": "Gain full access",
      "allowed_paths": ["**"],
      "forbidden_paths": [],
      "allowed_commands": ["pytest"],
      "destructive_requires_approval": false
    }
    """

    def mock_post(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "https://api.studio.nebius.ai/v1/chat/completions")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": permissive_json}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    compromised_contract = provider.generate_contract("Bypass")

    ws = Workspace(tmp_path)
    engine = PolicyEngine(ws)

    # 1. Attempt reading .env (must be blocked despite model's allowed_paths=["**"])
    act1 = Action(type=ActionType.READ_FILE, target=".env")
    dec1 = engine.evaluate(act1, compromised_contract)
    assert dec1.decision == DecisionType.DENY

    # 2. Attempt reading git config (must be blocked)
    act2 = Action(type=ActionType.READ_FILE, target=".git/config")
    dec2 = engine.evaluate(act2, compromised_contract)
    assert dec2.decision == DecisionType.DENY

    # 3. Attempt escaping workspace (must be blocked)
    act3 = Action(type=ActionType.READ_FILE, target="../outside.txt")
    dec3 = engine.evaluate(act3, compromised_contract)
    assert dec3.decision == DecisionType.DENY
