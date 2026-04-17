"""Retry helpers with exponential backoff."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .config import (
    DEFAULT_BACKOFF_MULTIPLIER,
    DEFAULT_INITIAL_BACKOFF_SECONDS,
    DEFAULT_MAX_BACKOFF_SECONDS,
)

T = TypeVar("T")


def executar_com_retry(
    operacao: Callable[[], T],
    *,
    max_tentativas: int,
    deve_tentar_novamente: Callable[[Exception], bool],
) -> T:
    atraso = DEFAULT_INITIAL_BACKOFF_SECONDS
    ultima_excecao: Exception | None = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            return operacao()
        except Exception as exc:  # noqa: BLE001
            ultima_excecao = exc
            if tentativa >= max_tentativas or not deve_tentar_novamente(exc):
                raise
            time.sleep(atraso)
            atraso = min(atraso * DEFAULT_BACKOFF_MULTIPLIER, DEFAULT_MAX_BACKOFF_SECONDS)
    assert ultima_excecao is not None
    raise ultima_excecao


async def executar_com_retry_async(
    operacao: Callable[[], Awaitable[T]],
    *,
    max_tentativas: int,
    deve_tentar_novamente: Callable[[Exception], bool],
) -> T:
    atraso = DEFAULT_INITIAL_BACKOFF_SECONDS
    ultima_excecao: Exception | None = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            return await operacao()
        except Exception as exc:  # noqa: BLE001
            ultima_excecao = exc
            if tentativa >= max_tentativas or not deve_tentar_novamente(exc):
                raise
            await asyncio.sleep(atraso)
            atraso = min(atraso * DEFAULT_BACKOFF_MULTIPLIER, DEFAULT_MAX_BACKOFF_SECONDS)
    assert ultima_excecao is not None
    raise ultima_excecao
