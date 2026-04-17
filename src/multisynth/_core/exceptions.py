"""Typed exceptions shared across the internal core and public API."""

from __future__ import annotations


class MultisynthError(Exception):
    """Base error for all public and internal multisynth failures."""


class ConfigurationError(MultisynthError):
    """Missing or inconsistent runtime configuration."""


class MissingCredentialError(ConfigurationError):
    """Required provider credentials are missing from explicit or env configuration.

    Attributes:
        provider: Canonical provider name that needs credentials.
        env_vars: Environment variable names that must be set.
    """

    def __init__(self, provider: str, env_vars: str | tuple[str, ...], *, detail: str | None = None) -> None:
        normalized = (env_vars,) if isinstance(env_vars, str) else tuple(env_vars)
        self.provider = provider
        self.env_vars = normalized
        expected = ", ".join(normalized)
        hint = (
            f"Set {expected} in your environment or pass them through "
            f"`credentials={{...}}` when calling multisynth."
        )
        message = detail or (
            f"Provider {provider!r} requires credential environment variable(s): "
            f"{expected}. {hint}"
        )
        super().__init__(message)


class UnsupportedProviderError(MultisynthError):
    """Unknown provider alias."""


class UnsupportedModelError(MultisynthError):
    """Provider/model combination is not supported by the library contract."""


class InvalidParameterError(MultisynthError):
    """One accepted parameter has an invalid value."""


class IncompatibleParameterError(MultisynthError):
    """A set of parameters is mutually incompatible."""


class PricingUnavailableError(MultisynthError):
    """Exact pricing cannot be computed for the selected provider/model."""


class ProviderTimeoutError(MultisynthError):
    """HTTP or polling timeout raised by a provider call."""


class JobFailedError(MultisynthError):
    """A long-running provider job finished in a failed state."""


class TemporaryDownloadError(MultisynthError):
    """A temporary asset URL could not be downloaded safely."""


class InvalidProviderResponseError(MultisynthError):
    """Provider returned a shape that the adapter cannot parse."""


# Internal compatibility aliases used by the ported provider layer.
NovaIntegracaoError = MultisynthError
ConfiguracaoAmbienteError = ConfigurationError
ApiNaoSuportadaError = UnsupportedProviderError
ModeloNaoSuportadoError = UnsupportedModelError
ParametroInvalidoError = InvalidParameterError
ParametroIncompativelError = IncompatibleParameterError
PricingIndisponivelError = PricingUnavailableError
TimeoutProvedorError = ProviderTimeoutError
JobFalhouError = JobFailedError
DownloadTemporarioError = TemporaryDownloadError
RespostaInvalidaProviderError = InvalidProviderResponseError
