"""Structured representations of actions that agents request to perform."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionType(str, Enum):
    """Supported action primitives."""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    RUN_COMMAND = "run_command"


class ActionRequest(BaseModel):
    """Raw request from an agent before internal normalization and evaluation."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: ActionType
    target: str = Field(..., min_length=1, max_length=4096)
    content: str | None = Field(default=None, max_length=10_000_000)
    args: list[str] | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        """Ensure target does not contain null bytes or illegal characters."""
        if "\x00" in value:
            raise ValueError("Target contains illegal null byte")
        stripped = value.strip()
        if not stripped:
            raise ValueError("Target cannot be empty or whitespace only")
        return stripped


class Action(BaseModel):
    """Validated, normalized internal action representation."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ActionType
    target: str
    content: str | None = None
    args: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_request(cls, request: ActionRequest) -> "Action":
        """Convert a validated request into an internal action instance."""
        return cls(
            type=request.type,
            target=request.target,
            content=request.content,
            args=request.args or [],
            metadata=dict(request.metadata),
        )
