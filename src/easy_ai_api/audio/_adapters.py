"""Infraestrutura compartilhada para audio."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .._core.config import (
    BASE_URL_ASSEMBLYAI,
    BASE_URL_BEATOVEN,
    BASE_URL_CARTESIA,
    BASE_URL_DEEPGRAM,
    BASE_URL_ELEVENLABS,
    BASE_URL_GOOGLE,
    BASE_URL_HUME,
    BASE_URL_LOUDLY,
    BASE_URL_MURF,
    BASE_URL_REVAI,
    BASE_URL_SPEECHMATICS,
)
from .._core.downloads import baixar_bytes_async, baixar_bytes_sync, extrair_primeiro_url
from .._core.exceptions import (
    ConfiguracaoAmbienteError,
    JobFalhouError,
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
from .._core.media import codificar_base64, normalizar_entrada_binaria
from .._core.polling import aguardar_job, aguardar_job_async
from .._core.retry import executar_com_retry, executar_com_retry_async
from .._core.schemas import (
    AudioParaTextoRequest,
    AudioParaTextoResultado,
    PalavraTemporizada,
    TextoParaAudioRequest,
    TextoParaAudioResultado,
    TextoParaMusicaRequest,
    TrechoSpeaker,
)


def _decimal(valor: Any) -> Decimal:
    return Decimal(str(valor))


def _agrupar_trechos_por_speaker(palavras: list[PalavraTemporizada]) -> list[TrechoSpeaker]:
    grupos: list[TrechoSpeaker] = []
    atual_speaker: str | None = None
    atual_texto: list[str] = []
    inicio: Decimal | None = None
    fim: Decimal | None = None
    for palavra in palavras:
        if palavra.speaker is None:
            continue
        if atual_speaker != palavra.speaker:
            if atual_speaker is not None and inicio is not None and fim is not None:
                grupos.append(
                    TrechoSpeaker(
                        speaker=atual_speaker,
                        inicio_s=inicio,
                        fim_s=fim,
                        texto=" ".join(atual_texto).strip(),
                    )
                )
            atual_speaker = palavra.speaker
            atual_texto = [palavra.texto]
            inicio = palavra.inicio_s
            fim = palavra.fim_s
        else:
            atual_texto.append(palavra.texto)
            fim = palavra.fim_s
    if atual_speaker is not None and inicio is not None and fim is not None:
        grupos.append(
            TrechoSpeaker(
                speaker=atual_speaker,
                inicio_s=inicio,
                fim_s=fim,
                texto=" ".join(atual_texto).strip(),
            )
        )
    return grupos


def _resultado_transcricao(
    palavras: list[PalavraTemporizada],
    metadata: dict[str, object],
) -> AudioParaTextoResultado:
    texto = " ".join(palavra.texto for palavra in palavras).strip()
    return AudioParaTextoResultado(
        texto=texto,
        palavras=palavras,
        trechos_por_speaker=_agrupar_trechos_por_speaker(palavras),
        metadata=metadata,
    )


def _agrupar_chars_em_palavras(
    texto: str,
    inicio_chars: list[float],
    fim_chars: list[float],
) -> list[PalavraTemporizada]:
    palavras: list[PalavraTemporizada] = []
    buffer_chars: list[str] = []
    buffer_inicios: list[float] = []
    buffer_fins: list[float] = []
    indice = 0
    for posicao, caractere in enumerate(texto):
        inicio = inicio_chars[posicao]
        fim = fim_chars[posicao]
        if caractere.isspace():
            if buffer_chars:
                palavras.append(
                    PalavraTemporizada(
                        indice=indice,
                        texto="".join(buffer_chars),
                        inicio_s=_decimal(min(buffer_inicios)),
                        fim_s=_decimal(max(buffer_fins)),
                    )
                )
                indice += 1
                buffer_chars = []
                buffer_inicios = []
                buffer_fins = []
            continue
        buffer_chars.append(caractere)
        buffer_inicios.append(inicio)
        buffer_fins.append(fim)
    if buffer_chars:
        palavras.append(
            PalavraTemporizada(
                indice=indice,
                texto="".join(buffer_chars),
                inicio_s=_decimal(min(buffer_inicios)),
                fim_s=_decimal(max(buffer_fins)),
            )
        )
    return palavras


@dataclass(frozen=True, slots=True)
class SpeechToTextAdapter(ABC):
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
    def transcrever(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        raise NotImplementedError

    @abstractmethod
    async def transcrever_async(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class TextToSpeechAdapter(ABC):
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
    def sintetizar(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        raise NotImplementedError

    @abstractmethod
    async def sintetizar_async(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class MusicAdapter(ABC):
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
    def gerar(self, request: TextoParaMusicaRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    async def gerar_async(self, request: TextoParaMusicaRequest) -> str:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class DeepgramAdapter(SpeechToTextAdapter):
    def _parse(self, payload: dict[str, Any], model: str) -> AudioParaTextoResultado:
        alternatives = (
            payload.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])
        )
        if not alternatives:
            raise RespostaInvalidaProviderError("Resposta Deepgram sem `alternatives`.")
        words = alternatives[0].get("words", [])
        palavras = [
            PalavraTemporizada(
                indice=indice,
                texto=str(item.get("word", "")).strip(),
                inicio_s=_decimal(item.get("start", 0)),
                fim_s=_decimal(item.get("end", 0)),
                speaker=str(item.get("speaker")) if item.get("speaker") is not None else None,
                confianca=_decimal(item["confidence"]) if item.get("confidence") is not None else None,
            )
            for indice, item in enumerate(words)
            if isinstance(item, dict) and str(item.get("word", "")).strip()
        ]
        return _resultado_transcricao(
            palavras,
            {"provider": "deepgram", "model": model, "request_id": payload.get("request_id")},
        )

    def transcrever(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_DEEPGRAM,
                headers={"Authorization": f"Token {api_key}", "Content-Type": audio.mime_type or "application/octet-stream"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    client.post(
                        "/listen",
                        params={
                            "model": model,
                            "diarize": str(request.diarizacao).lower(),
                            "smart_format": "true",
                            "utterances": "true",
                            "punctuate": "true",
                        },
                        content=audio.dados,
                    )
                )
                return ler_json(response)

        return self._parse(
            executar_com_retry(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
        )

    async def transcrever_async(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_DEEPGRAM,
                headers={"Authorization": f"Token {api_key}", "Content-Type": audio.mime_type or "application/octet-stream"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post(
                        "/listen",
                        params={
                            "model": model,
                            "diarize": str(request.diarizacao).lower(),
                            "smart_format": "true",
                            "utterances": "true",
                            "punctuate": "true",
                        },
                        content=audio.dados,
                    )
                )
                return ler_json(response)

        return self._parse(
            await executar_com_retry_async(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
        )


@dataclass(frozen=True, slots=True)
class AssemblyAIAdapter(SpeechToTextAdapter):
    def _parse(self, payload: dict[str, Any], model: str) -> AudioParaTextoResultado:
        words = payload.get("words", [])
        palavras = [
            PalavraTemporizada(
                indice=indice,
                texto=str(item.get("text", "")).strip(),
                inicio_s=_decimal(Decimal(item.get("start", 0)) / Decimal("1000")),
                fim_s=_decimal(Decimal(item.get("end", 0)) / Decimal("1000")),
                speaker=str(item.get("speaker")) if item.get("speaker") is not None else None,
                confianca=_decimal(item["confidence"]) if item.get("confidence") is not None else None,
            )
            for indice, item in enumerate(words)
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ]
        return _resultado_transcricao(
            palavras,
            {"provider": "assemblyai", "model": model, "id": payload.get("id")},
        )

    def _upload_sync(self, *, api_key: str, audio: bytes, timeout_segundos: float) -> str:
        with criar_cliente_http(
            base_url=BASE_URL_ASSEMBLYAI,
            headers={"Authorization": api_key, "Content-Type": "application/octet-stream"},
            timeout_segundos=timeout_segundos,
        ) as client:
            response = validar_resposta_http(client.post("/upload", content=audio))
            payload = ler_json(response)
            url = payload.get("upload_url")
            if not isinstance(url, str):
                raise RespostaInvalidaProviderError("Upload AssemblyAI sem `upload_url`.")
            return url

    async def _upload_async(self, *, api_key: str, audio: bytes, timeout_segundos: float) -> str:
        async with criar_cliente_http_async(
            base_url=BASE_URL_ASSEMBLYAI,
            headers={"Authorization": api_key, "Content-Type": "application/octet-stream"},
            timeout_segundos=timeout_segundos,
        ) as client:
            response = validar_resposta_http(await client.post("/upload", content=audio))
            payload = ler_json(response)
            url = payload.get("upload_url")
            if not isinstance(url, str):
                raise RespostaInvalidaProviderError("Upload AssemblyAI sem `upload_url`.")
            return url

    def transcrever(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")
        upload_url = self._upload_sync(api_key=api_key, audio=audio.dados, timeout_segundos=request.timeout_segundos)

        with criar_cliente_http(
            base_url=BASE_URL_ASSEMBLYAI,
            headers={"Authorization": api_key},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            response = validar_resposta_http(
                client.post(
                    "/transcript",
                    json={
                        "audio_url": upload_url,
                        "speech_model": model,
                        "speaker_labels": request.diarizacao,
                        "word_boost": [],
                    },
                )
            )
            payload = ler_json(response)
            transcript_id = payload.get("id")
            if not isinstance(transcript_id, str):
                raise RespostaInvalidaProviderError("AssemblyAI nao retornou id de transcricao.")

            def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(client.get(f"/transcript/{transcript_id}"))
                return ler_json(status_response)

            final_payload = aguardar_job(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"completed"},
                estados_falha={"error"},
            )
        return self._parse(final_payload, model)

    async def transcrever_async(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")
        upload_url = await self._upload_async(api_key=api_key, audio=audio.dados, timeout_segundos=request.timeout_segundos)

        async with criar_cliente_http_async(
            base_url=BASE_URL_ASSEMBLYAI,
            headers={"Authorization": api_key},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            response = validar_resposta_http(
                await client.post(
                    "/transcript",
                    json={
                        "audio_url": upload_url,
                        "speech_model": model,
                        "speaker_labels": request.diarizacao,
                        "word_boost": [],
                    },
                )
            )
            payload = ler_json(response)
            transcript_id = payload.get("id")
            if not isinstance(transcript_id, str):
                raise RespostaInvalidaProviderError("AssemblyAI nao retornou id de transcricao.")

            async def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(await client.get(f"/transcript/{transcript_id}"))
                return ler_json(status_response)

            final_payload = await aguardar_job_async(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"completed"},
                estados_falha={"error"},
            )
        return self._parse(final_payload, model)


@dataclass(frozen=True, slots=True)
class SpeechmaticsAdapter(SpeechToTextAdapter):
    def _parse(self, payload: dict[str, Any], model: str) -> AudioParaTextoResultado:
        results = payload.get("results", [])
        palavras: list[PalavraTemporizada] = []
        indice = 0
        for item in results:
            if not isinstance(item, dict) or item.get("type") != "word":
                continue
            alternatives = item.get("alternatives", [])
            palavra = alternatives[0] if isinstance(alternatives, list) and alternatives else {}
            texto = str(palavra.get("content", "")).strip()
            if not texto:
                continue
            palavras.append(
                PalavraTemporizada(
                    indice=indice,
                    texto=texto,
                    inicio_s=_decimal(item.get("start_time", 0)),
                    fim_s=_decimal(item.get("end_time", 0)),
                    speaker=str(item.get("speaker")) if item.get("speaker") is not None else None,
                    confianca=_decimal(palavra["confidence"]) if palavra.get("confidence") is not None else None,
                )
            )
            indice += 1
        return _resultado_transcricao(
            palavras,
            {"provider": "speechmatics", "model": model, "job_id": payload.get("job", {}).get("id")},
        )

    def transcrever(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")

        with criar_cliente_http(
            base_url=BASE_URL_SPEECHMATICS,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            config = {
                "type": "transcription",
                "transcription_config": {
                    "language": request.idioma or "pt",
                    "operating_point": model,
                    "diarization": "speaker" if request.diarizacao else None,
                    "enable_partials": False,
                },
            }
            response = validar_resposta_http(
                client.post(
                    "/jobs",
                    files={
                        "data_file": ("audio.bin", audio.dados, audio.mime_type or "application/octet-stream"),
                        "config": (None, json.dumps(config), "application/json"),
                    },
                )
            )
            created = ler_json(response)
            job_id = created.get("id")
            if not isinstance(job_id, str):
                raise RespostaInvalidaProviderError("Speechmatics nao retornou `id` de job.")

            def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(client.get(f"/jobs/{job_id}"))
                return ler_json(status_response)

            aguardar_job(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("job", {}).get("status", item.get("status", ""))),
                estados_sucesso={"done", "completed"},
                estados_falha={"failed", "rejected", "error"},
            )
            transcript_response = validar_resposta_http(client.get(f"/jobs/{job_id}/transcript", params={"format": "json-v2"}))
            payload = ler_json(transcript_response)
        return self._parse(payload, model)

    async def transcrever_async(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")

        async with criar_cliente_http_async(
            base_url=BASE_URL_SPEECHMATICS,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            config = {
                "type": "transcription",
                "transcription_config": {
                    "language": request.idioma or "pt",
                    "operating_point": model,
                    "diarization": "speaker" if request.diarizacao else None,
                    "enable_partials": False,
                },
            }
            response = validar_resposta_http(
                await client.post(
                    "/jobs",
                    files={
                        "data_file": ("audio.bin", audio.dados, audio.mime_type or "application/octet-stream"),
                        "config": (None, json.dumps(config), "application/json"),
                    },
                )
            )
            created = ler_json(response)
            job_id = created.get("id")
            if not isinstance(job_id, str):
                raise RespostaInvalidaProviderError("Speechmatics nao retornou `id` de job.")

            async def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(await client.get(f"/jobs/{job_id}"))
                return ler_json(status_response)

            await aguardar_job_async(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("job", {}).get("status", item.get("status", ""))),
                estados_sucesso={"done", "completed"},
                estados_falha={"failed", "rejected", "error"},
            )
            transcript_response = validar_resposta_http(await client.get(f"/jobs/{job_id}/transcript", params={"format": "json-v2"}))
            payload = ler_json(transcript_response)
        return self._parse(payload, model)


@dataclass(frozen=True, slots=True)
class RevAIAdapter(SpeechToTextAdapter):
    def _parse(self, payload: list[dict[str, Any]], model: str, job_id: str) -> AudioParaTextoResultado:
        palavras: list[PalavraTemporizada] = []
        indice = 0
        for monologue in payload:
            if not isinstance(monologue, dict):
                continue
            speaker = f"speaker_{monologue.get('speaker', 0)}" if monologue.get("speaker") is not None else None
            for element in monologue.get("elements", []):
                if not isinstance(element, dict) or element.get("type") != "text":
                    continue
                texto = str(element.get("value", "")).strip()
                if not texto:
                    continue
                palavras.append(
                    PalavraTemporizada(
                        indice=indice,
                        texto=texto,
                        inicio_s=_decimal(element.get("ts", 0)),
                        fim_s=_decimal(element.get("end_ts", 0)),
                        speaker=speaker,
                        confianca=_decimal(element["confidence"]) if element.get("confidence") is not None else None,
                    )
                )
                indice += 1
        return _resultado_transcricao(palavras, {"provider": "revai", "model": model, "job_id": job_id})

    def transcrever(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")

        with criar_cliente_http(
            base_url=BASE_URL_REVAI,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            response = validar_resposta_http(
                client.post(
                    "/jobs",
                    files={"media": ("audio.bin", audio.dados, audio.mime_type or "application/octet-stream")},
                    data={"metadata": "easy-ai-api", "skip_diarization": str(not request.diarizacao).lower()},
                )
            )
            created = ler_json(response)
            job_id = created.get("id")
            if not isinstance(job_id, str):
                raise RespostaInvalidaProviderError("Rev AI nao retornou id de job.")

            def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(client.get(f"/jobs/{job_id}"))
                return ler_json(status_response)

            aguardar_job(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"transcribed"},
                estados_falha={"failed"},
            )
            transcript_response = validar_resposta_http(
                client.get(f"/jobs/{job_id}/transcript", headers={"Accept": "application/vnd.rev.transcript.v1.0+json"})
            )
            payload = transcript_response.json()
            if not isinstance(payload, list):
                raise RespostaInvalidaProviderError("Transcript JSON da Rev AI em formato inesperado.")
        return self._parse(payload, model, job_id)

    async def transcrever_async(self, request: AudioParaTextoRequest) -> AudioParaTextoResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        audio = normalizar_entrada_binaria(request.audio, nome_campo="audio")

        async with criar_cliente_http_async(
            base_url=BASE_URL_REVAI,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            response = validar_resposta_http(
                await client.post(
                    "/jobs",
                    files={"media": ("audio.bin", audio.dados, audio.mime_type or "application/octet-stream")},
                    data={"metadata": "easy-ai-api", "skip_diarization": str(not request.diarizacao).lower()},
                )
            )
            created = ler_json(response)
            job_id = created.get("id")
            if not isinstance(job_id, str):
                raise RespostaInvalidaProviderError("Rev AI nao retornou id de job.")

            async def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(await client.get(f"/jobs/{job_id}"))
                return ler_json(status_response)

            await aguardar_job_async(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"transcribed"},
                estados_falha={"failed"},
            )
            transcript_response = validar_resposta_http(
                await client.get(f"/jobs/{job_id}/transcript", headers={"Accept": "application/vnd.rev.transcript.v1.0+json"})
            )
            payload = transcript_response.json()
            if not isinstance(payload, list):
                raise RespostaInvalidaProviderError("Transcript JSON da Rev AI em formato inesperado.")
        return self._parse(payload, model, job_id)


@dataclass(frozen=True, slots=True)
class CartesiaAdapter(TextToSpeechAdapter):
    def _parse(self, payload: dict[str, Any], model: str, voice: str | None) -> TextoParaAudioResultado:
        audio_b64 = payload.get("audio") or payload.get("audio_base64")
        timestamps = payload.get("word_timestamps") or payload.get("timestamps", {})
        words = timestamps.get("words", []) if isinstance(timestamps, dict) else payload.get("words", [])
        if not isinstance(audio_b64, str):
            raise RespostaInvalidaProviderError("Cartesia nao retornou audio em base64.")
        palavras = [
            PalavraTemporizada(
                indice=indice,
                texto=str(item.get("word", "")).strip(),
                inicio_s=_decimal(item.get("start", 0)),
                fim_s=_decimal(item.get("end", 0)),
            )
            for indice, item in enumerate(words)
            if isinstance(item, dict) and str(item.get("word", "")).strip()
        ]
        return TextoParaAudioResultado(audio_base64=audio_b64, palavras=palavras, metadata={"provider": "cartesia", "model": model, "voice": voice})

    def sintetizar(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "default"

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_CARTESIA,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    client.post(
                        "/tts/bytes",
                        json={
                            "model_id": model,
                            "transcript": request.texto,
                            "voice": {"mode": "id", "id": voice},
                            "output_format": {"container": "wav", "encoding": "pcm_f32le", "sample_rate": 44100},
                            "timestamps": True,
                        },
                    )
                )
                return ler_json(response)

        return self._parse(
            executar_com_retry(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
            voice,
        )

    async def sintetizar_async(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "default"

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_CARTESIA,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post(
                        "/tts/bytes",
                        json={
                            "model_id": model,
                            "transcript": request.texto,
                            "voice": {"mode": "id", "id": voice},
                            "output_format": {"container": "wav", "encoding": "pcm_f32le", "sample_rate": 44100},
                            "timestamps": True,
                        },
                    )
                )
                return ler_json(response)

        return self._parse(
            await executar_com_retry_async(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
            voice,
        )


@dataclass(frozen=True, slots=True)
class AzureSpeechAdapter(TextToSpeechAdapter):
    region: str | None = None

    def sintetizar(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        if not api_key or not self.region:
            raise MissingCredentialError(
                provider=self.provider,
                env_vars=self.credential_env_vars or ("AZURE_SPEECH_API_KEY", "AZURE_SPEECH_REGION"),
            )
        model = self.resolve_model(request.modelo)
        try:
            import azure.cognitiveservices.speech as speechsdk  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depende do ambiente do usuario.
            raise ConfiguracaoAmbienteError(
                "Para usar Azure Speech com WordBoundary, instale o SDK oficial `azure-cognitiveservices-speech`."
            ) from exc
        speech_config = speechsdk.SpeechConfig(subscription=api_key, region=self.region)
        speech_config.speech_synthesis_voice_name = request.voz or "pt-BR-AntonioNeural"
        speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_SynthEnableWordBoundary, "true")
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        palavras: list[PalavraTemporizada] = []

        def on_boundary(evt: Any) -> None:
            duracao = Decimal(str(getattr(evt, "duration", 0))) / Decimal("10000000")
            inicio = Decimal(str(getattr(evt, "audio_offset", 0))) / Decimal("10000000")
            texto = str(getattr(evt, "text", "")).strip()
            if texto:
                palavras.append(
                    PalavraTemporizada(
                        indice=len(palavras),
                        texto=texto,
                        inicio_s=inicio,
                        fim_s=inicio + duracao,
                    )
                )

        synthesizer.synthesis_word_boundary.connect(on_boundary)
        result = synthesizer.speak_text_async(request.texto).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise JobFalhouError(f"Falha no Azure Speech: {result.reason}")
        return TextoParaAudioResultado(
            audio_base64=codificar_base64(bytes(result.audio_data)),
            palavras=palavras,
            metadata={"provider": "azure", "model": model, "voice": request.voz or "pt-BR-AntonioNeural"},
        )

    async def sintetizar_async(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        # O SDK do Azure e bloqueante; executamos em thread para manter interface async.
        import asyncio

        return await asyncio.to_thread(self.sintetizar, request)


@dataclass(frozen=True, slots=True)
class HumeAdapter(TextToSpeechAdapter):
    def _parse(self, payload: dict[str, Any], model: str, voice: str | None) -> TextoParaAudioResultado:
        audio_b64 = payload.get("audio") or payload.get("audio_base64")
        words = payload.get("word_timestamps") or payload.get("timestamps", [])
        if not isinstance(audio_b64, str):
            url = extrair_primeiro_url(payload, ("audio", "url"), ("output", "url"))
            if not url:
                raise RespostaInvalidaProviderError("Hume nao retornou audio utilizavel.")
            audio_b64 = codificar_base64(baixar_bytes_sync(url))
        palavras = [
            PalavraTemporizada(
                indice=indice,
                texto=str(item.get("text", "")).strip(),
                inicio_s=_decimal(item.get("start", 0)),
                fim_s=_decimal(item.get("end", 0)),
            )
            for indice, item in enumerate(words)
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ]
        return TextoParaAudioResultado(audio_base64=audio_b64, palavras=palavras, metadata={"provider": "hume", "model": model, "voice": voice})

    def sintetizar(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "default"

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_HUME,
                headers={"X-Hume-Api-Key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    client.post(
                        "/tts",
                        json={"model": model, "text": request.texto, "voice": voice, "timestamps": True},
                    )
                )
                return ler_json(response)

        return self._parse(
            executar_com_retry(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
            voice,
        )

    async def sintetizar_async(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "default"

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_HUME,
                headers={"X-Hume-Api-Key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post(
                        "/tts",
                        json={"model": model, "text": request.texto, "voice": voice, "timestamps": True},
                    )
                )
                return ler_json(response)

        return self._parse(
            await executar_com_retry_async(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
            voice,
        )


@dataclass(frozen=True, slots=True)
class ElevenLabsAdapter(TextToSpeechAdapter):
    def _parse(self, payload: dict[str, Any], voice: str, model: str, texto: str) -> TextoParaAudioResultado:
        audio_b64 = payload.get("audio_base64")
        alignment = payload.get("alignment") or payload.get("normalized_alignment") or {}
        starts = alignment.get("character_start_times_seconds", [])
        ends = alignment.get("character_end_times_seconds", [])
        if not isinstance(audio_b64, str):
            raise RespostaInvalidaProviderError("ElevenLabs nao retornou `audio_base64`.")
        if not (isinstance(starts, list) and isinstance(ends, list) and len(starts) == len(ends) == len(texto)):
            raise RespostaInvalidaProviderError(
                "ElevenLabs nao retornou alinhamento por caractere suficiente para agregar por palavra."
            )
        return TextoParaAudioResultado(
            audio_base64=audio_b64,
            palavras=_agrupar_chars_em_palavras(texto, [float(v) for v in starts], [float(v) for v in ends]),
            metadata={"provider": "elevenlabs", "model": model, "voice": voice},
        )

    def sintetizar(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "JBFqnCBsd6RMkjVDRZzb"

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_ELEVENLABS,
                headers={"xi-api-key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    client.post(
                        f"/text-to-speech/{voice}/with-timestamps",
                        json={"text": request.texto, "model_id": model},
                    )
                )
                return ler_json(response)

        return self._parse(
            executar_com_retry(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            voice,
            model,
            request.texto,
        )

    async def sintetizar_async(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "JBFqnCBsd6RMkjVDRZzb"

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_ELEVENLABS,
                headers={"xi-api-key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post(
                        f"/text-to-speech/{voice}/with-timestamps",
                        json={"text": request.texto, "model_id": model},
                    )
                )
                return ler_json(response)

        return self._parse(
            await executar_com_retry_async(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            voice,
            model,
            request.texto,
        )


@dataclass(frozen=True, slots=True)
class MurfAdapter(TextToSpeechAdapter):
    def _parse(self, payload: dict[str, Any], model: str, voice: str | None) -> TextoParaAudioResultado:
        audio_b64 = payload.get("audio_base64")
        if not isinstance(audio_b64, str):
            url = extrair_primeiro_url(payload, ("audio", "url"), ("audio_url",), ("url",))
            if not url:
                raise RespostaInvalidaProviderError("Murf nao retornou audio utilizavel.")
            audio_b64 = codificar_base64(baixar_bytes_sync(url))
        timings = payload.get("word_timestamps") or payload.get("timestamps") or payload.get("words")
        if not isinstance(timings, list):
            raise RespostaInvalidaProviderError(
                "A resposta atual da Murf nao trouxe timestamps por palavra suficientes para o contrato publico."
            )
        palavras = [
            PalavraTemporizada(
                indice=indice,
                texto=str(item.get("text", "") or item.get("word", "")).strip(),
                inicio_s=_decimal(item.get("start", 0)),
                fim_s=_decimal(item.get("end", 0)),
            )
            for indice, item in enumerate(timings)
            if isinstance(item, dict) and str(item.get("text", "") or item.get("word", "")).strip()
        ]
        return TextoParaAudioResultado(audio_base64=audio_b64, palavras=palavras, metadata={"provider": "murf", "model": model, "voice": voice})

    def sintetizar(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "pt-BR-Helena"

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(
                base_url=BASE_URL_MURF,
                headers={"api-key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    client.post("/speech/generate", json={"text": request.texto, "voiceId": voice, "model": model, "timestamps": True})
                )
                return ler_json(response)

        return self._parse(
            executar_com_retry(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
            voice,
        )

    async def sintetizar_async(self, request: TextoParaAudioRequest) -> TextoParaAudioResultado:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        voice = request.voz or "pt-BR-Helena"

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(
                base_url=BASE_URL_MURF,
                headers={"api-key": api_key},
                timeout_segundos=request.timeout_segundos,
            ) as client:
                response = validar_resposta_http(
                    await client.post("/speech/generate", json={"text": request.texto, "voiceId": voice, "model": model, "timestamps": True})
                )
                return ler_json(response)

        return self._parse(
            await executar_com_retry_async(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable),
            model,
            voice,
        )


@dataclass(frozen=True, slots=True)
class GoogleMusicAdapter(MusicAdapter):
    def gerar(self, request: TextoParaMusicaRequest) -> str:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)

        def operacao() -> dict[str, Any]:
            with criar_cliente_http(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
                response = validar_resposta_http(
                    client.post(
                        f"/models/{model}:generateContent",
                        params={"key": api_key},
                        json={"contents": [{"role": "user", "parts": [{"text": request.prompt}]}], "generationConfig": {"responseModalities": ["AUDIO"]}},
                    )
                )
                return ler_json(response)

        payload = executar_com_retry(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable)
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise RespostaInvalidaProviderError("Resposta Google sem `candidates` para musica.")
        for parte in candidates[0].get("content", {}).get("parts", []):
            inline_data = parte.get("inline_data") or parte.get("inlineData")
            if isinstance(inline_data, dict) and isinstance(inline_data.get("data"), str):
                return inline_data["data"]
        raise RespostaInvalidaProviderError("Resposta Google sem audio inline.")

    async def gerar_async(self, request: TextoParaMusicaRequest) -> str:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)

        async def operacao() -> dict[str, Any]:
            async with criar_cliente_http_async(base_url=BASE_URL_GOOGLE, timeout_segundos=request.timeout_segundos) as client:
                response = validar_resposta_http(
                    await client.post(
                        f"/models/{model}:generateContent",
                        params={"key": api_key},
                        json={"contents": [{"role": "user", "parts": [{"text": request.prompt}]}], "generationConfig": {"responseModalities": ["AUDIO"]}},
                    )
                )
                return ler_json(response)

        payload = await executar_com_retry_async(operacao, max_tentativas=request.max_tentativas, deve_tentar_novamente=excecao_e_retryable)
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise RespostaInvalidaProviderError("Resposta Google sem `candidates` para musica.")
        for parte in candidates[0].get("content", {}).get("parts", []):
            inline_data = parte.get("inline_data") or parte.get("inlineData")
            if isinstance(inline_data, dict) and isinstance(inline_data.get("data"), str):
                return inline_data["data"]
        raise RespostaInvalidaProviderError("Resposta Google sem audio inline.")


@dataclass(frozen=True, slots=True)
class AsyncMusicJobAdapter(MusicAdapter):
    base_url: str
    create_path: str
    status_path: str
    auth_header_name: str = "Authorization"
    auth_prefix: str = "Bearer "

    def _headers(self) -> dict[str, str]:
        return {self.auth_header_name: f"{self.auth_prefix}{self.ensure_api_key()}".strip()}

    def _extract_audio(self, payload: dict[str, Any]) -> str:
        audio_b64 = payload.get("audio_base64")
        if isinstance(audio_b64, str):
            return audio_b64
        url = extrair_primeiro_url(
            payload,
            ("audio", "url"),
            ("audio_url",),
            ("url",),
            ("output", "url"),
            ("meta", "track_url"),
            ("music_file_path",),
        )
        if not url:
            raise RespostaInvalidaProviderError("Provider de musica nao retornou audio final.")
        return codificar_base64(baixar_bytes_sync(url))

    async def _extract_audio_async(self, payload: dict[str, Any]) -> str:
        audio_b64 = payload.get("audio_base64")
        if isinstance(audio_b64, str):
            return audio_b64
        url = extrair_primeiro_url(
            payload,
            ("audio", "url"),
            ("audio_url",),
            ("url",),
            ("output", "url"),
            ("meta", "track_url"),
            ("music_file_path",),
        )
        if not url:
            raise RespostaInvalidaProviderError("Provider de musica nao retornou audio final.")
        return codificar_base64(await baixar_bytes_async(url))

    def gerar(self, request: TextoParaMusicaRequest) -> str:
        model = self.resolve_model(request.modelo)
        with criar_cliente_http(base_url=self.base_url, headers=self._headers(), timeout_segundos=request.timeout_segundos) as client:
            response = validar_resposta_http(client.post(self.create_path, json={"prompt": request.prompt, "model": model}))
            created = ler_json(response)
            job_id = created.get("id") or created.get("request_id")
            if not isinstance(job_id, str):
                return self._extract_audio(created)

            def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(client.get(self.status_path.format(id=job_id)))
                return ler_json(status_response)

            payload = aguardar_job(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"completed", "ready", "succeeded"},
                estados_falha={"failed", "error"},
            )
        return self._extract_audio(payload)

    async def gerar_async(self, request: TextoParaMusicaRequest) -> str:
        model = self.resolve_model(request.modelo)
        async with criar_cliente_http_async(base_url=self.base_url, headers=self._headers(), timeout_segundos=request.timeout_segundos) as client:
            response = validar_resposta_http(await client.post(self.create_path, json={"prompt": request.prompt, "model": model}))
            created = ler_json(response)
            job_id = created.get("id") or created.get("request_id")
            if not isinstance(job_id, str):
                return await self._extract_audio_async(created)

            async def buscar_estado() -> dict[str, Any]:
                status_response = validar_resposta_http(await client.get(self.status_path.format(id=job_id)))
                return ler_json(status_response)

            payload = await aguardar_job_async(
                buscar_estado,
                timeout_segundos=request.timeout_segundos,
                extrair_estado=lambda item: str(item.get("status", "")),
                estados_sucesso={"completed", "ready", "succeeded"},
                estados_falha={"failed", "error"},
            )
        return await self._extract_audio_async(payload)


@dataclass(frozen=True, slots=True)
class BeatovenAdapter(MusicAdapter):
    """Adapter para a API publica atual de composicao da Beatoven.ai.

    A especificacao oficial atual usa:

    - `POST /api/v1/tracks/compose` com `Authorization: Bearer <token>`
    - `GET /api/v1/tasks/{task_id}` para polling

    A API publica nao expoe seletor estruturado de modelo no payload de
    composicao; por isso a interface central aceita apenas o identificador
    contratual `"maestro"` e rejeita quaisquer outros valores em `modelo`.
    A duracao tambem nao e um campo separado no endpoint atual, entao
    `duracao_segundos` nao pode ser normalizada sem alterar semanticamente o
    prompt. Para evitar degradacao silenciosa, este adapter exige que a duracao
    desejada seja descrita no proprio `prompt`.

    `parametros_provider` aceitos:

    - `format`: `"wav"`, `"mp3"` ou `"aac"`
    - `looping`: `bool`
    """

    def _montar_payload(self, request: TextoParaMusicaRequest) -> dict[str, Any]:
        if request.duracao_segundos is not None:
            raise ParametroIncompativelError(
                "Beatoven nao expoe `duracao_segundos` como campo estruturado; "
                "inclua a duracao desejada no proprio `prompt`."
            )
        parametros = dict(request.parametros_provider or {})
        permitidos = {"format", "looping"}
        invalidos = sorted(set(parametros) - permitidos)
        if invalidos:
            raise ParametroInvalidoError(
                "Parametros Beatoven nao suportados: " + ", ".join(invalidos)
            )
        formato = str(parametros.get("format", "wav")).strip().lower()
        if formato not in {"wav", "mp3", "aac"}:
            raise ParametroInvalidoError("`format` da Beatoven precisa ser `wav`, `mp3` ou `aac`.")
        payload: dict[str, Any] = {"prompt": {"text": request.prompt}, "format": formato}
        if "looping" in parametros:
            looping = parametros["looping"]
            if not isinstance(looping, bool):
                raise ParametroInvalidoError("`looping` da Beatoven precisa ser booleano.")
            payload["looping"] = looping
        return payload

    def _extrair_audio(self, payload: dict[str, Any]) -> str:
        url = extrair_primeiro_url(payload, ("meta", "track_url"), ("track_url",))
        if not url:
            raise RespostaInvalidaProviderError("Beatoven nao retornou `track_url` final.")
        return codificar_base64(baixar_bytes_sync(url))

    async def _extrair_audio_async(self, payload: dict[str, Any]) -> str:
        url = extrair_primeiro_url(payload, ("meta", "track_url"), ("track_url",))
        if not url:
            raise RespostaInvalidaProviderError("Beatoven nao retornou `track_url` final.")
        return codificar_base64(await baixar_bytes_async(url))

    def gerar(self, request: TextoParaMusicaRequest) -> str:
        api_key = self.ensure_api_key()
        self.resolve_model(request.modelo)
        with criar_cliente_http(
            base_url=BASE_URL_BEATOVEN,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            created = executar_com_retry(
                lambda: ler_json(
                    validar_resposta_http(
                        client.post("/api/v1/tracks/compose", json=self._montar_payload(request))
                    )
                ),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
            task_id = created.get("task_id")
            payload = created
            if isinstance(task_id, str):
                payload = aguardar_job(
                    lambda: ler_json(validar_resposta_http(client.get(f"/api/v1/tasks/{task_id}"))),
                    timeout_segundos=request.timeout_segundos,
                    extrair_estado=lambda item: str(item.get("status", "")),
                    estados_sucesso={"composed"},
                    estados_falha={"failed", "error"},
                )
        return self._extrair_audio(payload)

    async def gerar_async(self, request: TextoParaMusicaRequest) -> str:
        api_key = self.ensure_api_key()
        self.resolve_model(request.modelo)
        async with criar_cliente_http_async(
            base_url=BASE_URL_BEATOVEN,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            created = await executar_com_retry_async(
                lambda: _post_audio_json_async(client, "/api/v1/tracks/compose", self._montar_payload(request)),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
            task_id = created.get("task_id")
            payload = created
            if isinstance(task_id, str):
                payload = await aguardar_job_async(
                    lambda: _get_audio_json_async(client, f"/api/v1/tasks/{task_id}"),
                    timeout_segundos=request.timeout_segundos,
                    extrair_estado=lambda item: str(item.get("status", "")),
                    estados_sucesso={"composed"},
                    estados_falha={"failed", "error"},
                )
        return await self._extrair_audio_async(payload)


@dataclass(frozen=True, slots=True)
class LoudlyAdapter(MusicAdapter):
    """Adapter para a API publica da Loudly exposta no swagger oficial.

    A documentacao publica atual expoe:

    - servidor `https://soundtracks.loudly.com/`
    - autenticacao `API-KEY` em header
    - `POST /api/ai/prompt/songs` para texto-para-musica
    - retorno imediato de um objeto `ai_song` com `music_file_path`

    Modelos publicos documentados:

    - `VEGA_1`
    - `VEGA_2` (default recomendado por ser a variante mais nova presente na spec)

    `parametros_provider` aceitos:

    - `structure_id`: inteiro positivo retornado por `GET /api/ai/structures`
    - `test`: booleano. A spec documenta modo dummy para testes sem consumo de
      creditos; este pacote nao o executa durante validacoes offline, mas o
      parametro continua disponivel para uso real posterior.
    """

    def _montar_formulario(self, request: TextoParaMusicaRequest, model: str) -> dict[str, tuple[None, str]]:
        parametros = dict(request.parametros_provider or {})
        permitidos = {"structure_id", "test"}
        invalidos = sorted(set(parametros) - permitidos)
        if invalidos:
            raise ParametroInvalidoError(
                "Parametros Loudly nao suportados: " + ", ".join(invalidos)
            )
        dados: dict[str, str] = {"prompt": request.prompt, "model": model}
        if request.duracao_segundos is not None:
            if int(request.duracao_segundos) != request.duracao_segundos:
                raise ParametroInvalidoError("Loudly exige `duracao_segundos` inteiro.")
            duracao = int(request.duracao_segundos)
            if not 30 <= duracao <= 420:
                raise ParametroInvalidoError("Loudly aceita `duracao_segundos` apenas entre 30 e 420.")
            dados["duration"] = str(duracao)
        if "structure_id" in parametros:
            structure_id = parametros["structure_id"]
            if not isinstance(structure_id, int) or structure_id <= 0:
                raise ParametroInvalidoError("`structure_id` da Loudly precisa ser inteiro positivo.")
            dados["structure_id"] = str(structure_id)
        if "test" in parametros:
            test = parametros["test"]
            if not isinstance(test, bool):
                raise ParametroInvalidoError("`test` da Loudly precisa ser booleano.")
            dados["test"] = "true" if test else "false"
        return {chave: (None, valor) for chave, valor in dados.items()}

    def _extrair_audio(self, payload: dict[str, Any]) -> str:
        url = extrair_primeiro_url(payload, ("music_file_path",))
        if not url:
            raise RespostaInvalidaProviderError("Loudly nao retornou `music_file_path` final.")
        return codificar_base64(baixar_bytes_sync(url))

    async def _extrair_audio_async(self, payload: dict[str, Any]) -> str:
        url = extrair_primeiro_url(payload, ("music_file_path",))
        if not url:
            raise RespostaInvalidaProviderError("Loudly nao retornou `music_file_path` final.")
        return codificar_base64(await baixar_bytes_async(url))

    def gerar(self, request: TextoParaMusicaRequest) -> str:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        with criar_cliente_http(
            base_url=BASE_URL_LOUDLY,
            headers={"API-KEY": api_key},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            payload = executar_com_retry(
                lambda: ler_json(
                    validar_resposta_http(
                        client.post("/api/ai/prompt/songs", files=self._montar_formulario(request, model))
                    )
                ),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
        return self._extrair_audio(payload)

    async def gerar_async(self, request: TextoParaMusicaRequest) -> str:
        api_key = self.ensure_api_key()
        model = self.resolve_model(request.modelo)
        async with criar_cliente_http_async(
            base_url=BASE_URL_LOUDLY,
            headers={"API-KEY": api_key},
            timeout_segundos=request.timeout_segundos,
        ) as client:
            payload = await executar_com_retry_async(
                lambda: _post_audio_form_async(
                    client,
                    "/api/ai/prompt/songs",
                    self._montar_formulario(request, model),
                ),
                max_tentativas=request.max_tentativas,
                deve_tentar_novamente=excecao_e_retryable,
            )
        return await self._extrair_audio_async(payload)


async def _post_audio_json_async(client: Any, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return ler_json(validar_resposta_http(await client.post(path, json=payload)))


async def _post_audio_form_async(
    client: Any,
    path: str,
    files: dict[str, tuple[None, str]],
) -> dict[str, Any]:
    return ler_json(validar_resposta_http(await client.post(path, files=files)))


async def _get_audio_json_async(client: Any, path: str) -> dict[str, Any]:
    return ler_json(validar_resposta_http(await client.get(path)))
