"""Public image generation, transformation, and editing helpers."""

from __future__ import annotations

from collections.abc import Mapping

from .._core.aliases import normalizar_api
from .._core.credentials import CredentialStore
from .._core.public_api import coerce_request
from .._core.schemas import (
    EditarImagemRequest as InternalImageEditRequest,
)
from .._core.schemas import (
    TextoImagemParaImagemRequest as InternalImageTransformationRequest,
)
from .._core.schemas import (
    TextoParaImagemRequest as InternalImageGenerationRequest,
)
from ..models import (
    ImageEditRequest,
    ImageGenerationRequest,
    ImageResult,
    ImageTransformationRequest,
)
from .providers import ImageRegistries, build_image_registries


def _registries(credentials: Mapping[str, str] | CredentialStore | None) -> ImageRegistries:
    return build_image_registries(credentials)


def generate(
    request: ImageGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> ImageResult:
    """Generate an image from a text prompt."""

    request = coerce_request(request, ImageGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).generate[provider]
    internal = InternalImageGenerationRequest(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        modelo=request.model,
        largura=request.width,
        altura=request.height,
        seed=request.seed,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    image_base64 = adapter.gerar(internal)
    return ImageResult(
        image_base64=image_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


async def generate_async(
    request: ImageGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> ImageResult:
    """Async variant of :func:`generate`."""

    request = coerce_request(request, ImageGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).generate[provider]
    internal = InternalImageGenerationRequest(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        modelo=request.model,
        largura=request.width,
        altura=request.height,
        seed=request.seed,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    image_base64 = await adapter.gerar_async(internal)
    return ImageResult(
        image_base64=image_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


def transform(
    request: ImageTransformationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> ImageResult:
    """Generate a new image using a prompt plus an input image."""

    request = coerce_request(request, ImageTransformationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).transform[provider]
    internal = InternalImageTransformationRequest(
        prompt=request.prompt,
        imagem=request.image,
        negative_prompt=request.negative_prompt,
        modelo=request.model,
        intensidade=request.strength,
        seed=request.seed,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    image_base64 = adapter.gerar(internal)
    return ImageResult(
        image_base64=image_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


async def transform_async(
    request: ImageTransformationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> ImageResult:
    """Async variant of :func:`transform`."""

    request = coerce_request(request, ImageTransformationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registries(credentials).transform[provider]
    internal = InternalImageTransformationRequest(
        prompt=request.prompt,
        imagem=request.image,
        negative_prompt=request.negative_prompt,
        modelo=request.model,
        intensidade=request.strength,
        seed=request.seed,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    image_base64 = await adapter.gerar_async(internal)
    return ImageResult(
        image_base64=image_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


def edit(
    request: ImageEditRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> ImageResult:
    """Edit an image with an optional mask."""

    request = coerce_request(request, ImageEditRequest, kwargs)
    provider = normalizar_api(request.provider)
    registries = _registries(credentials)
    adapter = (
        registries.edit_with_mask[provider]
        if request.mask is not None
        else registries.edit_without_mask[provider]
    )
    internal = InternalImageEditRequest(
        prompt=request.prompt,
        imagem=request.image,
        mascara=request.mask,
        negative_prompt=request.negative_prompt,
        modelo=request.model,
        seed=request.seed,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    image_base64 = adapter.gerar(internal)
    return ImageResult(
        image_base64=image_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


async def edit_async(
    request: ImageEditRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> ImageResult:
    """Async variant of :func:`edit`."""

    request = coerce_request(request, ImageEditRequest, kwargs)
    provider = normalizar_api(request.provider)
    registries = _registries(credentials)
    adapter = (
        registries.edit_with_mask[provider]
        if request.mask is not None
        else registries.edit_without_mask[provider]
    )
    internal = InternalImageEditRequest(
        prompt=request.prompt,
        imagem=request.image,
        mascara=request.mask,
        negative_prompt=request.negative_prompt,
        modelo=request.model,
        seed=request.seed,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )
    image_base64 = await adapter.gerar_async(internal)
    return ImageResult(
        image_base64=image_base64,
        metadata={"provider": provider, "model": adapter.resolve_model(internal.modelo)},
    )


__all__ = ["edit", "edit_async", "generate", "generate_async", "transform", "transform_async"]
