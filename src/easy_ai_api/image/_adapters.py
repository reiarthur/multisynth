"""Infraestrutura compartilhada para capacidades de imagem.

Convenção de máscara:
    A biblioteca padroniza a máscara de entrada como PNG grayscale onde
    **pixels pretos (0) = regiões editáveis** e
    **pixels brancos (255) = regiões preservadas**.
    Cada adapter converte internamente para o formato exigido pelo seu provider.

Última atualização: 2026-04-17
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .._core.config import (
    BASE_URL_BFL,
    BASE_URL_GOOGLE,
    BASE_URL_HEDRA,
    BASE_URL_IDEOGRAM,
    BASE_URL_OPENAI,
    BASE_URL_STABILITY,
)
from .._core.downloads import baixar_bytes_async, baixar_bytes_sync, extrair_primeiro_url
from .._core.exceptions import (
    MissingCredentialError,
    ModeloNaoSuportadoError,
    ParametroIncompativelError,
    ParametroInvalidoError,
    RespostaInvalidaProviderError,
)
from .._core.http import (
    criar_cliente_http,
    criar_cliente_http_async,
    excecao_e_retryable,
    ler_json,
    validar_resposta_http,
)
from .._core.media import (
    codificar_base64,
    converter_mascara_para_rgba_openai,
    inverter_mascara,
    normalizar_entrada_binaria,
    validar_mascara_compativel,
)
from .._core.polling import aguardar_job, aguardar_job_async
from .._core.retry import executar_com_retry, executar_com_retry_async
from .._core.schemas import (
    ComporImagemRequest,
    EditarImagemRequest,
    TextoImagemParaImagemRequest,
    TextoParaImagemRequest,
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _extrair_base64_generico(payload: dict[str, Any]) -> str | None:
    data = payload.get("data")
    if isinstance(data, list) and data:
        item = data[0]
        if isinstance(item, dict):
            for chave in ("b64_json", "base64", "image_base64", "image"):
                if isinstance(item.get(chave), str):
                    return item[chave]
    for chave in ("b64_json", "base64", "image_base64", "image"):
        if isinstance(payload.get(chave), str):
            return payload[chave]
    outputs = payload.get("output")
    if isinstance(outputs, list) and outputs:
        item = outputs[0]
        if isinstance(item, dict):
            for chave in ("b64_json", "base64", "image"):
                if isinstance(item.get(chave), str):
                    return item[chave]
    return None


def _extrair_base64_ou_baixar(payload: dict[str, Any]) -> str:
    base64_dados = _extrair_base64_generico(payload)
    if base64_dados:
        return base64_dados
    url = extrair_primeiro_url(
        payload,
        ("data", "url"),
        ("data", "image_url"),
        ("result", "sample"),
        ("output", "url"),
        ("asset", "url"),
        ("download_url",),
        ("video", "url"),
        ("image", "url"),
    )
    if url:
        return codificar_base64(baixar_bytes_sync(url))
    raise RespostaInvalidaProviderError("Nao foi possivel extrair imagem final da resposta.")


async def _extrair_base64_ou_baixar_async(payload: dict[str, Any]) -> str:
    base64_dados = _extrair_base64_generico(payload)
    if base64_dados:
        return base64_dados
    url = extrair_primeiro_url(
        payload,
        ("data", "url"),
        ("data", "image_url"),
        ("result", "sample"),
        ("output", "url"),
        ("asset", "url"),
        ("download_url",),
        ("video", "url"),
        ("image", "url"),
    )
    if url:
        return codificar_base64(await baixar_bytes_async(url))
    raise RespostaInvalidaProviderError("Nao foi possivel extrair imagem final da resposta.")


@dataclass(frozen=True, slots=True)
class ImageAdapter(ABC):
    """Classe base para adapters de imagem com retorno publico em base64."""

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

    @abstractmethod
    def gerar(self, request: object) -> str:
        raise NotImplementedError

    @abstractmethod
    async def gerar_async(self, request: object) -> str:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class OpenAIImageAdapter(ImageAdapter):
    """Adapter para ``gpt-image-1`` em geracao e edicao."""

    capability: str = "text_to_image"

    def gerar(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_OPENAI,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                if self.capability == "text_to_image":
                    payload: dict[str, Any] = {
                        "model": model,
                        "prompt": request.prompt,
                        "response_format": "b64_json",
                        "n": 1,
                    }
                    if getattr(request, "largura", None) and getattr(request, "altura", None):
                        payload["size"] = f"{request.largura}x{request.altura}"
                    response = validar_resposta_http(client.post("/images/generations", json=payload))
                    return ler_json(response)
                imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                files = {"image": ("image.png", imagem.dados, imagem.mime_type or "image/png")}
                data: dict[str, Any] = {"model": model, "prompt": request.prompt, "response_format": "b64_json", "n": "1"}
                if isinstance(request, EditarImagemRequest) and request.mascara is not None:
                    mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
                    validar_mascara_compativel(imagem.dados, mascara.dados)
                    # OpenAI usa canal alpha: transparente (alpha=0) = editar, opaco = preservar.
                    files["mask"] = ("mask.png", converter_mascara_para_rgba_openai(mascara.dados), "image/png")
                response = validar_resposta_http(client.post("/images/edits", data=data, files=files))
                return ler_json(response)

        payload = executar_com_retry(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return _extrair_base64_ou_baixar(payload)

    async def gerar_async(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_OPENAI,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                if self.capability == "text_to_image":
                    payload: dict[str, Any] = {
                        "model": model,
                        "prompt": request.prompt,
                        "response_format": "b64_json",
                        "n": 1,
                    }
                    response = validar_resposta_http(await client.post("/images/generations", json=payload))
                    return ler_json(response)
                imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                files = {"image": ("image.png", imagem.dados, imagem.mime_type or "image/png")}
                data: dict[str, Any] = {"model": model, "prompt": request.prompt, "response_format": "b64_json", "n": "1"}
                if isinstance(request, EditarImagemRequest) and request.mascara is not None:
                    mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
                    validar_mascara_compativel(imagem.dados, mascara.dados)
                    # OpenAI usa canal alpha: transparente (alpha=0) = editar, opaco = preservar.
                    files["mask"] = ("mask.png", converter_mascara_para_rgba_openai(mascara.dados), "image/png")
                response = validar_resposta_http(await client.post("/images/edits", data=data, files=files))
                return ler_json(response)

        payload = await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return await _extrair_base64_ou_baixar_async(payload)


@dataclass(frozen=True, slots=True)
class GoogleImageAdapter(ImageAdapter):
    """Adapter para Gemini API / Imagen via API key simples."""

    capability: str = "text_to_image"

    def _montar_payload(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest | ComporImagemRequest) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [{"text": request.prompt}]
        if hasattr(request, "imagem"):
            imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
            parts.append(
                {
                    "inline_data": {
                        "mime_type": imagem.mime_type or "image/png",
                        "data": codificar_base64(imagem.dados),
                    }
                }
            )
        if isinstance(request, ComporImagemRequest):
            referencia = normalizar_entrada_binaria(request.imagem_referencia, nome_campo="imagem_referencia")
            parts.append(
                {
                    "inline_data": {
                        "mime_type": referencia.mime_type or "image/png",
                        "data": codificar_base64(referencia.dados),
                    }
                }
            )
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        if isinstance(request, EditarImagemRequest) and request.mascara is not None:
            mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
            payload["contents"][0]["parts"].append(
                {
                    "inline_data": {
                        "mime_type": mascara.mime_type or "image/png",
                        "data": codificar_base64(mascara.dados),
                    }
                }
            )
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def gerar(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
                response = validar_resposta_http(
                    client.post(f"/models/{model}:generateContent", params={"key": api_key}, json=self._montar_payload(request))
                )
                return ler_json(response)

        payload = executar_com_retry(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise RespostaInvalidaProviderError("Resposta Google sem `candidates`.")
        partes = candidates[0].get("content", {}).get("parts", [])
        for parte in partes:
            if isinstance(parte, dict):
                inline_data = parte.get("inline_data") or parte.get("inlineData")
                if isinstance(inline_data, dict) and isinstance(inline_data.get("data"), str):
                    return inline_data["data"]
        raise RespostaInvalidaProviderError("Resposta Google sem imagem inline.")

    async def gerar_async(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
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
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise RespostaInvalidaProviderError("Resposta Google sem `candidates`.")
        partes = candidates[0].get("content", {}).get("parts", [])
        for parte in partes:
            if isinstance(parte, dict):
                inline_data = parte.get("inline_data") or parte.get("inlineData")
                if isinstance(inline_data, dict) and isinstance(inline_data.get("data"), str):
                    return inline_data["data"]
        raise RespostaInvalidaProviderError("Resposta Google sem imagem inline.")


@dataclass(frozen=True, slots=True)
class BFLImageAdapter(ImageAdapter):
    """Adapter para Black Forest Labs / FLUX com jobs assincronos."""

    def _montar_payload(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest | ComporImagemRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": request.prompt}
        if hasattr(request, "imagem"):
            imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
            payload["image"] = codificar_base64(imagem.dados)
        if isinstance(request, ComporImagemRequest):
            referencia = normalizar_entrada_binaria(request.imagem_referencia, nome_campo="imagem_referencia")
            payload["image_prompt"] = codificar_base64(referencia.dados)
        if isinstance(request, EditarImagemRequest) and request.mascara is not None:
            mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
            # BFL espera branco=editar; inverte a convenção de entrada (preto=editar).
            payload["mask"] = codificar_base64(inverter_mascara(mascara.dados))
        if getattr(request, "seed", None) is not None:
            payload["seed"] = request.seed
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def _buscar_resultado_sync(self, *, api_key: str, request_id: str, timeout_segundos: float) -> dict[str, Any]:
        def buscar_estado() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_BFL,
                headers={"x-key": api_key},
                timeout_segundos=timeout_segundos,
            ) as client:
                response = validar_resposta_http(client.get("/get_result", params={"id": request_id}))
                return ler_json(response)

        return aguardar_job(
            buscar_estado,
            timeout_segundos=timeout_segundos,
            extrair_estado=lambda payload: str(payload.get("status", "unknown")),
            estados_sucesso={"Ready", "ready", "completed"},
            estados_falha={"Error", "Failed", "failed"},
        )

    async def _buscar_resultado_async(self, *, api_key: str, request_id: str, timeout_segundos: float) -> dict[str, Any]:
        async def buscar_estado() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_BFL,
                headers={"x-key": api_key},
                timeout_segundos=timeout_segundos,
            ) as client:
                response = validar_resposta_http(await client.get("/get_result", params={"id": request_id}))
                return ler_json(response)

        return await aguardar_job_async(
            buscar_estado,
            timeout_segundos=timeout_segundos,
            extrair_estado=lambda payload: str(payload.get("status", "unknown")),
            estados_sucesso={"Ready", "ready", "completed"},
            estados_falha={"Error", "Failed", "failed"},
        )

    def gerar(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_BFL,
                headers={"x-key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(client.post(f"/{model}", json=self._montar_payload(request)))
                return ler_json(response)

        payload = executar_com_retry(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        if isinstance(payload.get("id"), str):
            payload = self._buscar_resultado_sync(api_key=api_key, request_id=payload["id"], timeout_segundos=request.timeout_segundos)
        return _extrair_base64_ou_baixar(payload)

    async def gerar_async(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_BFL,
                headers={"x-key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(await client.post(f"/{model}", json=self._montar_payload(request)))
                return ler_json(response)

        payload = await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        if isinstance(payload.get("id"), str):
            payload = await self._buscar_resultado_async(
                api_key=api_key,
                request_id=payload["id"],
                timeout_segundos=request.timeout_segundos,
            )
        return await _extrair_base64_ou_baixar_async(payload)


@dataclass(frozen=True, slots=True)
class IdeogramImageAdapter(ImageAdapter):
    """Adapter para endpoints oficiais generate/remix/edit da Ideogram."""

    endpoint: str = "/generate"

    def gerar(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_IDEOGRAM,
                headers={"Api-Key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                data: dict[str, Any] = {"prompt": request.prompt, "model": model}
                files: dict[str, tuple[str, bytes, str]] = {}
                if hasattr(request, "imagem"):
                    imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                    files["image_file"] = ("image.png", imagem.dados, imagem.mime_type or "image/png")
                if isinstance(request, EditarImagemRequest) and request.mascara is not None:
                    mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
                    files["mask_file"] = ("mask.png", mascara.dados, mascara.mime_type or "image/png")
                response = validar_resposta_http(client.post(self.endpoint, data=data, files=files or None))
                return ler_json(response)

        payload = executar_com_retry(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return _extrair_base64_ou_baixar(payload)

    async def gerar_async(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_IDEOGRAM,
                headers={"Api-Key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                data: dict[str, Any] = {"prompt": request.prompt, "model": model}
                files: dict[str, tuple[str, bytes, str]] = {}
                if hasattr(request, "imagem"):
                    imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                    files["image_file"] = ("image.png", imagem.dados, imagem.mime_type or "image/png")
                if isinstance(request, EditarImagemRequest) and request.mascara is not None:
                    mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
                    files["mask_file"] = ("mask.png", mascara.dados, mascara.mime_type or "image/png")
                response = validar_resposta_http(await client.post(self.endpoint, data=data, files=files or None))
                return ler_json(response)

        payload = await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return await _extrair_base64_ou_baixar_async(payload)


@dataclass(frozen=True, slots=True)
class StabilityImageAdapter(ImageAdapter):
    """Adapter para a superficie atual ``stable-image`` da Stability AI."""

    endpoint: str = "/v2beta/stable-image/generate/core"
    mode: str = "generate"

    def gerar(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        def operacao() -> str:
            with criar_cliente_http(
                base_url=BASE_URL_STABILITY,
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                data: dict[str, Any] = {"prompt": request.prompt, "output_format": "png", "model": model}
                files: dict[str, tuple[str, bytes, str]] = {}
                if hasattr(request, "imagem"):
                    imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                    files["image"] = ("image.png", imagem.dados, imagem.mime_type or "image/png")
                if isinstance(request, EditarImagemRequest) and request.mascara is not None:
                    mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
                    # Stability espera branco=editar; inverte a convenção de entrada (preto=editar).
                    files["mask"] = ("mask.png", inverter_mascara(mascara.dados), "image/png")
                response = validar_resposta_http(client.post(self.endpoint, data=data, files=files or None))
                payload = ler_json(response)
                return _extrair_base64_ou_baixar(payload)

        return executar_com_retry(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )

    async def gerar_async(self, request: TextoParaImagemRequest | TextoImagemParaImagemRequest | EditarImagemRequest) -> str:
        model = self.resolve_model(getattr(request, "modelo", None))
        api_key = self.ensure_api_key()

        async def operacao() -> str:
            async with criar_cliente_http_async(
                base_url=BASE_URL_STABILITY,
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                data: dict[str, Any] = {"prompt": request.prompt, "output_format": "png", "model": model}
                files: dict[str, tuple[str, bytes, str]] = {}
                if hasattr(request, "imagem"):
                    imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                    files["image"] = ("image.png", imagem.dados, imagem.mime_type or "image/png")
                if isinstance(request, EditarImagemRequest) and request.mascara is not None:
                    mascara = normalizar_entrada_binaria(request.mascara, nome_campo="mascara")
                    # Stability espera branco=editar; inverte a convenção de entrada (preto=editar).
                    files["mask"] = ("mask.png", inverter_mascara(mascara.dados), "image/png")
                response = validar_resposta_http(await client.post(self.endpoint, data=data, files=files or None))
                payload = ler_json(response)
                return await _extrair_base64_ou_baixar_async(payload)

        return await executar_com_retry_async(
            operacao,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )


@dataclass(frozen=True, slots=True)
class HedraImageAdapter(ImageAdapter):
    """Adapter para geracao de imagem da Hedra via ``X-API-Key``.

    A documentacao publica atual da Hedra expoe geracao assíncrona de imagem
    pela rota ``POST /generations`` com ``type="image"`` e polling em
    ``GET /generations/{id}/status``. O provider trabalha com IDs de modelo
    UUID e com dimensoes abstratas (`aspect_ratio` e `resolution`) em vez de
    pixels arbitrarios. Por isso:

    - `modelo` aceita o ID oficial documentado ou qualquer UUID explicito
      informado pelo chamador quando ele já souber o model ID atual obtido por
      ``GET /models``.
    - `largura`, `altura` e `seed` nao sao normalizados para este provider,
      porque a superficie oficial nao usa esses campos.
    - `parametros_provider` aceita apenas campos oficialmente documentados:
      `aspect_ratio`, `resolution`, `batch_size` e `enhance_prompt`.
    """

    def resolve_model(self, model: str | None) -> str:
        final_model = (model or self.default_model).strip()
        if final_model in self.supported_models or _UUID_RE.fullmatch(final_model):
            return final_model
        raise ModeloNaoSuportadoError(
            f"Modelo nao suportado para provider={self.provider!r}: {final_model!r}"
        )

    def _montar_payload(self, request: TextoParaImagemRequest, model: str) -> dict[str, Any]:
        if request.largura is not None or request.altura is not None:
            raise ParametroIncompativelError(
                "Hedra usa `aspect_ratio` e `resolution` em `parametros_provider`; "
                "`largura`/`altura` nao sao suportadas por esta superficie."
            )
        if request.seed is not None:
            raise ParametroIncompativelError(
                "A documentacao publica atual da Hedra nao expoe `seed` para imagem."
            )

        payload: dict[str, Any] = {
            "type": "image",
            "text_prompt": request.prompt,
            "ai_model_id": model,
        }
        parametros = dict(request.parametros_provider or {})
        permitidos = {"aspect_ratio", "resolution", "batch_size", "enhance_prompt"}
        invalidos = sorted(set(parametros) - permitidos)
        if invalidos:
            raise ParametroInvalidoError(
                "Parametros Hedra para imagem nao suportados: " + ", ".join(invalidos)
            )
        if "aspect_ratio" in parametros:
            valor = parametros["aspect_ratio"]
            if not isinstance(valor, str) or not valor.strip():
                raise ParametroInvalidoError("`aspect_ratio` da Hedra precisa ser string nao vazia.")
            payload["aspect_ratio"] = valor.strip()
        if "resolution" in parametros:
            valor = parametros["resolution"]
            if not isinstance(valor, str) or not valor.strip():
                raise ParametroInvalidoError("`resolution` da Hedra precisa ser string nao vazia.")
            payload["resolution"] = valor.strip()
        if "batch_size" in parametros:
            valor = parametros["batch_size"]
            if not isinstance(valor, int) or not 1 <= valor <= 8:
                raise ParametroInvalidoError("`batch_size` da Hedra precisa ser inteiro entre 1 e 8.")
            payload["batch_size"] = valor
        if "enhance_prompt" in parametros:
            valor = parametros["enhance_prompt"]
            if not isinstance(valor, bool):
                raise ParametroInvalidoError("`enhance_prompt` da Hedra precisa ser booleano.")
            payload["enhance_prompt"] = valor
        return payload

    def gerar(self, request: TextoParaImagemRequest) -> str:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)

        def criar_job() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_HEDRA,
                headers={"X-API-Key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    client.post("/generations", json=self._montar_payload(request, model))
                )
                created = ler_json(response)
                generation_id = created.get("id")
                if not isinstance(generation_id, str):
                    raise RespostaInvalidaProviderError("Hedra nao retornou `id` de geracao de imagem.")
                return aguardar_job(
                    lambda: ler_json(
                        validar_resposta_http(client.get(f"/generations/{generation_id}/status"))
                    ),
                    timeout_segundos=request.timeout_segundos,
                    extrair_estado=lambda item: str(item.get("status", "")),
                    estados_sucesso={"complete"},
                    estados_falha={"failed", "error", "cancelled", "rejected"},
                )

        payload = executar_com_retry(
            criar_job,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return _extrair_base64_ou_baixar(payload)

    async def gerar_async(self, request: TextoParaImagemRequest) -> str:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)

        async def criar_job() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_HEDRA,
                headers={"X-API-Key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post("/generations", json=self._montar_payload(request, model))
                )
                created = ler_json(response)
                generation_id = created.get("id")
                if not isinstance(generation_id, str):
                    raise RespostaInvalidaProviderError("Hedra nao retornou `id` de geracao de imagem.")
                return await aguardar_job_async(
                    lambda: _get_status_hedra_async(client, generation_id),
                    timeout_segundos=request.timeout_segundos,
                    extrair_estado=lambda item: str(item.get("status", "")),
                    estados_sucesso={"complete"},
                    estados_falha={"failed", "error", "cancelled", "rejected"},
                )

        payload = await executar_com_retry_async(
            criar_job,
            max_tentativas=request.max_tentativas,
            deve_tentar_novamente=excecao_e_retryable,
        )
        return await _extrair_base64_ou_baixar_async(payload)


async def _get_status_hedra_async(client: Any, generation_id: str) -> dict[str, Any]:
    response = validar_resposta_http(await client.get(f"/generations/{generation_id}/status"))
    return ler_json(response)
