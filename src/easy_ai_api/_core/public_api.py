"""Shared helpers for the public modality modules."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

RequestModelT = TypeVar("RequestModelT", bound=BaseModel)


def coerce_request(
    request: RequestModelT | None,
    request_cls: type[RequestModelT],
    kwargs: dict[str, object],
) -> RequestModelT:
    """Merge positional request objects with keyword overrides."""

    if request is None:
        return request_cls(**kwargs)
    if not kwargs:
        return request
    payload = request.model_dump()
    payload.update(kwargs)
    return request_cls(**payload)
