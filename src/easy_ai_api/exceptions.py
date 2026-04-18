"""Exceções públicas disparadas por easy-ai-api.

Última atualização: 2026-04-18
"""

from ._core.exceptions import (
    ConfigurationError,
    EasyAiApiError,
    IncompatibleParameterError,
    InvalidParameterError,
    InvalidProviderResponseError,
    JobFailedError,
    MissingCredentialError,
    PricingUnavailableError,
    ProviderTimeoutError,
    TemporaryDownloadError,
    UnsupportedModelError,
    UnsupportedProviderError,
)

__all__ = [
    "ConfigurationError",
    "EasyAiApiError",
    "IncompatibleParameterError",
    "InvalidParameterError",
    "InvalidProviderResponseError",
    "JobFailedError",
    "MissingCredentialError",
    "PricingUnavailableError",
    "ProviderTimeoutError",
    "TemporaryDownloadError",
    "UnsupportedModelError",
    "UnsupportedProviderError",
]
