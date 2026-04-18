"""Internal audio schemas used by the provider layer."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from ..config import DEFAULT_RETRIES, DEFAULT_TIMEOUT_SECONDS
from .base import FrozenSchema


class PalavraTemporizada(FrozenSchema):
    indice: int = Field(ge=0)
    texto: str = Field(min_length=1)
    inicio_s: Decimal = Field(ge=Decimal("0"))
    fim_s: Decimal = Field(ge=Decimal("0"))
    speaker: str | None = None
    confianca: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("1"))


class TrechoSpeaker(FrozenSchema):
    speaker: str = Field(min_length=1)
    inicio_s: Decimal = Field(ge=Decimal("0"))
    fim_s: Decimal = Field(ge=Decimal("0"))
    texto: str = Field(min_length=1)


class AudioParaTextoResultado(FrozenSchema):
    texto: str = Field(min_length=1)
    palavras: list[PalavraTemporizada]
    trechos_por_speaker: list[TrechoSpeaker]
    metadata: dict[str, object]


class TextoParaAudioResultado(FrozenSchema):
    audio_base64: str = Field(min_length=1)
    palavras: list[PalavraTemporizada]
    metadata: dict[str, object]


class AudioParaTextoRequest(FrozenSchema):
    audio: str | bytes
    modelo: str | None = None
    idioma: str | None = None
    diarizacao: bool = True
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None


class TextoParaAudioRequest(FrozenSchema):
    texto: str = Field(min_length=1)
    modelo: str | None = None
    voz: str | None = None
    idioma: str | None = None
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None


class TextoParaMusicaRequest(FrozenSchema):
    prompt: str = Field(min_length=1)
    modelo: str | None = None
    duracao_segundos: float | None = Field(default=None, gt=0)
    timeout_segundos: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_tentativas: int = Field(default=DEFAULT_RETRIES, ge=1, le=10)
    parametros_provider: dict[str, object] | None = None
