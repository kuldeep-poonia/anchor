"""Unit tests for Action and ActionRequest models."""

import pytest
from pydantic import ValidationError

from anchor.actions.models import Action, ActionRequest, ActionType


def test_valid_action_request() -> None:
    req = ActionRequest(
        type=ActionType.WRITE_FILE,
        target="src/main.py",
        content="print('hello')",
    )
    assert req.type == ActionType.WRITE_FILE
    assert req.target == "src/main.py"
    assert req.content == "print('hello')"

    action = Action.from_request(req)
    assert action.type == ActionType.WRITE_FILE
    assert action.target == "src/main.py"
    assert action.id is not None


def test_rejects_unknown_action_type() -> None:
    with pytest.raises(ValidationError):
        ActionRequest(
            type="destroy_server",  # type: ignore
            target="src/main.py",
        )


def test_rejects_null_byte_in_target() -> None:
    with pytest.raises(ValidationError, match="null byte"):
        ActionRequest(
            type=ActionType.READ_FILE,
            target="src/main.py\x00extra",
        )


def test_rejects_empty_target() -> None:
    with pytest.raises(ValidationError):
        ActionRequest(
            type=ActionType.DELETE_FILE,
            target="   ",
        )


def test_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        ActionRequest(
            type=ActionType.RUN_COMMAND,
            target="pytest",
            malicious_payload="bypass_anchor",  # type: ignore
        )
