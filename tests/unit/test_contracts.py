"""Unit tests for Contract models and parsing."""

import pytest

from anchor.contracts.models import Contract
from anchor.contracts.parser import ContractValidationError, parse_contract


def test_valid_contract_creation() -> None:
    contract = Contract(
        goal="Refactor authentication",
        allowed_paths=["src/auth/**", "tests/**"],
        forbidden_paths=[".env", "secrets/**"],
        allowed_commands=["pytest", "git diff"],
    )
    assert contract.is_path_allowed("src/auth/login.py") is True
    assert contract.is_path_allowed("tests/test_auth.py") is True
    assert contract.is_path_allowed("src/main.py") is False


def test_forbidden_overrides_allowed() -> None:
    contract = Contract(
        goal="Work on secrets helper",
        allowed_paths=["secrets/**", "src/**"],
        forbidden_paths=["secrets/**"],
    )
    # Even though secrets/** is in allowed_paths, forbidden MUST override it!
    assert contract.is_path_allowed("secrets/api_keys.json") is False
    assert contract.is_path_allowed("src/app.py") is True


def test_default_forbidden_patterns() -> None:
    contract = Contract(
        goal="General work",
        allowed_paths=["**"],
    )
    # Default patterns like .env and .git must be blocked automatically
    assert contract.is_path_allowed(".env") is False
    assert contract.is_path_allowed(".env.production") is False
    assert contract.is_path_allowed(".git/config") is False
    assert contract.is_path_allowed(".anchor/state.db") is False


def test_empty_allowed_fails_closed() -> None:
    contract = Contract(
        goal="No paths allowed",
        allowed_paths=[],
    )
    assert contract.is_path_allowed("src/main.py") is False


def test_command_validation() -> None:
    contract = Contract(
        goal="Test running",
        allowed_commands=["pytest", "ruff check"],
    )
    assert contract.is_command_allowed("pytest -v") is True
    assert contract.is_command_allowed("ruff check .") is True
    assert contract.is_command_allowed("python -m rm -rf /") is False


def test_parse_contract_json() -> None:
    json_str = """
    {
        "goal": "Build feature",
        "allowed_paths": ["src/**"],
        "forbidden_paths": [".env"],
        "allowed_commands": ["pytest"]
    }
    """
    contract = parse_contract(json_str)
    assert contract.goal == "Build feature"
    assert contract.is_path_allowed("src/index.py") is True


def test_parse_contract_malformed_json() -> None:
    with pytest.raises(ContractValidationError):
        parse_contract("{malformed json")


def test_parse_contract_unexpected_fields() -> None:
    with pytest.raises(ContractValidationError):
        parse_contract('{"goal": "test", "extra_attack": true}')
