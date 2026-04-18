"""Shared HTTP client helpers built on top of httpx."""

from __future__ import annotations

from typing import Any

import httpx

from .config import DEFAULT_TIMEOUT_SECONDS, USER_AGENT
from .exceptions import InvalidProviderResponseError, ProviderTimeoutError

DEFAULT_LIMITS = httpx.Limits(max_connections=50, max_keepalive_connections=20)


def _build_timeout(timeout_seconds: float | None) -> httpx.Timeout:
    value = timeout_seconds or DEFAULT_TIMEOUT_SECONDS
    return httpx.Timeout(value, connect=min(value, 20.0), read=value, write=value, pool=value)


def create_http_client(
    *,
    base_url: str | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        timeout=_build_timeout(timeout_seconds),
        limits=DEFAULT_LIMITS,
        follow_redirects=True,
    )


def create_http_client_async(
    *,
    base_url: str | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        timeout=_build_timeout(timeout_seconds),
        limits=DEFAULT_LIMITS,
        follow_redirects=True,
    )


def is_retryable_http_exception(exc: Exception) -> bool:
    if isinstance(exc, ProviderTimeoutError | httpx.TimeoutException | httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
    return isinstance(exc, httpx.RequestError)


def validate_http_response(response: httpx.Response) -> httpx.Response:
    try:
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ProviderTimeoutError(str(exc)) from exc
    return response


def read_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover
        raise InvalidProviderResponseError("The provider returned a non-JSON body.") from exc
    if not isinstance(payload, dict):
        raise InvalidProviderResponseError("Expected a JSON object in the provider response.")
    return payload


# Internal compatibility aliases used by the ported provider layer.
criar_cliente_http = create_http_client
criar_cliente_http_async = create_http_client_async
excecao_e_retryable = is_retryable_http_exception
validar_resposta_http = validate_http_response
ler_json = read_json
