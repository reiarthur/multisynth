"""Cliente opcional com credenciais e defaults compartilhados.

Última atualização: 2026-04-18
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import audio as audio_api
from . import image as image_api
from . import text as text_api
from . import video as video_api


@dataclass(frozen=True, slots=True)
class _ClientDefaults:
    timeout_seconds: float | None = None
    job_timeout_seconds: float | None = None
    max_retries: int | None = None


class _BaseFacade:
    """Base helper used by the modality namespaces exposed on ``EasyAiApi``."""

    def __init__(self, client: EasyAiApi) -> None:
        self._client = client

    def _with_defaults(self, kwargs: dict[str, object], *, job: bool = False) -> dict[str, object]:
        enriched = dict(kwargs)
        timeout_key = "timeout_seconds"
        default_timeout = (
            self._client.defaults.job_timeout_seconds
            if job
            else self._client.defaults.timeout_seconds
        )
        if timeout_key not in enriched and default_timeout is not None:
            enriched[timeout_key] = default_timeout
        if "max_retries" not in enriched and self._client.defaults.max_retries is not None:
            enriched["max_retries"] = self._client.defaults.max_retries
        return enriched


class _TextFacade(_BaseFacade):
    """Stateful namespace for text generation helpers."""

    def generate(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.text.generate` com defaults do cliente."""

        return text_api.generate(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def generate_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`generate`."""

        return await text_api.generate_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def batch_generate(self, requests, /, **kwargs):
        """Chama :func:`easy_ai_api.text.batch_generate` com credenciais compartilhadas."""

        return text_api.batch_generate(requests, credentials=self._client.credentials, **kwargs)

    async def batch_generate_async(self, requests, /, **kwargs):
        """Variante assíncrona de :meth:`batch_generate`."""

        return await text_api.batch_generate_async(
            requests,
            credentials=self._client.credentials,
            **kwargs,
        )


class _AudioFacade(_BaseFacade):
    """Stateful namespace for audio helpers."""

    def transcribe(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.audio.transcribe` com defaults compartilhados."""

        return audio_api.transcribe(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def transcribe_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`transcribe`."""

        return await audio_api.transcribe_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def synthesize(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.audio.synthesize` com defaults compartilhados."""

        return audio_api.synthesize(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def synthesize_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`synthesize`."""

        return await audio_api.synthesize_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def compose(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.audio.compose` com defaults compartilhados."""

        return audio_api.compose(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def compose_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`compose`."""

        return await audio_api.compose_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )


class _ImageFacade(_BaseFacade):
    """Stateful namespace for image helpers."""

    def generate(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.image.generate` com defaults compartilhados."""

        return image_api.generate(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def generate_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`generate`."""

        return await image_api.generate_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def transform(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.image.transform` com defaults compartilhados."""

        return image_api.transform(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def transform_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`transform`."""

        return await image_api.transform_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def compose(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.image.compose` com defaults compartilhados."""

        return image_api.compose(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def compose_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`compose`."""

        return await image_api.compose_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def edit(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.image.edit` com defaults compartilhados."""

        return image_api.edit(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def edit_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`edit`."""

        return await image_api.edit_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )


class _VideoFacade(_BaseFacade):
    """Stateful namespace for video helpers."""

    def generate(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.video.generate` com defaults de job."""

        return video_api.generate(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )

    async def generate_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`generate`."""

        return await video_api.generate_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )

    def lipsync(self, request=None, /, **kwargs):
        """Chama :func:`easy_ai_api.video.lipsync` com defaults de job."""

        return video_api.lipsync(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )

    async def lipsync_async(self, request=None, /, **kwargs):
        """Variante assíncrona de :meth:`lipsync`."""

        return await video_api.lipsync_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )


class EasyAiApi:
    """Cliente com credenciais e defaults compartilhados para todas as chamadas.

    Args:
        credentials: Credenciais explícitas usadas antes das variáveis de ambiente.
        timeout_seconds: Timeout padrão para operações de texto, áudio e imagem quando
            uma chamada específica não sobrescreve.
        job_timeout_seconds: Timeout padrão para jobs de vídeo de longa duração.
        max_retries: Quantidade padrão de retries compartilhada entre as modalidades.

    Attributes:
        text: Namespace com métodos de geração de texto.
        audio: Namespace com transcrição, síntese e música.
        image: Namespace com geração, transformação, composição e edição de imagens.
        video: Namespace com geração e lip-sync de vídeo.
    """

    def __init__(
        self,
        *,
        credentials: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
        job_timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.credentials = dict(credentials or {})
        self.defaults = _ClientDefaults(
            timeout_seconds=timeout_seconds,
            job_timeout_seconds=job_timeout_seconds,
            max_retries=max_retries,
        )
        self.text = _TextFacade(self)
        self.audio = _AudioFacade(self)
        self.image = _ImageFacade(self)
        self.video = _VideoFacade(self)
