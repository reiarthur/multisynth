"""Public audio helpers for transcription, synthesis, and music generation."""

from __future__ import annotations

from collections.abc import Mapping

from .._core.aliases import normalizar_api
from .._core.credentials import CredentialStore
from .._core.public_api import coerce_request
from .._core.schemas import (
    AudioParaTextoRequest as InternalSpeechTranscriptionRequest,
)
from .._core.schemas import (
    PalavraTemporizada,
    TrechoSpeaker,
)
from .._core.schemas import (
    TextoParaAudioRequest as InternalSpeechSynthesisRequest,
)
from .._core.schemas import (
    TextoParaMusicaRequest as InternalMusicGenerationRequest,
)
from ..models import (
    MusicGenerationRequest,
    MusicGenerationResult,
    SpeakerSegment,
    SpeechSynthesisRequest,
    SpeechSynthesisResult,
    SpeechTranscriptionRequest,
    SpeechTranscriptionResult,
    WordTiming,
)
from .providers import AudioRegistries, build_audio_registries


def _to_word_timing(item: PalavraTemporizada) -> WordTiming:
    return WordTiming(
        index=item.indice,
        text=item.texto,
        start_seconds=item.inicio_s,
        end_seconds=item.fim_s,
        speaker=item.speaker,
        confidence=item.confianca,
    )


def _to_speaker_segment(item: TrechoSpeaker) -> SpeakerSegment:
    return SpeakerSegment(
        speaker=item.speaker,
        start_seconds=item.inicio_s,
        end_seconds=item.fim_s,
        text=item.texto,
    )


def _registries(credentials: Mapping[str, str] | CredentialStore | None) -> AudioRegistries:
    return build_audio_registries(credentials)


def transcribe(
    request: SpeechTranscriptionRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> SpeechTranscriptionResult:
    """Transcribe an audio file or byte payload into text.

    Args:
        request: Optional pre-built request model.
        credentials: Optional explicit credential mapping for this call.
        **kwargs: Fields used to build ``SpeechTranscriptionRequest``.

    Returns:
        A transcription result with plain text, word timings, speaker segments,
        and provider metadata.
    """

    request = coerce_request(request, SpeechTranscriptionRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).transcription[provider]
    result = adapter.transcrever(
        InternalSpeechTranscriptionRequest(
            audio=request.audio,
            modelo=request.model,
            idioma=request.language,
            diarizacao=request.diarization,
            timeout_segundos=request.timeout_seconds,
            max_tentativas=request.max_retries,
            parametros_provider=request.provider_params,
        )
    )
    return SpeechTranscriptionResult(
        text=result.texto,
        words=[_to_word_timing(item) for item in result.palavras],
        speaker_segments=[_to_speaker_segment(item) for item in result.trechos_por_speaker],
        metadata=dict(result.metadata),
    )


async def transcribe_async(
    request: SpeechTranscriptionRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> SpeechTranscriptionResult:
    """Async variant of :func:`transcribe`."""

    request = coerce_request(request, SpeechTranscriptionRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).transcription[provider]
    result = await adapter.transcrever_async(
        InternalSpeechTranscriptionRequest(
            audio=request.audio,
            modelo=request.model,
            idioma=request.language,
            diarizacao=request.diarization,
            timeout_segundos=request.timeout_seconds,
            max_tentativas=request.max_retries,
            parametros_provider=request.provider_params,
        )
    )
    return SpeechTranscriptionResult(
        text=result.texto,
        words=[_to_word_timing(item) for item in result.palavras],
        speaker_segments=[_to_speaker_segment(item) for item in result.trechos_por_speaker],
        metadata=dict(result.metadata),
    )


def synthesize(
    request: SpeechSynthesisRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> SpeechSynthesisResult:
    """Synthesize spoken audio from text."""

    request = coerce_request(request, SpeechSynthesisRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).synthesis[provider]
    result = adapter.sintetizar(
        InternalSpeechSynthesisRequest(
            texto=request.text,
            modelo=request.model,
            voz=request.voice,
            idioma=request.language,
            timeout_segundos=request.timeout_seconds,
            max_tentativas=request.max_retries,
            parametros_provider=request.provider_params,
        )
    )
    return SpeechSynthesisResult(
        audio_base64=result.audio_base64,
        words=[_to_word_timing(item) for item in result.palavras],
        metadata=dict(result.metadata),
    )


async def synthesize_async(
    request: SpeechSynthesisRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> SpeechSynthesisResult:
    """Async variant of :func:`synthesize`."""

    request = coerce_request(request, SpeechSynthesisRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).synthesis[provider]
    result = await adapter.sintetizar_async(
        InternalSpeechSynthesisRequest(
            texto=request.text,
            modelo=request.model,
            voz=request.voice,
            idioma=request.language,
            timeout_segundos=request.timeout_seconds,
            max_tentativas=request.max_retries,
            parametros_provider=request.provider_params,
        )
    )
    return SpeechSynthesisResult(
        audio_base64=result.audio_base64,
        words=[_to_word_timing(item) for item in result.palavras],
        metadata=dict(result.metadata),
    )


def compose(
    request: MusicGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> MusicGenerationResult:
    """Generate music from a text prompt."""

    request = coerce_request(request, MusicGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).music[provider]
    internal = InternalMusicGenerationRequest(
        prompt=request.prompt,
        modelo=request.model,
        duracao_segundos=request.duration_seconds,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    audio_base64 = adapter.gerar(internal)
    return MusicGenerationResult(
        audio_base64=audio_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


async def compose_async(
    request: MusicGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> MusicGenerationResult:
    """Async variant of :func:`compose`."""

    request = coerce_request(request, MusicGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).music[provider]
    internal = InternalMusicGenerationRequest(
        prompt=request.prompt,
        modelo=request.model,
        duracao_segundos=request.duration_seconds,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    audio_base64 = await adapter.gerar_async(internal)
    return MusicGenerationResult(
        audio_base64=audio_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


__all__ = [
    "compose",
    "compose_async",
    "synthesize",
    "synthesize_async",
    "transcribe",
    "transcribe_async",
]
