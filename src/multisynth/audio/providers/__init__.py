"""Audio provider registry builders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..._core.config import BASE_URL_ELEVENLABS, BASE_URL_STABILITY
from ..._core.credentials import CredentialStore, ensure_credential_store
from ..._core.provider_catalog import get_required_env_vars
from .._adapters import (
    AssemblyAIAdapter,
    AsyncMusicJobAdapter,
    AzureSpeechAdapter,
    BeatovenAdapter,
    CartesiaAdapter,
    DeepgramAdapter,
    ElevenLabsAdapter,
    GoogleMusicAdapter,
    HumeAdapter,
    LoudlyAdapter,
    MurfAdapter,
    MusicAdapter,
    RevAIAdapter,
    SpeechmaticsAdapter,
    SpeechToTextAdapter,
    TextToSpeechAdapter,
)


@dataclass(frozen=True, slots=True)
class AudioRegistries:
    transcription: dict[str, SpeechToTextAdapter]
    synthesis: dict[str, TextToSpeechAdapter]
    music: dict[str, MusicAdapter]


def build_audio_registries(credentials: Mapping[str, str] | CredentialStore | None = None) -> AudioRegistries:
    store = ensure_credential_store(credentials)
    transcription = {
        adapter.provider: adapter
        for adapter in (
            DeepgramAdapter(
                provider="deepgram",
                default_model="nova-3",
                supported_models=frozenset({"nova-3"}),
                api_key=store.resolve("DEEPGRAM_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "transcription", "deepgram"),
            ),
            AssemblyAIAdapter(
                provider="assemblyai",
                default_model="best",
                supported_models=frozenset({"best", "nano"}),
                api_key=store.resolve("ASSEMBLYAI_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "transcription", "assemblyai"),
            ),
            SpeechmaticsAdapter(
                provider="speechmatics",
                default_model="enhanced",
                supported_models=frozenset({"enhanced", "standard"}),
                api_key=store.resolve("SPEECHMATICS_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "transcription", "speechmatics"),
            ),
            RevAIAdapter(
                provider="revai",
                default_model="machine_v2",
                supported_models=frozenset({"machine_v2"}),
                api_key=store.resolve("REVAI_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "transcription", "revai"),
            ),
        )
    }
    synthesis = {
        adapter.provider: adapter
        for adapter in (
            CartesiaAdapter(
                provider="cartesia",
                default_model="sonic-2",
                supported_models=frozenset({"sonic-2"}),
                api_key=store.resolve("CARTESIA_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "synthesis", "cartesia"),
            ),
            AzureSpeechAdapter(
                provider="azure",
                default_model="azure-neural",
                supported_models=frozenset({"azure-neural"}),
                api_key=store.resolve("AZURE_SPEECH_API_KEY"),
                region=store.resolve("AZURE_SPEECH_REGION"),
                credential_env_vars=get_required_env_vars("audio", "synthesis", "azure"),
            ),
            HumeAdapter(
                provider="hume",
                default_model="octave-2",
                supported_models=frozenset({"octave-2"}),
                api_key=store.resolve("HUME_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "synthesis", "hume"),
            ),
            ElevenLabsAdapter(
                provider="elevenlabs",
                default_model="eleven_multilingual_v2",
                supported_models=frozenset({"eleven_multilingual_v2", "eleven_flash_v2_5"}),
                api_key=store.resolve("ELEVENLABS_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "synthesis", "elevenlabs"),
            ),
            MurfAdapter(
                provider="murf",
                default_model="murf-tts",
                supported_models=frozenset({"murf-tts"}),
                api_key=store.resolve("MURF_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "synthesis", "murf"),
            ),
        )
    }
    music = {
        adapter.provider: adapter
        for adapter in (
            GoogleMusicAdapter(
                provider="google",
                default_model="lyria-3.0-generate-001",
                supported_models=frozenset({"lyria-3.0-generate-001"}),
                api_key=store.resolve("GOOGLE_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "music", "google"),
            ),
            AsyncMusicJobAdapter(
                provider="elevenlabs",
                default_model="music_v1",
                supported_models=frozenset({"music_v1"}),
                api_key=store.resolve("ELEVENLABS_API_KEY"),
                base_url=BASE_URL_ELEVENLABS,
                create_path="/music",
                status_path="/music/{id}",
                auth_header_name="xi-api-key",
                auth_prefix="",
                credential_env_vars=get_required_env_vars("audio", "music", "elevenlabs"),
            ),
            AsyncMusicJobAdapter(
                provider="stability",
                default_model="stable-audio-2.0",
                supported_models=frozenset({"stable-audio-2.0"}),
                api_key=store.resolve("STABILITY_API_KEY"),
                base_url=BASE_URL_STABILITY,
                create_path="/v2beta/audio/stable-audio",
                status_path="/v2beta/audio/stable-audio/{id}",
                credential_env_vars=get_required_env_vars("audio", "music", "stability"),
            ),
            BeatovenAdapter(
                provider="beatoven",
                default_model="maestro",
                supported_models=frozenset({"maestro"}),
                api_key=store.resolve("BEATOVEN_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "music", "beatoven"),
            ),
            LoudlyAdapter(
                provider="loudly",
                default_model="VEGA_2",
                supported_models=frozenset({"VEGA_1", "VEGA_2"}),
                api_key=store.resolve("LOUDLY_API_KEY"),
                credential_env_vars=get_required_env_vars("audio", "music", "loudly"),
            ),
        )
    }
    return AudioRegistries(transcription=transcription, synthesis=synthesis, music=music)
