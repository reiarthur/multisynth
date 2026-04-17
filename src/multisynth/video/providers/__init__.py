"""Video provider registry builders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..._core.config import (
    BASE_URL_DID,
    BASE_URL_FAL,
    BASE_URL_HEYGEN,
    BASE_URL_LUMA,
    BASE_URL_RUNWAY,
    RUNWAY_API_VERSION,
)
from ..._core.credentials import CredentialStore, ensure_credential_store
from ..._core.provider_catalog import get_required_env_vars
from .._adapters import GenericVideoJobAdapter, GoogleVideoAdapter, HedraVideoAdapter, VideoAdapter


@dataclass(frozen=True, slots=True)
class VideoRegistries:
    without_audio: dict[str, VideoAdapter]
    with_audio: dict[str, VideoAdapter]
    lipsync: dict[str, VideoAdapter]


def build_video_registries(credentials: Mapping[str, str] | CredentialStore | None = None) -> VideoRegistries:
    store = ensure_credential_store(credentials)
    without_audio = {
        adapter.provider: adapter
        for adapter in (
            GenericVideoJobAdapter(
                provider="runway",
                default_model="gen4_turbo",
                supported_models=frozenset({"gen4_turbo", "gen3a_turbo"}),
                api_key=store.resolve("RUNWAYML_API_SECRET"),
                base_url=BASE_URL_RUNWAY,
                create_path="/image_to_video",
                status_path="/tasks/{id}",
                prompt_field="promptText",
                image_field="promptImage",
                extra_headers={"X-Runway-Version": RUNWAY_API_VERSION},
                credential_env_vars=get_required_env_vars("video", "generate_without_audio", "runway"),
            ),
            GenericVideoJobAdapter(
                provider="luma",
                default_model="ray-2",
                supported_models=frozenset({"ray-2", "ray-flash-2"}),
                api_key=store.resolve("LUMA_API_KEY"),
                base_url=BASE_URL_LUMA,
                create_path="/generations",
                status_path="/generations/{id}",
                prompt_field="prompt",
                image_field="keyframes",
                image_requires_public_url=True,
                credential_env_vars=get_required_env_vars("video", "generate_without_audio", "luma"),
            ),
            GenericVideoJobAdapter(
                provider="fal",
                default_model="fal-ai/pika/v2.2/text-to-video",
                supported_models=frozenset({"fal-ai/pika/v2.2/text-to-video"}),
                api_key=store.resolve("FAL_KEY"),
                base_url=BASE_URL_FAL,
                create_path="/fal-ai/pika/v2.2/text-to-video",
                status_path="/fal-ai/pika/v2.2/text-to-video/requests/{id}/status",
                auth_prefix="Key ",
                credential_env_vars=get_required_env_vars("video", "generate_without_audio", "fal"),
            ),
            HedraVideoAdapter(
                provider="hedra",
                default_model="827122cd-5fdd-4412-86f2-554f7bb8eef9",
                default_image_model="0435547d-1b30-41ad-bf66-ca476ff0564e",
                supported_models=frozenset(
                    {
                        "827122cd-5fdd-4412-86f2-554f7bb8eef9",
                        "0435547d-1b30-41ad-bf66-ca476ff0564e",
                    }
                ),
                api_key=store.resolve("HEDRA_API_KEY"),
                capability="sem_audio",
                credential_env_vars=get_required_env_vars("video", "generate_without_audio", "hedra"),
            ),
        )
    }
    with_audio = {
        adapter.provider: adapter
        for adapter in (
            GoogleVideoAdapter(
                provider="google",
                default_model="veo-3.1-generate-preview",
                supported_models=frozenset({"veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"}),
                api_key=store.resolve("GOOGLE_API_KEY"),
                credential_env_vars=get_required_env_vars("video", "generate_with_audio", "google"),
            ),
            GenericVideoJobAdapter(
                provider="heygen",
                default_model="avatar-iv",
                supported_models=frozenset({"avatar-iv"}),
                api_key=store.resolve("HEYGEN_API_KEY"),
                base_url=BASE_URL_HEYGEN,
                create_path="/video/generate",
                status_path="/video/{id}",
                prompt_field="script",
                image_field="avatar_image",
                audio_field="audio",
                auth_header_name="X-Api-Key",
                auth_prefix="",
                credential_env_vars=get_required_env_vars("video", "generate_with_audio", "heygen"),
            ),
            GenericVideoJobAdapter(
                provider="did",
                default_model="clips",
                supported_models=frozenset({"clips"}),
                api_key=store.resolve("DID_API_KEY"),
                base_url=BASE_URL_DID,
                create_path="/clips",
                status_path="/clips/{id}",
                prompt_field="script",
                image_field="source_url",
                audio_field="audio",
                auth_prefix="Basic ",
                image_requires_public_url=True,
                credential_env_vars=get_required_env_vars("video", "generate_with_audio", "did"),
            ),
            HedraVideoAdapter(
                provider="hedra",
                default_model="26f0fc66-152b-40ab-abed-76c43df99bc8",
                supported_models=frozenset(
                    {
                        "26f0fc66-152b-40ab-abed-76c43df99bc8",
                        "ab372b84-432f-44f5-bacc-c2542465f712",
                    }
                ),
                api_key=store.resolve("HEDRA_API_KEY"),
                capability="com_audio",
                credential_env_vars=get_required_env_vars("video", "generate_with_audio", "hedra"),
            ),
        )
    }
    lipsync = {
        adapter.provider: adapter
        for adapter in (
            GenericVideoJobAdapter(
                provider="heygen",
                default_model="avatar-iv",
                supported_models=frozenset({"avatar-iv"}),
                api_key=store.resolve("HEYGEN_API_KEY"),
                base_url=BASE_URL_HEYGEN,
                create_path="/video/generate",
                status_path="/video/{id}",
                prompt_field="script",
                image_field="avatar_image",
                audio_field="audio",
                auth_header_name="X-Api-Key",
                auth_prefix="",
                credential_env_vars=get_required_env_vars("video", "lipsync", "heygen"),
            ),
            GenericVideoJobAdapter(
                provider="did",
                default_model="talks",
                supported_models=frozenset({"talks"}),
                api_key=store.resolve("DID_API_KEY"),
                base_url=BASE_URL_DID,
                create_path="/talks",
                status_path="/talks/{id}",
                prompt_field="script",
                image_field="source_url",
                audio_field="audio",
                auth_prefix="Basic ",
                image_requires_public_url=True,
                credential_env_vars=get_required_env_vars("video", "lipsync", "did"),
            ),
            HedraVideoAdapter(
                provider="hedra",
                default_model="26f0fc66-152b-40ab-abed-76c43df99bc8",
                supported_models=frozenset(
                    {
                        "26f0fc66-152b-40ab-abed-76c43df99bc8",
                        "ab372b84-432f-44f5-bacc-c2542465f712",
                    }
                ),
                api_key=store.resolve("HEDRA_API_KEY"),
                capability="lipsync",
                credential_env_vars=get_required_env_vars("video", "lipsync", "hedra"),
            ),
        )
    }
    return VideoRegistries(without_audio=without_audio, with_audio=with_audio, lipsync=lipsync)
