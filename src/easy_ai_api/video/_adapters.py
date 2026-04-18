"""Infraestrutura compartilhada para capacidades de video."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .._core.config import (
    BASE_URL_GOOGLE,
    BASE_URL_HEDRA,
)
from .._core.downloads import baixar_bytes_async, baixar_bytes_sync, extrair_primeiro_url
from .._core.exceptions import (
    MissingCredentialError,
    ModeloNaoSuportadoError,
    ParametroIncompativelError,
    ParametroInvalidoError,
    RespostaInvalidaProviderError,
)
from .._core.files import salvar_bytes
from .._core.http import (
    criar_cliente_http,
    criar_cliente_http_async,
    excecao_e_retryable,
    ler_json,
    validar_resposta_http,
)
from .._core.media import codificar_base64, normalizar_entrada_binaria
from .._core.polling import aguardar_job, aguardar_job_async
from .._core.retry import executar_com_retry, executar_com_retry_async
from .._core.schemas import VideoJobRequest

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True, slots=True)
class VideoAdapter(ABC):
    provider: str
    default_model: str
    supported_models: frozenset[str]
    api_key: str | None
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
    def gerar(self, request: VideoJobRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    async def gerar_async(self, request: VideoJobRequest) -> None:
        raise NotImplementedError


def _salvar_video_de_payload(payload: dict[str, Any], caminho_saida: str) -> None:
    url = extrair_primeiro_url(
        payload,
        ("video", "url"),
        ("output", "url"),
        ("asset", "url"),
        ("download_url",),
        ("url",),
        ("result", "url"),
        ("result", "video_url"),
        ("data", "url"),
    )
    if url:
        salvar_bytes(caminho_saida, baixar_bytes_sync(url))
        return
    for chave in ("video_base64", "base64", "video"):
        valor = payload.get(chave)
        if isinstance(valor, str) and valor and not valor.startswith("http"):
            import base64

            salvar_bytes(caminho_saida, base64.b64decode(valor))
            return
    raise RespostaInvalidaProviderError("Nao foi possivel localizar o video final no payload do provider.")


async def _salvar_video_de_payload_async(payload: dict[str, Any], caminho_saida: str) -> None:
    url = extrair_primeiro_url(
        payload,
        ("video", "url"),
        ("output", "url"),
        ("asset", "url"),
        ("download_url",),
        ("url",),
        ("result", "url"),
        ("result", "video_url"),
        ("data", "url"),
    )
    if url:
        salvar_bytes(caminho_saida, await baixar_bytes_async(url))
        return
    for chave in ("video_base64", "base64", "video"):
        valor = payload.get(chave)
        if isinstance(valor, str) and valor and not valor.startswith("http"):
            import base64

            salvar_bytes(caminho_saida, base64.b64decode(valor))
            return
    raise RespostaInvalidaProviderError("Nao foi possivel localizar o video final no payload do provider.")


@dataclass(frozen=True, slots=True)
class GenericVideoJobAdapter(VideoAdapter):
    base_url: str
    create_path: str
    status_path: str
    auth_header_name: str = "Authorization"
    auth_prefix: str = "Bearer "
    prompt_field: str = "prompt"
    image_field: str = "image"
    audio_field: str = "audio"
    model_field: str = "model"
    image_requires_public_url: bool = False
    extra_headers: dict[str, str] | None = None

    def _headers(self) -> dict[str, str]:
        valor = f"{self.auth_prefix}{self.ensure_api_key()}".strip()
        headers = {self.auth_header_name: valor}
        if self.extra_headers:
            headers.update(self.extra_headers)
        return headers

    def _build_payload(self, request: VideoJobRequest, model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {self.model_field: model}
        if request.prompt:
            payload[self.prompt_field] = request.prompt
        if request.imagem is not None:
            if self.image_requires_public_url:
                if not isinstance(request.imagem, str) or not request.imagem.startswith(("http://", "https://")):
                    raise ParametroInvalidoError(
                        f"O provider {self.provider!r} exige URL publica para imagem de entrada."
                    )
                payload[self.image_field] = request.imagem
            else:
                imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
                payload[self.image_field] = codificar_base64(imagem.dados)
        if request.audio is not None:
            audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")
            payload[self.audio_field] = codificar_base64(audio.dados)
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def gerar(self, request: VideoJobRequest) -> None:
        model = self.resolve_model(request.modelo)

        with criar_cliente_http(
            base_url=self.base_url,
            headers=self._headers(),
            timeout_segundos=request.timeout_segundos,
        ) as client:
            created = executar_com_retry(
                lambda: ler_json(validar_resposta_http(client.post(self.create_path, json=self._build_payload(request, model)))),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
            job_id = created.get("id") or created.get("task_id") or created.get("video_id") or created.get("request_id")
            payload = created
            if isinstance(job_id, str):
                payload = aguardar_job(
                    lambda: ler_json(validar_resposta_http(client.get(self.status_path.format(id=job_id)))),
                    timeout_segundos=request.timeout_segundos,
                    extrair_estado=lambda item: str(item.get("status", item.get("state", ""))),
                    estados_sucesso={"completed", "succeeded", "success", "done", "ready"},
                    estados_falha={"failed", "error", "rejected", "cancelled"},
                )
        _salvar_video_de_payload(payload, str(request.caminho_saida))

    async def gerar_async(self, request: VideoJobRequest) -> None:
        model = self.resolve_model(request.modelo)

        async with criar_cliente_http_async(
            base_url=self.base_url,
            headers=self._headers(),
            timeout_segundos=request.timeout_segundos,
        ) as client:
            created = await executar_com_retry_async(
                lambda: _post_json_async(client, self.create_path, self._build_payload(request, model)),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
            job_id = created.get("id") or created.get("task_id") or created.get("video_id") or created.get("request_id")
            payload = created
            if isinstance(job_id, str):
                payload = await aguardar_job_async(
                    lambda: _get_json_async(client, self.status_path.format(id=job_id)),
                    timeout_segundos=request.timeout_segundos,
                    extrair_estado=lambda item: str(item.get("status", item.get("state", ""))),
                    estados_sucesso={"completed", "succeeded", "success", "done", "ready"},
                    estados_falha={"failed", "error", "rejected", "cancelled"},
                )
        await _salvar_video_de_payload_async(payload, str(request.caminho_saida))


async def _post_json_async(client: Any, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return ler_json(validar_resposta_http(await client.post(path, json=payload)))


async def _get_json_async(client: Any, path: str) -> dict[str, Any]:
    return ler_json(validar_resposta_http(await client.get(path)))


@dataclass(frozen=True, slots=True)
class GoogleVideoAdapter(VideoAdapter):
    def _build_payload(self, request: VideoJobRequest, model: str) -> dict[str, Any]:
        parts: list[dict[str, Any]] = []
        if request.prompt:
            parts.append({"text": request.prompt})
        if request.imagem is not None:
            imagem = normalizar_entrada_binaria(request.imagem, nome_campo="imagem")
            parts.append({"inline_data": {"mime_type": imagem.mime_type or "image/png", "data": codificar_base64(imagem.dados)}})
        if request.audio is not None:
            audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")
            parts.append({"inline_data": {"mime_type": audio.mime_type or "audio/mpeg", "data": codificar_base64(audio.dados)}})
        payload: dict[str, Any] = {"contents": [{"role": "user", "parts": parts}]}
        if request.parametros_provider:
            payload.update(request.parametros_provider)
        return payload

    def gerar(self, request: VideoJobRequest) -> None:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        with criar_cliente_http(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
            created = ler_json(
                validar_resposta_http(
                    client.post(f"/models/{model}:generateVideos", params={"key": api_key}, json=self._build_payload(request, model))
                )
            )
            operation_name = created.get("name")
            if not isinstance(operation_name, str):
                raise RespostaInvalidaProviderError("Google nao retornou operation `name` para video.")
            payload = aguardar_job(
                lambda: ler_json(validar_resposta_http(client.get(f"/{operation_name}", params={"key": api_key}))),
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: "completed" if item.get("done") else "running",
                estados_sucesso={"completed"},
                estados_falha={"error"},
            )
        _salvar_video_de_payload(payload.get("response", payload), str(request.caminho_saida))

    async def gerar_async(self, request: VideoJobRequest) -> None:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        async with criar_cliente_http_async(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
            created = ler_json(
                validar_resposta_http(
                    await client.post(f"/models/{model}:generateVideos", params={"key": api_key}, json=self._build_payload(request, model))
                )
            )
            operation_name = created.get("name")
            if not isinstance(operation_name, str):
                raise RespostaInvalidaProviderError("Google nao retornou operation `name` para video.")
            payload = await aguardar_job_async(
                lambda: _get_json_async(client, f"/{operation_name}?key={api_key}"),
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: "completed" if item.get("done") else "running",
                estados_sucesso={"completed"},
                estados_falha={"error"},
            )
        await _salvar_video_de_payload_async(payload.get("response", payload), str(request.caminho_saida))


@dataclass(frozen=True, slots=True)
class HedraVideoAdapter(VideoAdapter):
    """Adapter para os fluxos publicos de video da Hedra.

    Esta implementacao cobre tres superficies oficiais publicas:

    - `sem_audio`: texto-para-video e imagem-para-video via `POST /generations`
    - `com_audio`: avatar video com imagem obrigatoria e audio enviado ou TTS
      inline via `audio_generation`
    - `lipsync`: imagem + audio -> video falado

    A documentacao da Hedra expoe IDs de modelos em UUID e tambem recomenda
    descoberta adicional via `GET /models`. Para nao bloquear modelos novos sem
    obrigar mudancas locais, o adapter aceita:

    - os IDs oficiais conhecidos neste pacote;
    - qualquer UUID explicito informado em `modelo`.

    Parametros aceitos em `parametros_provider` variam por capacidade:

    - comuns: `aspect_ratio`, `resolution`, `duration_ms`
    - `sem_audio`: `imagem_final`
    - `com_audio` e `lipsync`: `visual_prompt`
    - `com_audio` sem `audio`: `voice_id` obrigatorio para TTS inline
    """

    capability: str = "sem_audio"
    default_image_model: str | None = None
    default_visual_prompt: str = "A person speaking to the camera"

    def _resolve_model_for_request(self, request: VideoJobRequest) -> str:
        if request.modelo:
            final_model = request.modelo.strip()
        elif self.capability == "sem_audio" and request.imagem is not None and self.default_image_model:
            final_model = self.default_image_model
        else:
            final_model = self.default_model
        if final_model in self.supported_models or _UUID_RE.fullmatch(final_model):
            return final_model
        raise ModeloNaoSuportadoError(
            f"Modelo nao suportado para provider={self.provider!r}: {final_model!r}"
        )

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.ensure_api_key()}

    def _validar_comuns(self, parametros: dict[str, object]) -> dict[str, object]:
        payload: dict[str, object] = {}
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
        if "duration_ms" in parametros:
            valor = parametros["duration_ms"]
            if not isinstance(valor, int) or valor <= 0:
                raise ParametroInvalidoError("`duration_ms` da Hedra precisa ser inteiro positivo.")
            payload["duration_ms"] = valor
        return payload

    def _criar_asset_sync(self, client: Any, *, tipo: str, nome: str, conteudo: Any) -> str:
        created = ler_json(
            validar_resposta_http(client.post("/assets", json={"name": nome, "type": tipo}))
        )
        asset_id = created.get("id")
        if not isinstance(asset_id, str):
            raise RespostaInvalidaProviderError("Hedra nao retornou `id` de asset.")
        binario = normalizar_entrada_binaria(conteudo, nome_campo=tipo)
        validar_resposta_http(
            client.post(
                f"/assets/{asset_id}/upload",
                files={"file": (nome, binario.dados, binario.mime_type or "application/octet-stream")},
            )
        )
        return asset_id

    async def _criar_asset_async(self, client: Any, *, tipo: str, nome: str, conteudo: Any) -> str:
        created = ler_json(
            validar_resposta_http(await client.post("/assets", json={"name": nome, "type": tipo}))
        )
        asset_id = created.get("id")
        if not isinstance(asset_id, str):
            raise RespostaInvalidaProviderError("Hedra nao retornou `id` de asset.")
        binario = normalizar_entrada_binaria(conteudo, nome_campo=tipo)
        validar_resposta_http(
            await client.post(
                f"/assets/{asset_id}/upload",
                files={"file": (nome, binario.dados, binario.mime_type or "application/octet-stream")},
            )
        )
        return asset_id

    def _build_payload(self, request: VideoJobRequest, model: str, client: Any) -> dict[str, Any]:
        parametros = dict(request.parametros_provider or {})
        payload: dict[str, Any] = {"type": "video", "ai_model_id": model}

        if self.capability == "sem_audio":
            if not request.prompt:
                raise ParametroInvalidoError("Hedra exige `prompt` para video sem audio.")
            permitidos = {"aspect_ratio", "resolution", "duration_ms", "imagem_final"}
            invalidos = sorted(set(parametros) - permitidos)
            if invalidos:
                raise ParametroInvalidoError(
                    "Parametros Hedra para video sem audio nao suportados: " + ", ".join(invalidos)
                )
            if request.audio is not None:
                raise ParametroIncompativelError("Hedra sem audio nao aceita `audio`.")
            if request.imagem is not None:
                payload["start_keyframe_id"] = self._criar_asset_sync(
                    client,
                    tipo="image",
                    nome="start-frame.png",
                    conteudo=request.imagem,
                )
            if "imagem_final" in parametros:
                payload["end_keyframe_id"] = self._criar_asset_sync(
                    client,
                    tipo="image",
                    nome="end-frame.png",
                    conteudo=parametros["imagem_final"],
                )
            payload["generated_video_inputs"] = {
                "text_prompt": request.prompt,
                **self._validar_comuns(parametros),
            }
            return payload

        if request.imagem is None:
            raise ParametroInvalidoError("Hedra exige `imagem` para video com audio e lipsync.")
        payload["start_keyframe_id"] = self._criar_asset_sync(
            client,
            tipo="image",
            nome="portrait.png",
            conteudo=request.imagem,
        )
        if self.capability == "lipsync":
            if request.audio is None:
                raise ParametroInvalidoError("Hedra lipsync exige `audio`.")
            permitidos = {"aspect_ratio", "resolution", "duration_ms", "visual_prompt"}
            invalidos = sorted(set(parametros) - permitidos)
            if invalidos:
                raise ParametroInvalidoError(
                    "Parametros Hedra para lipsync nao suportados: " + ", ".join(invalidos)
                )
            payload["audio_id"] = self._criar_asset_sync(
                client,
                tipo="audio",
                nome="speech.mp3",
                conteudo=request.audio,
            )
            payload["generated_video_inputs"] = {
                "text_prompt": str(parametros.get("visual_prompt", self.default_visual_prompt)),
                **self._validar_comuns(parametros),
            }
            return payload

        permitidos = {"aspect_ratio", "resolution", "duration_ms", "visual_prompt", "voice_id"}
        invalidos = sorted(set(parametros) - permitidos)
        if invalidos:
            raise ParametroInvalidoError(
                "Parametros Hedra para video com audio nao suportados: " + ", ".join(invalidos)
            )
        payload["generated_video_inputs"] = {
            "text_prompt": str(parametros.get("visual_prompt", self.default_visual_prompt)),
            **self._validar_comuns(parametros),
        }
        if request.audio is not None:
            payload["audio_id"] = self._criar_asset_sync(
                client,
                tipo="audio",
                nome="speech.mp3",
                conteudo=request.audio,
            )
            return payload
        if not request.prompt:
            raise ParametroIncompativelError(
                "Hedra com audio exige `audio` ou, sem audio enviado, `prompt` + `voice_id`."
            )
        voice_id = parametros.get("voice_id")
        if not isinstance(voice_id, str) or not _UUID_RE.fullmatch(voice_id.strip()):
            raise ParametroIncompativelError(
                "Hedra com TTS inline exige `parametros_provider['voice_id']` com UUID valido."
            )
        payload["audio_generation"] = {
            "type": "text_to_speech",
            "voice_id": voice_id.strip(),
            "text": request.prompt,
        }
        return payload

    async def _build_payload_async(self, request: VideoJobRequest, model: str, client: Any) -> dict[str, Any]:
        parametros = dict(request.parametros_provider or {})
        payload: dict[str, Any] = {"type": "video", "ai_model_id": model}

        if self.capability == "sem_audio":
            if not request.prompt:
                raise ParametroInvalidoError("Hedra exige `prompt` para video sem audio.")
            permitidos = {"aspect_ratio", "resolution", "duration_ms", "imagem_final"}
            invalidos = sorted(set(parametros) - permitidos)
            if invalidos:
                raise ParametroInvalidoError(
                    "Parametros Hedra para video sem audio nao suportados: " + ", ".join(invalidos)
                )
            if request.audio is not None:
                raise ParametroIncompativelError("Hedra sem audio nao aceita `audio`.")
            if request.imagem is not None:
                payload["start_keyframe_id"] = await self._criar_asset_async(
                    client,
                    tipo="image",
                    nome="start-frame.png",
                    conteudo=request.imagem,
                )
            if "imagem_final" in parametros:
                payload["end_keyframe_id"] = await self._criar_asset_async(
                    client,
                    tipo="image",
                    nome="end-frame.png",
                    conteudo=parametros["imagem_final"],
                )
            payload["generated_video_inputs"] = {
                "text_prompt": request.prompt,
                **self._validar_comuns(parametros),
            }
            return payload

        if request.imagem is None:
            raise ParametroInvalidoError("Hedra exige `imagem` para video com audio e lipsync.")
        payload["start_keyframe_id"] = await self._criar_asset_async(
            client,
            tipo="image",
            nome="portrait.png",
            conteudo=request.imagem,
        )
        if self.capability == "lipsync":
            if request.audio is None:
                raise ParametroInvalidoError("Hedra lipsync exige `audio`.")
            permitidos = {"aspect_ratio", "resolution", "duration_ms", "visual_prompt"}
            invalidos = sorted(set(parametros) - permitidos)
            if invalidos:
                raise ParametroInvalidoError(
                    "Parametros Hedra para lipsync nao suportados: " + ", ".join(invalidos)
                )
            payload["audio_id"] = await self._criar_asset_async(
                client,
                tipo="audio",
                nome="speech.mp3",
                conteudo=request.audio,
            )
            payload["generated_video_inputs"] = {
                "text_prompt": str(parametros.get("visual_prompt", self.default_visual_prompt)),
                **self._validar_comuns(parametros),
            }
            return payload

        permitidos = {"aspect_ratio", "resolution", "duration_ms", "visual_prompt", "voice_id"}
        invalidos = sorted(set(parametros) - permitidos)
        if invalidos:
            raise ParametroInvalidoError(
                "Parametros Hedra para video com audio nao suportados: " + ", ".join(invalidos)
            )
        payload["generated_video_inputs"] = {
            "text_prompt": str(parametros.get("visual_prompt", self.default_visual_prompt)),
            **self._validar_comuns(parametros),
        }
        if request.audio is not None:
            payload["audio_id"] = await self._criar_asset_async(
                client,
                tipo="audio",
                nome="speech.mp3",
                conteudo=request.audio,
            )
            return payload
        if not request.prompt:
            raise ParametroIncompativelError(
                "Hedra com audio exige `audio` ou, sem audio enviado, `prompt` + `voice_id`."
            )
        voice_id = parametros.get("voice_id")
        if not isinstance(voice_id, str) or not _UUID_RE.fullmatch(voice_id.strip()):
            raise ParametroIncompativelError(
                "Hedra com TTS inline exige `parametros_provider['voice_id']` com UUID valido."
            )
        payload["audio_generation"] = {
            "type": "text_to_speech",
            "voice_id": voice_id.strip(),
            "text": request.prompt,
        }
        return payload

    def gerar(self, request: VideoJobRequest) -> None:
        api_key = self.ensure_api_key()
        model = self._resolve_model_for_request(request)
        with criar_cliente_http(
            base_url=BASE_URL_HEDRA,
            headers={"X-API-Key": api_key},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            created = executar_com_retry(
                lambda: ler_json(
                    validar_resposta_http(
                        client.post("/generations", json=self._build_payload(request, model, client))
                    )
                ),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
            generation_id = created.get("id")
            if not isinstance(generation_id, str):
                raise RespostaInvalidaProviderError("Hedra nao retornou `id` de geracao de video.")
            payload = aguardar_job(
                lambda: ler_json(
                    validar_resposta_http(client.get(f"/generations/{generation_id}/status"))
                ),
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"complete"},
                estados_falha={"failed", "error", "cancelled", "rejected"},
            )
        _salvar_video_de_payload(payload, str(request.caminho_saida))

    async def gerar_async(self, request: VideoJobRequest) -> None:
        api_key = self.ensure_api_key()
        model = self._resolve_model_for_request(request)
        async with criar_cliente_http_async(
            base_url=BASE_URL_HEDRA,
            headers={"X-API-Key": api_key},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            async def criar_job() -> dict[str, Any]:
                return ler_json(
                    validar_resposta_http(
                        await client.post(
                            "/generations",
                            json=await self._build_payload_async(request, model, client),
                        )
                    )
                )

            created = await executar_com_retry_async(
                criar_job,
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
            generation_id = created.get("id")
            if not isinstance(generation_id, str):
                raise RespostaInvalidaProviderError("Hedra nao retornou `id` de geracao de video.")
            payload = await aguardar_job_async(
                lambda: _get_json_async(client, f"/generations/{generation_id}/status"),
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"complete"},
                estados_falha={"failed", "error", "cancelled", "rejected"},
            )
        await _salvar_video_de_payload_async(payload, str(request.caminho_saida))
