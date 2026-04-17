"""Internal text schemas used by the ported provider layer."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from ..config import DEFAULT_RETRIES, DEFAULT_TIMEOUT_SECONDS
from .base import FrozenSchema


class TextoParaTextoResultado(FrozenSchema):
    texto: str = Field(min_length=1)
    custo_usd: Decimal = Field(ge=Decimal("0"))


class TextoParaTextoRequest(FrozenSchema):
    instrucoes: str = Field(min_length=1)
    informacoes: str | list[str] | dict[str, Any] | None = None
    api: str = Field(min_length=1)
    modelo: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    max_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    seed: int | None = None
    stop: str | list[str] | None = None
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    response_format: dict[str, Any] | None = None
    reasoning_effort: str | None = None
    thinking: dict[str, Any] | None = None
    imagens_entrada: list[str | bytes] | None = None
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, Any] | None = None

    @field_validator("stop")
    @classmethod
    def validar_stop(cls, value: str | list[str] | None) -> str | list[str] | None:
        if value is None:
            return value
        if isinstance(value, list) and not value:
            raise ValueError("`stop` cannot be an empty list.")
        return value

    @model_validator(mode="after")
    def validar_max_tokens(self) -> TextoParaTextoRequest:
        if self.max_tokens and self.max_output_tokens and self.max_tokens != self.max_output_tokens:
            raise ValueError("`max_tokens` and `max_output_tokens` cannot differ.")
        return self


class TextoParaTextoLoteItem(FrozenSchema):
    identificador: str = Field(min_length=1)
    request: TextoParaTextoRequest
