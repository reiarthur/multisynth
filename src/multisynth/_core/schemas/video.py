"""Internal video schemas used by the provider layer."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from ..config import DEFAULT_JOB_TIMEOUT_SECONDS, DEFAULT_RETRIES
from .base import FrozenSchema


class VideoJobRequest(FrozenSchema):
    prompt: str | None = None
    imagem: str | bytes | None = None
    audio: str | bytes | None = None
    modelo: str | None = None
    caminho_saida: Path = Field(...)
    timeout_segundos: float = Field(default=DEFAULT_JOB_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None
