"""Internal strict/frozen pydantic base model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FrozenSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        validate_assignment=False,
    )
