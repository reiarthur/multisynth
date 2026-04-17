"""Canonical provider metadata used by registries, docs, and tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Describe one public provider capability exposed by the library."""

    modality: str
    operation: str
    provider: str
    env_vars: tuple[str, ...]


PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec("text", "generate", "openai", ("OPENAI_API_KEY",)),
    ProviderSpec("text", "generate", "groq", ("GROQ_API_KEY",)),
    ProviderSpec("text", "generate", "together", ("TOGETHER_API_KEY",)),
    ProviderSpec("text", "generate", "fireworks", ("FIREWORKS_API_KEY",)),
    ProviderSpec("text", "generate", "deepseek", ("DEEPSEEK_API_KEY",)),
    ProviderSpec("text", "generate", "openrouter", ("OPENROUTER_API_KEY",)),
    ProviderSpec("text", "generate", "xai", ("XAI_API_KEY",)),
    ProviderSpec("text", "generate", "mistral", ("MISTRAL_API_KEY",)),
    ProviderSpec("text", "generate", "anthropic", ("ANTHROPIC_API_KEY",)),
    ProviderSpec("text", "generate", "google", ("GOOGLE_API_KEY",)),
    ProviderSpec("text", "generate", "cohere", ("COHERE_API_KEY",)),
    ProviderSpec("text", "generate", "perplexity", ("PERPLEXITY_API_KEY",)),
    ProviderSpec("audio", "transcription", "deepgram", ("DEEPGRAM_API_KEY",)),
    ProviderSpec("audio", "transcription", "assemblyai", ("ASSEMBLYAI_API_KEY",)),
    ProviderSpec("audio", "transcription", "speechmatics", ("SPEECHMATICS_API_KEY",)),
    ProviderSpec("audio", "transcription", "revai", ("REVAI_API_KEY",)),
    ProviderSpec("audio", "synthesis", "cartesia", ("CARTESIA_API_KEY",)),
    ProviderSpec("audio", "synthesis", "azure", ("AZURE_SPEECH_API_KEY", "AZURE_SPEECH_REGION")),
    ProviderSpec("audio", "synthesis", "hume", ("HUME_API_KEY",)),
    ProviderSpec("audio", "synthesis", "elevenlabs", ("ELEVENLABS_API_KEY",)),
    ProviderSpec("audio", "synthesis", "murf", ("MURF_API_KEY",)),
    ProviderSpec("audio", "music", "google", ("GOOGLE_API_KEY",)),
    ProviderSpec("audio", "music", "elevenlabs", ("ELEVENLABS_API_KEY",)),
    ProviderSpec("audio", "music", "stability", ("STABILITY_API_KEY",)),
    ProviderSpec("audio", "music", "beatoven", ("BEATOVEN_API_KEY",)),
    ProviderSpec("audio", "music", "loudly", ("LOUDLY_API_KEY",)),
    ProviderSpec("image", "generate", "openai", ("OPENAI_API_KEY",)),
    ProviderSpec("image", "generate", "google", ("GOOGLE_API_KEY",)),
    ProviderSpec("image", "generate", "bfl", ("BFL_API_KEY",)),
    ProviderSpec("image", "generate", "ideogram", ("IDEOGRAM_API_KEY",)),
    ProviderSpec("image", "generate", "stability", ("STABILITY_API_KEY",)),
    ProviderSpec("image", "generate", "hedra", ("HEDRA_API_KEY",)),
    ProviderSpec("image", "transform", "openai", ("OPENAI_API_KEY",)),
    ProviderSpec("image", "transform", "google", ("GOOGLE_API_KEY",)),
    ProviderSpec("image", "transform", "bfl", ("BFL_API_KEY",)),
    ProviderSpec("image", "transform", "ideogram", ("IDEOGRAM_API_KEY",)),
    ProviderSpec("image", "transform", "stability", ("STABILITY_API_KEY",)),
    ProviderSpec("image", "edit", "openai", ("OPENAI_API_KEY",)),
    ProviderSpec("image", "edit", "google", ("GOOGLE_API_KEY",)),
    ProviderSpec("image", "edit", "bfl", ("BFL_API_KEY",)),
    ProviderSpec("image", "edit", "ideogram", ("IDEOGRAM_API_KEY",)),
    ProviderSpec("image", "edit", "stability", ("STABILITY_API_KEY",)),
    ProviderSpec("video", "generate_without_audio", "runway", ("RUNWAYML_API_SECRET",)),
    ProviderSpec("video", "generate_without_audio", "luma", ("LUMA_API_KEY",)),
    ProviderSpec("video", "generate_without_audio", "fal", ("FAL_KEY",)),
    ProviderSpec("video", "generate_without_audio", "hedra", ("HEDRA_API_KEY",)),
    ProviderSpec("video", "generate_with_audio", "google", ("GOOGLE_API_KEY",)),
    ProviderSpec("video", "generate_with_audio", "heygen", ("HEYGEN_API_KEY",)),
    ProviderSpec("video", "generate_with_audio", "did", ("DID_API_KEY",)),
    ProviderSpec("video", "generate_with_audio", "hedra", ("HEDRA_API_KEY",)),
    ProviderSpec("video", "lipsync", "heygen", ("HEYGEN_API_KEY",)),
    ProviderSpec("video", "lipsync", "did", ("DID_API_KEY",)),
    ProviderSpec("video", "lipsync", "hedra", ("HEDRA_API_KEY",)),
)

KNOWN_CREDENTIAL_ENV_VARS = frozenset(
    env_var
    for spec in PROVIDER_SPECS
    for env_var in spec.env_vars
)


def get_provider_specs(
    *,
    modality: str | None = None,
    operation: str | None = None,
) -> tuple[ProviderSpec, ...]:
    """Return provider specs filtered by modality and/or operation."""

    return tuple(
        spec
        for spec in PROVIDER_SPECS
        if (modality is None or spec.modality == modality)
        and (operation is None or spec.operation == operation)
    )


def get_required_env_vars(modality: str, operation: str, provider: str) -> tuple[str, ...]:
    """Return the configured env var names for one provider capability."""

    for spec in PROVIDER_SPECS:
        if (
            spec.modality == modality
            and spec.operation == operation
            and spec.provider == provider
        ):
            return spec.env_vars
    raise KeyError(
        f"No provider metadata registered for modality={modality!r}, "
        f"operation={operation!r}, provider={provider!r}."
    )
