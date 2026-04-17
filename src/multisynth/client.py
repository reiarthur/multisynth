"""Optional client object with shared credentials and request defaults."""

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
    """Base helper used by the modality namespaces exposed on ``Multisynth``."""

    def __init__(self, client: Multisynth) -> None:
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
        """Call :func:`multisynth.text.generate` with shared client defaults."""

        return text_api.generate(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def generate_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`generate`."""

        return await text_api.generate_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def batch_generate(self, requests, /, **kwargs):
        """Call :func:`multisynth.text.batch_generate` with shared credentials."""

        return text_api.batch_generate(requests, credentials=self._client.credentials, **kwargs)

    async def batch_generate_async(self, requests, /, **kwargs):
        """Async variant of :meth:`batch_generate`."""

        return await text_api.batch_generate_async(
            requests,
            credentials=self._client.credentials,
            **kwargs,
        )


class _AudioFacade(_BaseFacade):
    """Stateful namespace for audio helpers."""

    def transcribe(self, request=None, /, **kwargs):
        """Call :func:`multisynth.audio.transcribe` with shared defaults."""

        return audio_api.transcribe(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def transcribe_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`transcribe`."""

        return await audio_api.transcribe_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def synthesize(self, request=None, /, **kwargs):
        """Call :func:`multisynth.audio.synthesize` with shared defaults."""

        return audio_api.synthesize(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def synthesize_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`synthesize`."""

        return await audio_api.synthesize_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def compose(self, request=None, /, **kwargs):
        """Call :func:`multisynth.audio.compose` with shared defaults."""

        return audio_api.compose(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def compose_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`compose`."""

        return await audio_api.compose_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )


class _ImageFacade(_BaseFacade):
    """Stateful namespace for image helpers."""

    def generate(self, request=None, /, **kwargs):
        """Call :func:`multisynth.image.generate` with shared defaults."""

        return image_api.generate(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def generate_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`generate`."""

        return await image_api.generate_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def transform(self, request=None, /, **kwargs):
        """Call :func:`multisynth.image.transform` with shared defaults."""

        return image_api.transform(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def transform_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`transform`."""

        return await image_api.transform_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    def edit(self, request=None, /, **kwargs):
        """Call :func:`multisynth.image.edit` with shared defaults."""

        return image_api.edit(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )

    async def edit_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`edit`."""

        return await image_api.edit_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs),
        )


class _VideoFacade(_BaseFacade):
    """Stateful namespace for video helpers."""

    def generate(self, request=None, /, **kwargs):
        """Call :func:`multisynth.video.generate` with shared job defaults."""

        return video_api.generate(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )

    async def generate_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`generate`."""

        return await video_api.generate_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )

    def lipsync(self, request=None, /, **kwargs):
        """Call :func:`multisynth.video.lipsync` with shared job defaults."""

        return video_api.lipsync(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )

    async def lipsync_async(self, request=None, /, **kwargs):
        """Async variant of :meth:`lipsync`."""

        return await video_api.lipsync_async(
            request,
            credentials=self._client.credentials,
            **self._with_defaults(kwargs, job=True),
        )


class Multisynth:
    """Stateful client that shares credentials and request defaults.

    Args:
        credentials: Explicit credentials used before environment variables.
        timeout_seconds: Default timeout applied to text, audio, and image
            operations when a call does not override it.
        job_timeout_seconds: Default timeout applied to long-running video jobs.
        max_retries: Default retry count shared across all modality helpers.

    Attributes:
        text: Namespace exposing text-generation methods.
        audio: Namespace exposing transcription, synthesis, and music methods.
        image: Namespace exposing image generation, transform, and edit methods.
        video: Namespace exposing video generation and lip-sync methods.
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
