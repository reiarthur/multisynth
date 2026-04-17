"""Exact text pricing tables and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .config import COST_QUANTIZE, TOKEN_SCALE
from .exceptions import PricingUnavailableError


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Uso faturavel normalizado de uma chamada de texto."""

    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int = 0


@dataclass(frozen=True, slots=True)
class TextPricing:
    """Tabela de precificacao por provider/model.

    Valores sao sempre expressos em USD por 1 milhao de tokens. Quando um
    provider usa faixas de contexto distintas, os campos ``long_context_*``
    permitem um calculo exato baseado na contagem autoritativa retornada na
    resposta da propria API.
    """

    input_per_million: Decimal
    output_per_million: Decimal
    cached_input_per_million: Decimal | None = None
    long_context_threshold_tokens: int | None = None
    long_context_input_per_million: Decimal | None = None
    long_context_output_per_million: Decimal | None = None


PRICING_TABLE: dict[str, dict[str, TextPricing]] = {
    "openai": {
        "gpt-5-mini": TextPricing(
            input_per_million=Decimal("0.25"),
            output_per_million=Decimal("2.00"),
            cached_input_per_million=Decimal("0.025"),
        ),
        "gpt-5.4-mini": TextPricing(
            input_per_million=Decimal("0.75"),
            output_per_million=Decimal("4.50"),
            cached_input_per_million=Decimal("0.075"),
        ),
    },
    "groq": {
        "openai/gpt-oss-20b": TextPricing(
            input_per_million=Decimal("0.075"),
            output_per_million=Decimal("0.30"),
        ),
    },
    "together": {
        "openai/gpt-oss-20b": TextPricing(
            input_per_million=Decimal("0.05"),
            output_per_million=Decimal("0.20"),
        ),
    },
    "fireworks": {
        "openai/gpt-oss-20b": TextPricing(
            input_per_million=Decimal("0.07"),
            output_per_million=Decimal("0.30"),
        ),
    },
    "deepseek": {
        "deepseek-chat": TextPricing(
            input_per_million=Decimal("0.28"),
            output_per_million=Decimal("0.42"),
            cached_input_per_million=Decimal("0.028"),
        ),
    },
    "openrouter": {
        "openai/gpt-oss-20b:nitro": TextPricing(
            input_per_million=Decimal("0.03"),
            output_per_million=Decimal("0.11"),
        ),
    },
    "xai": {
        "grok-4-1-fast-reasoning": TextPricing(
            input_per_million=Decimal("0.20"),
            output_per_million=Decimal("0.50"),
            cached_input_per_million=Decimal("0.05"),
            long_context_threshold_tokens=128000,
            long_context_input_per_million=Decimal("0.40"),
            long_context_output_per_million=Decimal("1.00"),
        ),
    },
    "mistral": {
        "mistral-medium-2508+1": TextPricing(
            input_per_million=Decimal("0.40"),
            output_per_million=Decimal("2.00"),
        ),
    },
    "anthropic": {
        "claude-sonnet-4-5": TextPricing(
            input_per_million=Decimal("3.00"),
            output_per_million=Decimal("15.00"),
        ),
    },
    "google": {
        "gemini-2.5-flash": TextPricing(
            input_per_million=Decimal("0.30"),
            output_per_million=Decimal("2.50"),
            cached_input_per_million=Decimal("0.03"),
        ),
        "gemini-2.5-flash-lite": TextPricing(
            input_per_million=Decimal("0.10"),
            output_per_million=Decimal("0.40"),
            cached_input_per_million=Decimal("0.01"),
        ),
    },
    "cohere": {
        "command-a-03-2025": TextPricing(
            input_per_million=Decimal("2.50"),
            output_per_million=Decimal("10.00"),
        ),
    },
}


def obter_precificacao(provider: str, model: str) -> TextPricing:
    """Retorna a precificacao exata cadastrada para um provider/modelo."""

    try:
        return PRICING_TABLE[provider][model]
    except KeyError as exc:
        raise PricingUnavailableError(
            f"Nao ha precificacao exata cadastrada para provider={provider!r}, model={model!r}."
        ) from exc


def calcular_custo_usd(provider: str, model: str, usage: TokenUsage) -> Decimal:
    """Calcula custo exato em USD usando somente contadores autoritativos."""

    pricing = obter_precificacao(provider, model)
    if usage.prompt_tokens < 0 or usage.completion_tokens < 0 or usage.cached_prompt_tokens < 0:
        raise PricingUnavailableError("Contadores de uso invalidos impedem calculo exato.")
    prompt_nao_cacheado = max(usage.prompt_tokens - usage.cached_prompt_tokens, 0)
    input_rate = pricing.input_per_million
    output_rate = pricing.output_per_million
    if pricing.long_context_threshold_tokens is not None and usage.prompt_tokens > pricing.long_context_threshold_tokens:
        input_rate = pricing.long_context_input_per_million or pricing.input_per_million
        output_rate = pricing.long_context_output_per_million or pricing.output_per_million
    custo = (Decimal(prompt_nao_cacheado) / TOKEN_SCALE) * input_rate
    if usage.cached_prompt_tokens:
        if pricing.cached_input_per_million is None:
            raise PricingUnavailableError(
                f"O provider/modelo {provider}/{model} exige taxa de cache nao cadastrada."
            )
        custo += (Decimal(usage.cached_prompt_tokens) / TOKEN_SCALE) * pricing.cached_input_per_million
    custo += (Decimal(usage.completion_tokens) / TOKEN_SCALE) * output_rate
    return custo.quantize(COST_QUANTIZE)


PricingIndisponivelError = PricingUnavailableError
