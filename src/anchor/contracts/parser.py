"""Parser for ANCHOR contracts from structured data, JSON, or files."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from anchor.contracts.models import Contract


class ContractValidationError(ValueError):
    """Raised when a contract fails validation or contains malicious definitions."""


MAX_CONTRACT_SIZE_BYTES = 1_048_576  # 1 MB


def parse_contract(raw_data: str | bytes | dict[str, Any] | Path) -> Contract:
    """
    Parse and validate a Contract instance from JSON string, dictionary, or file.

    Fails closed: Any parsing or validation error results in ContractValidationError.
    """
    if isinstance(raw_data, Path):
        if not raw_data.exists():
            raise ContractValidationError(f"Contract file not found: {raw_data}")
        content = raw_data.read_text(encoding="utf-8")
        return parse_contract(content)

    if isinstance(raw_data, (str, bytes)):
        if len(raw_data) > MAX_CONTRACT_SIZE_BYTES:
            raise ContractValidationError("Contract payload exceeds maximum size limit of 1 MB")
        try:
            parsed = json.loads(raw_data)
        except json.JSONDecodeError as err:
            raise ContractValidationError(f"Malformed JSON in contract: {err}") from err
        if not isinstance(parsed, dict):
            raise ContractValidationError("Contract JSON must be an object")
        return parse_contract(parsed)

    if isinstance(raw_data, dict):
        try:
            return Contract(**raw_data)
        except (ValidationError, TypeError) as err:
            raise ContractValidationError(f"Invalid contract schema: {err}") from err

    raise ContractValidationError(f"Unsupported contract input type: {type(raw_data).__name__}")
