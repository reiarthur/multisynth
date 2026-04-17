"""Infraestrutura compartilhada para adapters de ``texto_para_texto``."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .._core.config import (
    BASE_URL_ANTHROPIC,
    BASE_URL_COHERE,
    BASE_URL_GOOGLE,
)
from .._core.exceptions import (
    MissingCredentialError,
    ModeloNaoSuportadoError,
    RespostaInvalidaProviderError,
)
from .._core.http import (
    criar_cliente_http,
    criar_cliente_http_async,
    excecao_e_retryable,
    ler_json,
    validar_resposta_http,
)
from .._core.media import codificar_base64, normalizar_entrada_binaria
from .._core.pricing import TokenUsage, calcular_custo_usd, obter_precificacao
from .._core.retry import executar_com_retry, executar_com_retry_async
from .._core.schemas import TextoParaTextoRequest, TextoParaTextoResultado


def _serializar_informacoes(informacoes: Any) -> str:
    if informacoes is None:
        return ""
    if isinstance(informacoes, str):
        return informacoes
    return json.dumps(informacoes, ensure_ascii=False, separators=(",", ":"), default=str)


def _montar_prompt_usuario(request: TextoParaTextoRequest) -> str:
    informacoes = _serializar_informacoes(request.informacoes)
    if not informacoes:
        return request.instrucoes
    return (
        "Siga as instrucoes do sistema e utilize as informacoes abaixo como contexto principal.\n\n"
        f"{informacoes}"
    )


def _montar_partes_multimodais(request: TextoParaTextoRequest) -> list[dict[str, Any]]:
    partes: list[dict[str, Any]] = [{"type": "text", "text": _montar_prompt_usuario(request)}]
    for imagem in request.imagens_entrada or []:
        normalizada = normalizar_entrada_binaria(imagem, nome_campo="imagens_entrada")
        mime_type = normalizada.mime_type or "image/png"
        partes.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{codificar_base64(normalizada.dados)}",
                },
            }
        )
    return partes


def _extrair_texto_openai_compat(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RespostaInvalidaProviderError("Resposta OpenAI-compatible sem `choices`.")
    mensagem = choices[0].get("message", {})
    conteudo = mensagem.get("content", "")
    if isinstance(conteudo, str):
        return conteudo.strip()
    if isinstance(conteudo, list):
        partes: list[str] = []
        for item in conteudo:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                partes.append(item["text"])
        texto = "".join(partes).strip()
        if texto:
            return texto
    raise RespostaInvalidaProviderError("Nao foi possivel extrair texto da resposta.")


def _extrair_usage_openai_compat(payload: dict[str, Any]) -> TokenUsage:
    usage = payload.get("usage", {})
    prompt_details = usage.get("prompt_tokens_details", {}) if isinstance(usage, dict) else {}
    return TokenUsage(
        prompt_tokens=int(usage.get("prompt_tokens", 0)),
        completion_tokens=int(usage.get("completion_tokens", 0)),
        cached_prompt_tokens=int(prompt_details.get("cached_tokens", 0)),
    )


@dataclass(frozen=True, slots=True)
class TextProviderAdapter(ABC):
    """Classe base para adapters de ``texto_para_texto``.

    Cada adapter encapsula:

    - autenticacao por unica chave/token simples;
    - endpoint oficial do provider;
    - modelos suportados com override permitido;
    - estrategia de parsing da resposta e dos contadores de uso;
    - calculo de custo exato usando a camada compartilhada de pricing.
    """

    provider: str
    default_model: str
    supported_models: frozenset[str]
    api_key: str | None
    aliases: frozenset[str] = field(default_factory=frozenset)
    credential_env_vars: tuple[str, ...] = field(default_factory=tuple, kw_only=True)

    def resolve_model(self, model: str | None) -> str:
        final_model = (model or self.default_model).strip()
        if final_model not in self.supported_models:
            raise ModeloNaoSuportadoError(
                f"Modelo nao suportado para provider={self.provider!r}: {final_model!r}"
            )
        return final_model

    def ensure_api_key(self) -> str:
        if not self.api_key:
            raise MissingCredentialError(
                provider=self.provider,
                env_vars=self.credential_env_vars or ("API_KEY",),
            )
        return self.api_key

    def ensure_precificacao(self, model: str) -> None:
        obter_precificacao(self.provider, model)

    def gerar(self, request: TextoParaTextoRequest) -> TextoParaTextoResultado:
        model = self.resolve_model(request.modelo)
        self.ensure_precificacao(model)
        texto, usage = self._gerar_sync(request=request, model=model)
        return TextoParaTextoResultado(texto=texto, custo_usd=calcular_custo_usd(self.provider, model, usage))

    async def gerar_async(self, request: TextoParaTextoRequest) -> TextoParaTextoResultado:
        model = self.resolve_model(request.modelo)
        self.ensure_precificacao(model)
        texto, usage = await self._gerar_async(request=request, model=model)
        return TextoParaTextoResultado(texto=texto, custo_usd=calcular_custo_usd(self.provider, model, usage))

    @abstractmethod
    def _gerar_sync(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        raise NotImplementedError

    @abstractmethod
    async def _gerar_async(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class OpenAICompatibleTextAdapter(TextProviderAdapter):
    """Adapter para providers que expoem ``/chat/completions`` OpenAI-compatible."""

    base_url: str = ""
    extra_headers: dict[str, str] = field(default_factory=dict)

    def _montar_payload(self, request: TextoParaTextoRequest, model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.instrucoes},
                {"role": "user", "content": _montar_partes_multimodais(request)},
            ],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        limite = request.max_output_tokens or request.max_tokens
        if limite is not None:
            payload["max_tokens"] = limite
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.stop is not None:
            payload["stop"] = request.stop
        if request.stream:
            payload["stream"] = True
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        if request.response_format is not None:
            payload["response_format"] = request.response_format
        if request.reasoning_effort is not None:
            payload["reasoning_effort"] = request.reasoning_effort
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def _request_sync(self, *, request: TextoParaTextoRequest, model: str) -> dict[str, Any]:
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {api_key}", **self.extra_headers},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(client.post("/chat/completions", json=self._montar_payload(request, model)))
                return ler_json(response)

        return executar_com_retry(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )

    async def _request_async(self, *, request: TextoParaTextoRequest, model: str) -> dict[str, Any]:
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {api_key}", **self.extra_headers},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post("/chat/completions", json=self._montar_payload(request, model))
                )
                return ler_json(response)

        return await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )

    def _gerar_sync(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        payload = self._request_sync(request=request, model=model)
        return _extrair_texto_openai_compat(payload), _extrair_usage_openai_compat(payload)

    async def _gerar_async(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        payload = await self._request_async(request=request, model=model)
        return _extrair_texto_openai_compat(payload), _extrair_usage_openai_compat(payload)


@dataclass(frozen=True, slots=True)
class AnthropicTextAdapter(TextProviderAdapter):
    """Adapter para a API oficial ``/v1/messages`` da Anthropic."""

    anthropic_version: str = "2023-06-01"

    def _montar_payload(self, request: TextoParaTextoRequest, model: str) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": _montar_prompt_usuario(request)}]
        for imagem in request.imagens_entrada or []:
            normalizada = normalizar_entrada_binaria(imagem, nome_campo="imagens_entrada")
            media_type = normalizada.mime_type or "image/png"
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": codificar_base64(normalizada.dados),
                    },
                }
            )
        payload: dict[str, Any] = {
            "model": model,
            "system": request.instrucoes,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": request.max_output_tokens or request.max_tokens or 1024,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop is not None:
            payload["stop_sequences"] = [request.stop] if isinstance(request.stop, str) else request.stop
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        if request.thinking is not None:
            payload["thinking"] = request.thinking
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def _parse(self, payload: dict[str, Any]) -> tuple[str, TokenUsage]:
        blocos = payload.get("content")
        if not isinstance(blocos, list):
            raise RespostaInvalidaProviderError("Resposta Anthropic sem `content` em lista.")
        texto = "".join(
            bloco.get("text", "")
            for bloco in blocos
            if isinstance(bloco, dict) and bloco.get("type") == "text"
        ).strip()
        if not texto:
            raise RespostaInvalidaProviderError("Resposta Anthropic sem texto utilizavel.")
        usage = payload.get("usage", {})
        return texto, TokenUsage(
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
        )

    def _gerar_sync(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_ANTHROPIC,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": self.anthropic_version,
                    "content-type": "application/json",
                },
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(client.post("/messages", json=self._montar_payload(request, model)))
                return ler_json(response)

        return self._parse(
            executar_com_retry(
                operacao,
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
        )

    async def _gerar_async(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_ANTHROPIC,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": self.anthropic_version,
                    "content-type": "application/json",
                },
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(await client.post("/messages", json=self._montar_payload(request, model)))
                return ler_json(response)

        payload = await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return self._parse(payload)


@dataclass(frozen=True, slots=True)
class GoogleTextAdapter(TextProviderAdapter):
    """Adapter para Gemini API via Google AI Studio API key."""

    def _montar_payload(self, request: TextoParaTextoRequest) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [{"text": _montar_prompt_usuario(request)}]
        for imagem in request.imagens_entrada or []:
            normalizada = normalizar_entrada_binaria(imagem, nome_campo="imagens_entrada")
            parts.append(
                {
                    "inline_data": {
                        "mime_type": normalizada.mime_type or "image/png",
                        "data": codificar_base64(normalizada.dados),
                    }
                }
            )
        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        limite = request.max_output_tokens or request.max_tokens
        if limite is not None:
            generation_config["maxOutputTokens"] = limite
        if request.stop is not None:
            generation_config["stopSequences"] = [request.stop] if isinstance(request.stop, str) else request.stop
        if request.seed is not None:
            generation_config["seed"] = request.seed
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": request.instrucoes}]},
            "contents": [{"role": "user", "parts": parts}],
        }
        if generation_config:
            payload["generationConfig"] = generation_config
        if request.tools:
            payload["tools"] = request.tools
        if request.response_format:
            payload.setdefault("generationConfig", {}).update(request.response_format)
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def _parse(self, payload: dict[str, Any]) -> tuple[str, TokenUsage]:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise RespostaInvalidaProviderError("Resposta Gemini sem `candidates`.")
        partes = candidates[0].get("content", {}).get("parts", [])
        texto = "".join(
            parte.get("text", "")
            for parte in partes
            if isinstance(parte, dict) and isinstance(parte.get("text"), str)
        ).strip()
        if not texto:
            raise RespostaInvalidaProviderError("Resposta Gemini sem texto.")
        usage = payload.get("usageMetadata", {})
        return texto, TokenUsage(
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
            cached_prompt_tokens=int(usage.get("cachedContentTokenCount", 0)),
        )

    def _gerar_sync(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
                response = validar_resposta_http(
                    client.post(f"/models/{model}:generateContent", params={"key": api_key}, json=self._montar_payload(request))
                )
                return ler_json(response)

        return self._parse(
            executar_com_retry(
                operacao,
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
        )

    async def _gerar_async(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
                response = validar_resposta_http(
                    await client.post(
                        f"/models/{model}:generateContent",
                        params={"key": api_key},
                        json=self._montar_payload(request),
                    )
                )
                return ler_json(response)

        payload = await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return self._parse(payload)


@dataclass(frozen=True, slots=True)
class CohereTextAdapter(TextProviderAdapter):
    """Adapter para a API oficial ``/v2/chat`` da Cohere."""

    def _montar_payload(self, request: TextoParaTextoRequest, model: str) -> dict[str, Any]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": request.instrucoes},
            {"role": "user", "content": _montar_prompt_usuario(request)},
        ]
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["p"] = request.top_p
        limite = request.max_output_tokens or request.max_tokens
        if limite is not None:
            payload["max_tokens"] = limite
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.stop is not None:
            payload["stop_sequences"] = [request.stop] if isinstance(request.stop, str) else request.stop
        if request.tools:
            payload["tools"] = request.tools
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def _parse(self, payload: dict[str, Any]) -> tuple[str, TokenUsage]:
        message = payload.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            raise RespostaInvalidaProviderError("Resposta Cohere sem `message.content` em lista.")
        texto = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ).strip()
        if not texto:
            raise RespostaInvalidaProviderError("Resposta Cohere sem texto.")
        usage = payload.get("usage", {})
        tokens = usage.get("tokens", {})
        input_tokens = tokens.get("input_tokens", {}) if isinstance(tokens.get("input_tokens"), dict) else {}
        output_tokens = tokens.get("output_tokens", {}) if isinstance(tokens.get("output_tokens"), dict) else {}
        return texto, TokenUsage(
            prompt_tokens=int(input_tokens.get("input_tokens", 0) or input_tokens.get("tokens", 0)),
            completion_tokens=int(output_tokens.get("output_tokens", 0) or output_tokens.get("tokens", 0)),
        )

    def _gerar_sync(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_COHERE,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(client.post("/chat", json=self._montar_payload(request, model)))
                return ler_json(response)

        return self._parse(
            executar_com_retry(
                operacao,
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
        )

    async def _gerar_async(self, *, request: TextoParaTextoRequest, model: str) -> tuple[str, TokenUsage]:
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_COHERE,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(await client.post("/chat", json=self._montar_payload(request, model)))
                return ler_json(response)

        payload = await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return self._parse(payload)


def executar_lote_async(
    adapter: TextProviderAdapter,
    itens: Sequence[TextoParaTextoRequest],
    *,
    concorrencia: int,
) -> asyncio.Future[list[TextoParaTextoResultado]]:
    """Cria uma coroutine de execucao em lote com limite de concorrencia."""

    async def runner() -> list[TextoParaTextoResultado]:
        semaphore = asyncio.Semaphore(concorrencia)

        async def executar_item(item: TextoParaTextoRequest) -> TextoParaTextoResultado:
            async with semaphore:
                return await adapter.gerar_async(item)

        return await asyncio.gather(*(executar_item(item) for item in itens))

    return runner()
