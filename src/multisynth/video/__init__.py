"""Public video generation and lip-sync helpers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .._core.aliases import normalizar_api
from .._core.credentials import CredentialStore
from .._core.exceptions import UnsupportedProviderError
from .._core.public_api import coerce_request
from .._core.schemas import VideoJobRequest
from ..models import LipSyncRequest, VideoGenerationRequest, VideoResult
from .providers import VideoRegistries, build_video_registries


def _registries(credentials: Mapping[str, str] | CredentialStore | None) -> VideoRegistries:
    return build_video_registries(credentials)


def _resolve_model(adapter, request: VideoJobRequest) -> str:
    if hasattr(adapter, "_resolve_model_for_request"):
        return adapter._resolve_model_for_request(request)
    return adapter.resolve_model(request.modelo)


def generate(
    request: VideoGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> VideoResult:
    """Generate a video with or without input audio."""

    request = coerce_request(request, VideoGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    registries = _registries(credentials)
    registry = registries.with_audio if request.audio is not None else registries.without_audio
    if provider not in registry:
        mode = "with audio" if request.audio is not None else "without audio"
        raise UnsupportedProviderError(
            f"Provider {provider!r} does not support video generation {mode}."
        )
    adapter = registry[provider]
    internal = VideoJobRequest(
        prompt=request.prompt,
        imagem=request.image,
        audio=request.audio,
        modelo=request.model,
        caminho_saida=Path(request.output_path),
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    adapter.gerar(internal)
    return VideoResult(
        output_path=internal.caminho_saida,
        metadata={"provider": provider, "model": _resolve_model(adapter, internal)},
    )


async def generate_async(
    request: VideoGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> VideoResult:
    """Async variant of :func:`generate`."""

    request = coerce_request(request, VideoGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    registries = _registries(credentials)
    registry = registries.with_audio if request.audio is not None else registries.without_audio
    if provider not in registry:
        mode = "with audio" if request.audio is not None else "without audio"
        raise UnsupportedProviderError(
            f"Provider {provider!r} does not support video generation {mode}."
        )
    adapter = registry[provider]
    internal = VideoJobRequest(
        prompt=request.prompt,
        imagem=request.image,
        audio=request.audio,
        modelo=request.model,
        caminho_saida=Path(request.output_path),
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    await adapter.gerar_async(internal)
    return VideoResult(
        output_path=internal.caminho_saida,
        metadata={"provider": provider, "model": _resolve_model(adapter, internal)},
    )


def lipsync(
    request: LipSyncRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> VideoResult:
    """Animate a still image or avatar with a supplied audio track."""

    request = coerce_request(request, LipSyncRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).lipsync[provider]
    internal = VideoJobRequest(
        imagem=request.image,
        audio=request.audio,
        modelo=request.model,
        caminho_saida=Path(request.output_path),
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    adapter.gerar(internal)
    return VideoResult(
        output_path=internal.caminho_saida,
        metadata={"provider": provider, "model": _resolve_model(adapter, internal)},
    )


async def lipsync_async(
    request: LipSyncRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> VideoResult:
    """Async variant of :func:`lipsync`."""

    request = coerce_request(request, LipSyncRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).lipsync[provider]
    internal = VideoJobRequest(
        imagem=request.image,
        audio=request.audio,
        modelo=request.model,
        caminho_saida=Path(request.output_path),
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    await adapter.gerar_async(internal)
    return VideoResult(
        output_path=internal.caminho_saida,
        metadata={"provider": provider, "model": _resolve_model(adapter, internal)},
    )


__all__ = ["generate", "generate_async", "lipsync", "lipsync_async"]
