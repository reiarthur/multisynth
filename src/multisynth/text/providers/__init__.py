"""Text provider registry builder."""

from __future__ import annotations

from collections.abc import Mapping

from ..._core.config import (
    BASE_URL_DEEPSEEK,
    BASE_URL_FIREWORKS,
    BASE_URL_GROQ,
    BASE_URL_MISTRAL,
    BASE_URL_OPENAI,
    BASE_URL_OPENROUTER,
    BASE_URL_PERPLEXITY,
    BASE_URL_TOGETHER,
    BASE_URL_XAI,
    USER_AGENT,
)
from ..._core.credentials import CredentialStore, ensure_credential_store
from ..._core.provider_catalog import get_required_env_vars
from .._adapters import (
    AnthropicTextAdapter,
    CohereTextAdapter,
    GoogleTextAdapter,
    OpenAICompatibleTextAdapter,
    TextProviderAdapter,
)


def build_text_registry(credentials: Mapping[str, str] | CredentialStore | None = None) -> dict[str, TextProviderAdapter]:
    store = ensure_credential_store(credentials)
    adapters = (
        OpenAICompatibleTextAdapter(
            provider="openai",
            default_model="gpt-5-mini",
            supported_models=frozenset({"gpt-5-mini", "gpt-5.4-mini"}),
            api_key=store.resolve("OPENAI_API_KEY"),
            aliases=frozenset({"open-ai"}),
            base_url=BASE_URL_OPENAI,
            credential_env_vars=get_required_env_vars("text", "generate", "openai"),
        ),
        OpenAICompatibleTextAdapter(
            provider="groq",
            default_model="openai/gpt-oss-20b",
            supported_models=frozenset({"openai/gpt-oss-20b"}),
            api_key=store.resolve("GROQ_API_KEY"),
            base_url=BASE_URL_GROQ,
            credential_env_vars=get_required_env_vars("text", "generate", "groq"),
        ),
        OpenAICompatibleTextAdapter(
            provider="together",
            default_model="openai/gpt-oss-20b",
            supported_models=frozenset({"openai/gpt-oss-20b"}),
            api_key=store.resolve("TOGETHER_API_KEY"),
            aliases=frozenset({"together-ai", "together_ai"}),
            base_url=BASE_URL_TOGETHER,
            credential_env_vars=get_required_env_vars("text", "generate", "together"),
        ),
        OpenAICompatibleTextAdapter(
            provider="fireworks",
            default_model="openai/gpt-oss-20b",
            supported_models=frozenset({"openai/gpt-oss-20b"}),
            api_key=store.resolve("FIREWORKS_API_KEY"),
            aliases=frozenset({"fireworks-ai", "fireworks_ai"}),
            base_url=BASE_URL_FIREWORKS,
            credential_env_vars=get_required_env_vars("text", "generate", "fireworks"),
        ),
        OpenAICompatibleTextAdapter(
            provider="deepseek",
            default_model="deepseek-chat",
            supported_models=frozenset({"deepseek-chat"}),
            api_key=store.resolve("DEEPSEEK_API_KEY"),
            base_url=BASE_URL_DEEPSEEK,
            credential_env_vars=get_required_env_vars("text", "generate", "deepseek"),
        ),
        OpenAICompatibleTextAdapter(
            provider="openrouter",
            default_model="openai/gpt-oss-20b:nitro",
            supported_models=frozenset({"openai/gpt-oss-20b:nitro"}),
            api_key=store.resolve("OPENROUTER_API_KEY"),
            base_url=BASE_URL_OPENROUTER,
            extra_headers={"X-Title": USER_AGENT},
            credential_env_vars=get_required_env_vars("text", "generate", "openrouter"),
        ),
        OpenAICompatibleTextAdapter(
            provider="xai",
            default_model="grok-4-1-fast-reasoning",
            supported_models=frozenset({"grok-4-1-fast-reasoning"}),
            api_key=store.resolve("XAI_API_KEY"),
            aliases=frozenset({"x-ai", "x_ai"}),
            base_url=BASE_URL_XAI,
            credential_env_vars=get_required_env_vars("text", "generate", "xai"),
        ),
        OpenAICompatibleTextAdapter(
            provider="mistral",
            default_model="mistral-medium-2508+1",
            supported_models=frozenset({"mistral-medium-2508+1"}),
            api_key=store.resolve("MISTRAL_API_KEY"),
            aliases=frozenset({"mistralai"}),
            base_url=BASE_URL_MISTRAL,
            credential_env_vars=get_required_env_vars("text", "generate", "mistral"),
        ),
        AnthropicTextAdapter(
            provider="anthropic",
            default_model="claude-sonnet-4-5",
            supported_models=frozenset({"claude-sonnet-4-5"}),
            api_key=store.resolve("ANTHROPIC_API_KEY"),
            credential_env_vars=get_required_env_vars("text", "generate", "anthropic"),
        ),
        GoogleTextAdapter(
            provider="google",
            default_model="gemini-2.5-flash",
            supported_models=frozenset({"gemini-2.5-flash", "gemini-2.5-flash-lite"}),
            api_key=store.resolve("GOOGLE_API_KEY"),
            aliases=frozenset({"gemini", "google-ai", "google_ai"}),
            credential_env_vars=get_required_env_vars("text", "generate", "google"),
        ),
        CohereTextAdapter(
            provider="cohere",
            default_model="command-a-03-2025",
            supported_models=frozenset({"command-a-03-2025"}),
            api_key=store.resolve("COHERE_API_KEY"),
            credential_env_vars=get_required_env_vars("text", "generate", "cohere"),
        ),
        OpenAICompatibleTextAdapter(
            provider="perplexity",
            default_model="sonar-pro",
            supported_models=frozenset({"sonar-pro"}),
            api_key=store.resolve("PERPLEXITY_API_KEY"),
            base_url=BASE_URL_PERPLEXITY,
            credential_env_vars=get_required_env_vars("text", "generate", "perplexity"),
        ),
    )
    return {adapter.provider: adapter for adapter in adapters}
