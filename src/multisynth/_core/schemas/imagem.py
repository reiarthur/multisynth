"""Internal image schemas used by the provider layer."""

from __future__ import annotations

from pydantic import Field, model_validator

from ..config import DEFAULT_RETRIES, DEFAULT_TIMEOUT_SECONDS
from .base import FrozenSchema


class TextoParaImagemRequest(FrozenSchema):
    prompt: str = Field(min_length=1)
    negative_prompt: str | None = None
    modelo: str | None = None
    largura: int | None = Field(default=None, gt=0)
    altura: int | None = Field(default=None, gt=0)
    seed: int | None = None
    quantidade: int = Field(default=1, ge=1, le=1)
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None


class TextoImagemParaImagemRequest(FrozenSchema):
    prompt: str = Field(min_length=1)
    imagem: str | bytes
    negative_prompt: str | None = None
    modelo: str | None = None
    intensidade: float | None = Field(default=None, ge=0, le=1)
    seed: int | None = None
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None


class EditarImagemRequest(FrozenSchema):
    prompt: str = Field(min_length=1)
    imagem: str | bytes
    mascara: str | bytes | None = None
    negative_prompt: str | None = None
    modelo: str | None = None
    seed: int | None = None
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None

    @model_validator(mode="after")
    def validar_prompt(self) -> EditarImagemRequest:
        if not self.prompt.strip():
            raise ValueError("`prompt` cannot be blank after trimming.")
        return self
