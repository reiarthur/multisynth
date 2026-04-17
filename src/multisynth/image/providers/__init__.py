"""Image provider registry builders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..._core.credentials import CredentialStore, ensure_credential_store
from ..._core.provider_catalog import get_required_env_vars
from .._adapters import (
    BFLImageAdapter,
    GoogleImageAdapter,
    HedraImageAdapter,
    IdeogramImageAdapter,
    ImageAdapter,
    OpenAIImageAdapter,
    StabilityImageAdapter,
)


@dataclass(frozen=True, slots=True)
class ImageRegistries:
    generate: dict[str, ImageAdapter]
    transform: dict[str, ImageAdapter]
    edit_without_mask: dict[str, ImageAdapter]
    edit_with_mask: dict[str, ImageAdapter]


def build_image_registries(credentials: Mapping[str, str] | CredentialStore | None = None) -> ImageRegistries:
    store = ensure_credential_store(credentials)
    generate = {
        adapter.provider: adapter
        for adapter in (
            OpenAIImageAdapter(
                provider="openai",
                default_model="gpt-image-1",
                supported_models=frozenset({"gpt-image-1"}),
                api_key=store.resolve("OPENAI_API_KEY"),
                capability="text_to_image",
                credential_env_vars=get_required_env_vars("image", "generate", "openai"),
            ),
            GoogleImageAdapter(
                provider="google",
                default_model="imagen-4.0-generate-001",
                supported_models=frozenset({"imagen-4.0-generate-001", "imagen-4.0-ultra-generate-001"}),
                api_key=store.resolve("GOOGLE_API_KEY"),
                capability="text_to_image",
                credential_env_vars=get_required_env_vars("image", "generate", "google"),
            ),
            BFLImageAdapter(
                provider="bfl",
                default_model="flux-pro-1.1",
                supported_models=frozenset({"flux-pro-1.1", "flux-pro-1.1-ultra"}),
                api_key=store.resolve("BFL_API_KEY"),
                credential_env_vars=get_required_env_vars("image", "generate", "bfl"),
            ),
            IdeogramImageAdapter(
                provider="ideogram",
                default_model="V_3",
                supported_models=frozenset({"V_3", "V_2A"}),
                api_key=store.resolve("IDEOGRAM_API_KEY"),
                endpoint="/generate",
                credential_env_vars=get_required_env_vars("image", "generate", "ideogram"),
            ),
            StabilityImageAdapter(
                provider="stability",
                default_model="sd3.5-large",
                supported_models=frozenset({"sd3.5-large", "sd3.5-large-turbo"}),
                api_key=store.resolve("STABILITY_API_KEY"),
                endpoint="/v2beta/stable-image/generate/core",
                mode="generate",
                credential_env_vars=get_required_env_vars("image", "generate", "stability"),
            ),
            HedraImageAdapter(
                provider="hedra",
                default_model="a66300b4-f76e-4c4a-ac41-b31694ff585e",
                supported_models=frozenset({"a66300b4-f76e-4c4a-ac41-b31694ff585e"}),
                api_key=store.resolve("HEDRA_API_KEY"),
                credential_env_vars=get_required_env_vars("image", "generate", "hedra"),
            ),
        )
    }
    transform = {
        adapter.provider: adapter
        for adapter in (
            OpenAIImageAdapter(
                provider="openai",
                default_model="gpt-image-1",
                supported_models=frozenset({"gpt-image-1"}),
                api_key=store.resolve("OPENAI_API_KEY"),
                capability="image_to_image",
                credential_env_vars=get_required_env_vars("image", "transform", "openai"),
            ),
            GoogleImageAdapter(
                provider="google",
                default_model="gemini-2.5-flash-image-preview",
                supported_models=frozenset({"gemini-2.5-flash-image-preview"}),
                api_key=store.resolve("GOOGLE_API_KEY"),
                capability="image_to_image",
                credential_env_vars=get_required_env_vars("image", "transform", "google"),
            ),
            BFLImageAdapter(
                provider="bfl",
                default_model="flux-kontext-pro",
                supported_models=frozenset({"flux-kontext-pro", "flux-kontext-max"}),
                api_key=store.resolve("BFL_API_KEY"),
                credential_env_vars=get_required_env_vars("image", "transform", "bfl"),
            ),
            IdeogramImageAdapter(
                provider="ideogram",
                default_model="V_3",
                supported_models=frozenset({"V_3", "V_2A"}),
                api_key=store.resolve("IDEOGRAM_API_KEY"),
                endpoint="/remix",
                credential_env_vars=get_required_env_vars("image", "transform", "ideogram"),
            ),
            StabilityImageAdapter(
                provider="stability",
                default_model="sd3.5-large",
                supported_models=frozenset({"sd3.5-large", "sd3.5-large-turbo"}),
                api_key=store.resolve("STABILITY_API_KEY"),
                endpoint="/v2beta/stable-image/edit/search-and-replace",
                mode="image_to_image",
                credential_env_vars=get_required_env_vars("image", "transform", "stability"),
            ),
        )
    }
    edit_without_mask = {
        adapter.provider: adapter
        for adapter in (
            OpenAIImageAdapter(
                provider="openai",
                default_model="gpt-image-1",
                supported_models=frozenset({"gpt-image-1"}),
                api_key=store.resolve("OPENAI_API_KEY"),
                capability="edit_no_mask",
                credential_env_vars=get_required_env_vars("image", "edit", "openai"),
            ),
            GoogleImageAdapter(
                provider="google",
                default_model="gemini-2.5-flash-image-preview",
                supported_models=frozenset({"gemini-2.5-flash-image-preview"}),
                api_key=store.resolve("GOOGLE_API_KEY"),
                capability="edit_no_mask",
                credential_env_vars=get_required_env_vars("image", "edit", "google"),
            ),
            BFLImageAdapter(
                provider="bfl",
                default_model="flux-kontext-pro",
                supported_models=frozenset({"flux-kontext-pro", "flux-kontext-max"}),
                api_key=store.resolve("BFL_API_KEY"),
                credential_env_vars=get_required_env_vars("image", "edit", "bfl"),
            ),
            IdeogramImageAdapter(
                provider="ideogram",
                default_model="V_3",
                supported_models=frozenset({"V_3", "V_2A"}),
                api_key=store.resolve("IDEOGRAM_API_KEY"),
                endpoint="/remix",
                credential_env_vars=get_required_env_vars("image", "edit", "ideogram"),
            ),
            StabilityImageAdapter(
                provider="stability",
                default_model="sd3.5-large",
                supported_models=frozenset({"sd3.5-large", "sd3.5-large-turbo"}),
                api_key=store.resolve("STABILITY_API_KEY"),
                endpoint="/v2beta/stable-image/edit/search-and-replace",
                mode="edit_no_mask",
                credential_env_vars=get_required_env_vars("image", "edit", "stability"),
            ),
        )
    }
    edit_with_mask = {
        adapter.provider: adapter
        for adapter in (
            OpenAIImageAdapter(
                provider="openai",
                default_model="gpt-image-1",
                supported_models=frozenset({"gpt-image-1"}),
                api_key=store.resolve("OPENAI_API_KEY"),
                capability="edit_with_mask",
                credential_env_vars=get_required_env_vars("image", "edit", "openai"),
            ),
            GoogleImageAdapter(
                provider="google",
                default_model="imagen-4.0-generate-001",
                supported_models=frozenset({"imagen-4.0-generate-001"}),
                api_key=store.resolve("GOOGLE_API_KEY"),
                capability="edit_with_mask",
                credential_env_vars=get_required_env_vars("image", "edit", "google"),
            ),
            IdeogramImageAdapter(
                provider="ideogram",
                default_model="V_3",
                supported_models=frozenset({"V_3", "V_2A"}),
                api_key=store.resolve("IDEOGRAM_API_KEY"),
                endpoint="/edit",
                credential_env_vars=get_required_env_vars("image", "edit", "ideogram"),
            ),
            StabilityImageAdapter(
                provider="stability",
                default_model="sd3.5-large",
                supported_models=frozenset({"sd3.5-large", "sd3.5-large-turbo"}),
                api_key=store.resolve("STABILITY_API_KEY"),
                endpoint="/v2beta/stable-image/edit/inpaint",
                mode="edit_with_mask",
                credential_env_vars=get_required_env_vars("image", "edit", "stability"),
            ),
        )
    }
    return ImageRegistries(
        generate=generate,
        transform=transform,
        edit_without_mask=edit_without_mask,
        edit_with_mask=edit_with_mask,
    )
