"""Public text generation helpers for multisynth."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence

from .._core.aliases import normalizar_api
from .._core.config import DEFAULT_BATCH_CONCURRENCY
from .._core.credentials import CredentialStore
from .._core.exceptions import IncompatibleParameterError
from .._core.public_api import coerce_request
from .._core.schemas import TextoParaTextoRequest as InternalTextGenerationRequest
from .._core.schemas import TextoParaTextoResultado as InternalTextGenerationResult
from ..models import TextGenerationRequest, TextGenerationResult
from ._adapters import executar_lote_async
from .providers import build_text_registry


def _to_internal_request(request: TextGenerationRequest) -> InternalTextGenerationRequest:
    return InternalTextGenerationRequest(
        instrucoes=request.instructions,
        informacoes=request.context,
        api=request.provider,
        modelo=request.model,
        temperature=request.temperature,
        top_p=request.top_p,
        max_tokens=request.max_tokens,
        max_output_tokens=request.max_output_tokens,
        seed=request.seed,
        stop=request.stop,
        stream=request.stream,
        tools=request.tools,
        tool_choice=request.tool_choice,
        response_format=request.response_format,
        reasoning_effort=request.reasoning_effort,
        thinking=request.thinking,
        imagens_entrada=request.input_images,
        timeout_segundos=request.timeout_seconds,
        max_tentativas=request.max_retries,
        parametros_provider=request.provider_params,
    )


def _to_public_result(result: InternalTextGenerationResult) -> TextGenerationResult:
    return TextGenerationResult(text=result.texto, cost_usd=result.custo_usd)


def _registry(credentials: Mapping[str, str] | CredentialStore | None) -> dict[str, object]:
    return build_text_registry(credentials)


def generate(
    request: TextGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> TextGenerationResult:
    """Generate text with a single provider call.

    Args:
        request: Optional pre-built request model. When omitted, keyword
            arguments are validated into a ``TextGenerationRequest``.
        credentials: Optional explicit credential mapping. Values here override
            environment variables for this call only.
        **kwargs: Request fields such as ``provider``, ``instructions``,
            ``context``, sampling controls, multimodal inputs, or raw
            ``provider_params``.

    Returns:
        A ``TextGenerationResult`` containing generated text and exact cost when
        pricing is available for the selected provider/model pair.

    Raises:
        IncompatibleParameterError: If mutually exclusive arguments are used.
        MissingCredentialError: If the selected provider is not configured.
        UnsupportedProviderError: If ``provider`` is unknown.
        UnsupportedModelError: If the requested model is not supported.
        InvalidParameterError: If request validation fails.
        ProviderTimeoutError: If the provider times out.
        InvalidProviderResponseError: If the provider response cannot be parsed.
    """

    request = coerce_request(request, TextGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registry(credentials)[provider]
    return _to_public_result(adapter.gerar(_to_internal_request(request)))


async def generate_async(
    request: TextGenerationRequest | None = None,
    /,
    *,
    credentials: Mapping[str, str] | None = None,
    **kwargs: object,
) -> TextGenerationResult:
    """Async variant of :func:`generate`.

    Args:
        request: Optional request model.
        credentials: Optional explicit credential mapping.
        **kwargs: Request fields used to build ``TextGenerationRequest``.

    Returns:
        A ``TextGenerationResult`` for the completed generation call.
    """

    request = coerce_request(request, TextGenerationRequest, kwargs)
    provider = normalizar_api(request.provider)
    adapter = _registry(credentials)[provider]
    return _to_public_result(await adapter.gerar_async(_to_internal_request(request)))


def batch_generate(
    requests: Sequence[TextGenerationRequest],
    *,
    credentials: Mapping[str, str] | None = None,
    concurrency: int = DEFAULT_BATCH_CONCURRENCY,
) -> list[TextGenerationResult]:
    """Generate multiple text prompts with the same provider.

    Args:
        requests: A sequence of text generation requests. Every item must
            target the same canonical provider.
        credentials: Optional explicit credential mapping.
        concurrency: Maximum in-flight async tasks used by the internal batch
            runner when no event loop is active.

    Returns:
        Results in the same order as the input sequence.

    Raises:
        IncompatibleParameterError: If the batch mixes providers or if it is
            called while an event loop is already running.
    """

    if not requests:
        return []
    providers = {normalizar_api(item.provider) for item in requests}
    if len(providers) != 1:
        raise IncompatibleParameterError("All batch items must use the same provider.")
    provider = next(iter(providers))
    adapter = _registry(credentials)[provider]
    internal_requests = [_to_internal_request(item) for item in requests]
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        results = asyncio.run(
            executar_lote_async(adapter, internal_requests, concorrencia=concurrency)
        )
        return [_to_public_result(result) for result in results]
    raise IncompatibleParameterError(
        "An event loop is already running. Use `await batch_generate_async(...)`."
    )


async def batch_generate_async(
    requests: Sequence[TextGenerationRequest],
    *,
    credentials: Mapping[str, str] | None = None,
    concurrency: int = DEFAULT_BATCH_CONCURRENCY,
) -> list[TextGenerationResult]:
    """Async variant of :func:`batch_generate`."""

    if not requests:
        return []
    providers = {normalizar_api(item.provider) for item in requests}
    if len(providers) != 1:
        raise IncompatibleParameterError("All batch items must use the same provider.")
    provider = next(iter(providers))
    adapter = _registry(credentials)[provider]
    results = await executar_lote_async(
        adapter,
        [_to_internal_request(item) for item in requests],
        concorrencia=concurrency,
    )
    return [_to_public_result(result) for result in results]


__all__ = ["batch_generate", "batch_generate_async", "generate", "generate_async"]
