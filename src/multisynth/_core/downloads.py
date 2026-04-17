"""Safe download helpers for temporary provider assets."""

from __future__ import annotations

from typing import Any

from .config import DEFAULT_DOWNLOAD_TIMEOUT_SECONDS
from .exceptions import TemporaryDownloadError
from .http import create_http_client, create_http_client_async, validate_http_response


def download_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
) -> bytes:
    try:
        with create_http_client(headers=headers, timeout_seconds=timeout_seconds) as client:
            response = validate_http_response(client.get(url))
            return response.content
    except Exception as exc:  # noqa: BLE001
        raise TemporaryDownloadError(f"Failed to download temporary asset: {url}") from exc


async def download_bytes_async(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
) -> bytes:
    try:
        async with create_http_client_async(headers=headers, timeout_seconds=timeout_seconds) as client:
            response = validate_http_response(await client.get(url))
            return response.content
    except Exception as exc:  # noqa: BLE001
        raise TemporaryDownloadError(f"Failed to download temporary asset: {url}") from exc


def first_url(payload: dict[str, Any], *paths: tuple[str, ...]) -> str | None:

    for path in paths:
        cursor: Any = payload
        for key in path:
            if isinstance(cursor, list):
                if not cursor:
                    cursor = None
                    break
                cursor = cursor[0]
            if not isinstance(cursor, dict):
                cursor = None
                break
            cursor = cursor.get(key)
        if isinstance(cursor, str) and cursor.startswith(("http://", "https://")):
            return cursor
    return None


# Internal compatibility aliases used by the ported provider layer.
baixar_bytes_sync = download_bytes
baixar_bytes_async = download_bytes_async
extrair_primeiro_url = first_url
