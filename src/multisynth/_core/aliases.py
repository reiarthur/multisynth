"""Normalization of public provider aliases."""

from __future__ import annotations

import re

from .exceptions import InvalidParameterError, UnsupportedProviderError

_ALIASES_PADRAO: dict[str, set[str]] = {
    "openai": {"open-ai"},
    "groq": set(),
    "together": {"together-ai", "together_ai"},
    "fireworks": {"fireworks-ai", "fireworks_ai"},
    "deepseek": {"deep-seek"},
    "openrouter": {"open-router"},
    "xai": {"x-ai", "x_ai"},
    "mistral": {"mistralai"},
    "anthropic": set(),
    "google": {"gemini", "google-ai", "google_ai", "imagen", "veo", "lyria"},
    "cohere": set(),
    "perplexity": {"pplx"},
    "ideogram": set(),
    "stability": {"stability-ai", "stable-diffusion"},
    "bfl": {"flux", "black-forest-labs", "black_forest_labs"},
    "deepgram": set(),
    "assemblyai": {"assembly-ai"},
    "speechmatics": set(),
    "revai": {"rev-ai", "rev_ai"},
    "cartesia": set(),
    "azure": {"azure-speech", "azure_speech", "microsoft-azure"},
    "hume": set(),
    "elevenlabs": {"eleven-labs"},
    "murf": set(),
    "beatoven": {"beatoven-ai", "beatoven_ai"},
    "loudly": set(),
    "runway": {"runwayml", "runway-ml"},
    "luma": {"lumalabs", "luma-dream-machine"},
    "fal": {"fal-ai"},
    "heygen": {"hey-gen"},
    "did": {"d-id", "d_id"},
    "hedra": set(),
}


def _canonizar(valor: str) -> str:
    if not isinstance(valor, str):
        raise InvalidParameterError("`provider` must be a string.")
    canonico = re.sub(r"[^a-z0-9]+", "-", valor.strip().lower()).strip("-")
    if not canonico:
        raise InvalidParameterError("`provider` cannot be empty.")
    return canonico


def normalizar_api(api: str, aliases_extras: dict[str, set[str]] | None = None) -> str:
    """Normalize a provider alias into the canonical provider name."""

    consulta = _canonizar(api)
    tabela: dict[str, set[str]] = {k: set(v) for k, v in _ALIASES_PADRAO.items()}
    if aliases_extras:
        for provider, aliases in aliases_extras.items():
            tabela.setdefault(provider, set()).update({_canonizar(alias) for alias in aliases})
    for provider, aliases in tabela.items():
        if consulta == provider or consulta in aliases:
            return provider
    raise UnsupportedProviderError(f"Unsupported provider: {api!r}.")
