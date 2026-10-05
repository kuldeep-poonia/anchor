"""Unit tests for AI providers (Local and Nebius)."""

import httpx
import pytest

from anchor.contracts.models import Contract
from anchor.providers import LocalProvider, NebiusProvider, ProviderError, get_provider


def test_local_provider_generates_valid_contract() -> None:
    provider = LocalProvider()
    contract = provider.generate_contract("Refactor authentication module and add tests")

    assert isinstance(contract, Contract)
    assert any("auth" in p for p in contract.allowed_paths)
    assert ".env" in contract.forbidden_paths
    assert contract.is_path_allowed("src/auth/login.py") is True
    assert contract.is_path_allowed(".env") is False


def test_local_provider_proposes_actions() -> None:
    provider = LocalProvider()
    contract = provider.generate_contract("Build features")
    actions = provider.propose_actions("Build features", contract)

    assert len(actions) >= 3
    # Check that representative action requests were created
    types = [a.type for a in actions]
    assert "write_file" in types
    assert "read_file" in types
    assert "delete_file" in types


def test_get_provider_factory_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    # When no key is present -> LocalProvider
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    p1 = get_provider()
    assert isinstance(p1, LocalProvider)

    # When key is present -> NebiusProvider
    monkeypatch.setenv("NEBIUS_API_KEY", "test_key_xyz")
    p2 = get_provider()
    assert isinstance(p2, NebiusProvider)
    assert p2.api_key == "test_key_xyz"


def test_nebius_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="NEBIUS_API_KEY is not set"):
        NebiusProvider(api_key="")


def test_nebius_provider_with_mocked_response(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = NebiusProvider(api_key="mock_key")

    mock_llm_json = """
    {
      "goal": "Refactor auth",
      "allowed_paths": ["src/auth/**", "tests/**"],
      "forbidden_paths": [".env"],
      "allowed_commands": ["pytest"],
      "destructive_requires_approval": true,
      "verification_command": "pytest"
    }
    """

    def mock_post(*args, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", "https://api.studio.nebius.ai/v1/chat/completions")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": f"```json\n{mock_llm_json}\n```"}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    contract = provider.generate_contract("Refactor auth")
    assert contract.goal == "Refactor auth"
    assert contract.is_path_allowed("src/auth/token.py") is True
    assert contract.is_path_allowed(".env") is False
