"""Polling helpers for asynchronous provider jobs."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .config import DEFAULT_INITIAL_POLL_SECONDS, DEFAULT_MAX_POLL_SECONDS
from .exceptions import JobFailedError, ProviderTimeoutError

T = TypeVar("T")


def aguardar_job(
    buscar_estado: Callable[[], T],
    *,
    timeout_segundos: float,
    extrair_estado: Callable[[T], str],
    estados_sucesso: set[str],
    estados_falha: set[str],
) -> T:
    inicio = time.monotonic()
    intervalo = DEFAULT_INITIAL_POLL_SECONDS
    while True:
        snapshot = buscar_estado()
        estado = extrair_estado(snapshot).lower()
        if estado in {item.lower() for item in estados_sucesso}:
            return snapshot
        if estado in {item.lower() for item in estados_falha}:
            raise JobFailedError(f"Job finalizado com falha: {estado}")
        if time.monotonic() - inicio > timeout_segundos:
            raise ProviderTimeoutError("Timeout aguardando conclusao do job assincrono.")
        time.sleep(intervalo)
        intervalo = min(intervalo * 1.5, DEFAULT_MAX_POLL_SECONDS)


async def aguardar_job_async(
    buscar_estado: Callable[[], Awaitable[T]],
    *,
    timeout_segundos: float,
    extrair_estado: Callable[[T], str],
    estados_sucesso: set[str],
    estados_falha: set[str],
) -> T:
    inicio = time.monotonic()
    intervalo = DEFAULT_INITIAL_POLL_SECONDS
    while True:
        snapshot = await buscar_estado()
        estado = extrair_estado(snapshot).lower()
        if estado in {item.lower() for item in estados_sucesso}:
            return snapshot
        if estado in {item.lower() for item in estados_falha}:
            raise JobFailedError(f"Job finalizado com falha: {estado}")
        if time.monotonic() - inicio > timeout_segundos:
            raise ProviderTimeoutError("Timeout aguardando conclusao do job assincrono.")
        await asyncio.sleep(intervalo)
        intervalo = min(intervalo * 1.5, DEFAULT_MAX_POLL_SECONDS)
