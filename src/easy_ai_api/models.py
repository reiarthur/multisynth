"""Modelos públicos canônicos de easy-ai-api.

Última atualização: 2026-04-18
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ._core.config import DEFAULT_JOB_TIMEOUT_SECONDS, DEFAULT_RETRIES, DEFAULT_TIMEOUT_SECONDS


class PublicModel(BaseModel):
    """Base class for frozen public request and result models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
    )


class WordTiming(PublicModel):
    """Word-level timing returned by speech transcription or synthesis providers.

    Attributes:
        index: Zero-based position of the word in the sequence.
        text: Word text as returned by the provider.
        start_seconds: Word start time in seconds.
        end_seconds: Word end time in seconds.
        speaker: Optional speaker label when diarization is available.
        confidence: Optional confidence score between 0 and 1.
    """

    index: int = Field(ge=0, description="Zero-based word index.")
    text: str = Field(min_length=1, description="Word text.")
    start_seconds: Decimal = Field(ge=Decimal("0"), description="Word start time in seconds.")
    end_seconds: Decimal = Field(ge=Decimal("0"), description="Word end time in seconds.")
    speaker: str | None = Field(default=None, description="Optional speaker label.")
    confidence: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Optional confidence score between 0 and 1.",
    )


class SpeakerSegment(PublicModel):
    """Speaker-attributed segment returned by diarization-aware providers."""

    speaker: str = Field(min_length=1, description="Speaker label.")
    start_seconds: Decimal = Field(
        ge=Decimal("0"),
        description="Segment start time in seconds.",
    )
    end_seconds: Decimal = Field(
        ge=Decimal("0"),
        description="Segment end time in seconds.",
    )
    text: str = Field(min_length=1, description="Transcript text for the segment.")


class TextGenerationRequest(PublicModel):
    """Request payload for ``easy_ai_api.text`` helpers.

    Attributes:
        provider: Provider name or supported alias.
        instructions: Primary instruction prompt.
        context: Optional supporting context as text, a list, or structured data.
        model: Optional explicit provider model override.
        temperature: Optional sampling temperature.
        top_p: Optional nucleus sampling value.
        max_tokens: Optional provider token limit alias.
        max_output_tokens: Optional explicit output token limit.
        seed: Optional deterministic seed when supported.
        stop: Optional stop sequence or list of sequences.
        stream: Whether to request streamed output when the provider supports it.
        tools: Optional tool declarations for tool-capable LLM providers.
        tool_choice: Optional tool-choice policy.
        response_format: Optional structured output contract.
        reasoning_effort: Optional provider-specific reasoning control.
        thinking: Optional provider-specific “thinking” configuration.
        input_images: Optional input images as file paths, bytes, or base64 strings.
        timeout_seconds: Per-call timeout in seconds.
        max_retries: Maximum retry attempts for retryable failures.
        provider_params: Raw provider-specific payload extensions.
    """

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    instructions: str = Field(min_length=1, description="Primary instruction prompt.")
    context: str | list[str] | dict[str, Any] | None = Field(
        default=None,
        description="Optional supporting context as text, a list, or a JSON-like object.",
    )
    model: str | None = Field(default=None, description="Optional provider model override.")
    temperature: float | None = Field(default=None, ge=0, le=2, description="Sampling temperature.")
    top_p: float | None = Field(default=None, gt=0, le=1, description="Nucleus sampling value.")
    max_tokens: int | None = Field(default=None, gt=0, description="Legacy token limit alias.")
    max_output_tokens: int | None = Field(default=None, gt=0, description="Output token limit.")
    seed: int | None = Field(default=None, description="Optional deterministic seed.")
    stop: str | list[str] | None = Field(
        default=None,
        description="Optional stop sequence or list of sequences.",
    )
    stream: bool = Field(default=False, description="Whether to request streamed output.")
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional tool declarations passed through to the provider.",
    )
    tool_choice: str | dict[str, Any] | None = Field(
        default=None,
        description="Optional tool-choice strategy.",
    )
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured output contract.",
    )
    reasoning_effort: str | None = Field(
        default=None,
        description="Optional provider-specific reasoning level.",
    )
    thinking: dict[str, Any] | None = Field(
        default=None,
        description="Optional provider-specific thinking configuration.",
    )
    input_images: list[str | bytes] | None = Field(
        default=None,
        description="Optional input images as file paths, base64 strings, or bytes.",
    )
    timeout_seconds: float = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        gt=0,
        description="Per-call timeout in seconds.",
    )
    max_retries: int = Field(
        default=DEFAULT_RETRIES,
        ge=1,
        le=10,
        description="Maximum retry attempts for retryable failures.",
    )
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )

    @field_validator("stop")
    @classmethod
    def validate_stop(cls, value: str | list[str] | None) -> str | list[str] | None:
        if value is None:
            return value
        if isinstance(value, list) and not value:
            raise ValueError("`stop` cannot be an empty list.")
        return value

    @model_validator(mode="after")
    def validate_token_limits(self) -> TextGenerationRequest:
        if self.max_tokens and self.max_output_tokens and self.max_tokens != self.max_output_tokens:
            raise ValueError("`max_tokens` and `max_output_tokens` cannot differ.")
        return self


class TextGenerationResult(PublicModel):
    """Normalized text-generation result."""

    text: str = Field(min_length=1, description="Generated text.")
    cost_usd: Decimal = Field(
        ge=Decimal("0"),
        description="Exact USD cost when pricing is available for the provider/model.",
    )


class SpeechTranscriptionRequest(PublicModel):
    """Request payload for speech transcription."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    audio: str | bytes = Field(description="Audio input as a local path, base64 string, or bytes.")
    model: str | None = Field(default=None, description="Optional transcription model override.")
    language: str | None = Field(default=None, description="Optional language hint.")
    diarization: bool = Field(default=True, description="Whether speaker diarization should be requested.")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class SpeechTranscriptionResult(PublicModel):
    """Normalized transcription result."""

    text: str = Field(min_length=1, description="Full transcript text.")
    words: list[WordTiming] = Field(description="Word-level timing items.")
    speaker_segments: list[SpeakerSegment] = Field(description="Speaker-attributed segments.")
    metadata: dict[str, Any] = Field(description="Provider metadata for the completed job.")


class SpeechSynthesisRequest(PublicModel):
    """Request payload for speech synthesis."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    text: str = Field(min_length=1, description="Text to synthesize.")
    model: str | None = Field(default=None, description="Optional speech model override.")
    voice: str | None = Field(default=None, description="Optional provider voice identifier.")
    language: str | None = Field(default=None, description="Optional language hint.")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class SpeechSynthesisResult(PublicModel):
    """Normalized speech-synthesis result."""

    audio_base64: str = Field(min_length=1, description="Base64-encoded output audio.")
    words: list[WordTiming] = Field(description="Optional word timing details.")
    metadata: dict[str, Any] = Field(description="Provider metadata for the completed synthesis.")


class MusicGenerationRequest(PublicModel):
    """Request payload for soundtrack or instrumental music generation."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    prompt: str = Field(min_length=1, description="Music prompt or style instruction.")
    model: str | None = Field(default=None, description="Optional music model override.")
    duration_seconds: float | None = Field(
        default=None,
        gt=0,
        description="Optional target duration in seconds.",
    )
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class MusicGenerationResult(PublicModel):
    """Normalized music-generation result."""

    audio_base64: str = Field(min_length=1, description="Base64-encoded generated audio.")
    metadata: dict[str, Any] = Field(description="Provider metadata for the completed generation.")


class ImageGenerationRequest(PublicModel):
    """Request payload for text-to-image generation."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    prompt: str = Field(min_length=1, description="Primary image-generation prompt.")
    negative_prompt: str | None = Field(default=None, description="Optional negative prompt.")
    model: str | None = Field(default=None, description="Optional image model override.")
    width: int | None = Field(default=None, gt=0, description="Optional output width in pixels.")
    height: int | None = Field(default=None, gt=0, description="Optional output height in pixels.")
    seed: int | None = Field(default=None, description="Optional deterministic seed.")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class ImageTransformationRequest(PublicModel):
    """Request payload for prompt-guided image transformation."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    prompt: str = Field(min_length=1, description="Instruction prompt for the transformation.")
    image: str | bytes = Field(description="Input image as a local path, base64 string, or bytes.")
    negative_prompt: str | None = Field(default=None, description="Optional negative prompt.")
    model: str | None = Field(default=None, description="Optional image model override.")
    strength: float | None = Field(default=None, ge=0, le=1, description="Transformation strength when supported.")
    seed: int | None = Field(default=None, description="Optional deterministic seed.")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class ImageCompositionRequest(PublicModel):
    """Request payload para composição imagem+imagem+texto → imagem.

    Recebe ``image`` como imagem-base (sujeito principal a transformar) e
    ``reference_image`` como imagem adicional de referência (estilo, cena,
    pose ou qualquer outra inspiração). O ``prompt`` descreve como combinar
    as duas imagens. Úteis, por exemplo, para pedir "gere a pessoa da
    imagem 1 no estilo da imagem 2" ou "coloque a pessoa da imagem 1 na
    cena da imagem 2".

    Attributes:
        provider: Nome do provider ou alias suportado.
        prompt: Instrução descrevendo como combinar as imagens.
        image: Imagem principal a ser transformada.
        reference_image: Imagem adicional usada como referência.
        negative_prompt: Prompt negativo opcional.
        model: Override opcional do modelo do provider.
        strength: Intensidade opcional da composição quando suportada.
        seed: Seed determinística opcional.
        timeout_seconds: Timeout por chamada em segundos.
        max_retries: Máximo de tentativas para falhas retryable.
        provider_params: Extensões brutas de payload específicas do provider.
    """

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    prompt: str = Field(min_length=1, description="Instruction prompt describing how to combine both images.")
    image: str | bytes = Field(description="Base image as a local path, base64 string, or bytes.")
    reference_image: str | bytes = Field(
        description="Reference image as a local path, base64 string, or bytes.",
    )
    negative_prompt: str | None = Field(default=None, description="Optional negative prompt.")
    model: str | None = Field(default=None, description="Optional image model override.")
    strength: float | None = Field(default=None, ge=0, le=1, description="Composition strength when supported.")
    seed: int | None = Field(default=None, description="Optional deterministic seed.")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class ImageEditRequest(PublicModel):
    """Request payload for image editing with an optional mask.

    When `mask` is supplied, it must be a PNG grayscale image with the same
    dimensions as `image`. **Black pixels (0) mark regions to be edited**;
    white pixels (255) mark regions to preserve. The library converts the
    mask internally to the format required by each provider.
    """

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    prompt: str = Field(min_length=1, description="Instruction prompt for the edit.")
    image: str | bytes = Field(description="Base image as a local path, base64 string, or bytes.")
    mask: str | bytes | None = Field(
        default=None,
        description=(
            "Optional mask as a local path, base64 string, or bytes. "
            "Must be a PNG grayscale image with the same dimensions as `image`. "
            "Black pixels (0) mark regions to be edited; white pixels (255) mark regions to preserve. "
            "Each provider adapter converts this mask internally to its own format."
        ),
    )
    negative_prompt: str | None = Field(default=None, description="Optional negative prompt.")
    model: str | None = Field(default=None, description="Optional image model override.")
    seed: int | None = Field(default=None, description="Optional deterministic seed.")
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0, description="Per-call timeout in seconds.")
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class ImageResult(PublicModel):
    """Normalized image result."""

    image_base64: str = Field(min_length=1, description="Base64-encoded image output.")
    metadata: dict[str, Any] = Field(description="Provider metadata for the completed generation.")


class VideoGenerationRequest(PublicModel):
    """Request payload for video generation."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    output_path: Path = Field(description="Local filesystem path where the final video should be written.")
    prompt: str | None = Field(default=None, description="Optional text prompt for the video.")
    image: str | bytes | None = Field(
        default=None,
        description="Optional image input as a local path, base64 string, or bytes.",
    )
    audio: str | bytes | None = Field(
        default=None,
        description="Optional audio input as a local path, base64 string, or bytes.",
    )
    model: str | None = Field(default=None, description="Optional video model override.")
    timeout_seconds: float = Field(
        default=DEFAULT_JOB_TIMEOUT_SECONDS,
        gt=0,
        description="Per-call timeout in seconds for long-running jobs.",
    )
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class LipSyncRequest(PublicModel):
    """Request payload for lip-sync video generation."""

    provider: str = Field(min_length=1, description="Provider name or supported alias.")
    output_path: Path = Field(description="Local filesystem path where the final video should be written.")
    image: str | bytes = Field(description="Image input as a local path, base64 string, or bytes.")
    audio: str | bytes = Field(description="Audio input as a local path, base64 string, or bytes.")
    model: str | None = Field(default=None, description="Optional provider model override.")
    timeout_seconds: float = Field(
        default=DEFAULT_JOB_TIMEOUT_SECONDS,
        gt=0,
        description="Per-call timeout in seconds for long-running jobs.",
    )
    max_retries: int = Field(default=DEFAULT_RETRIES, ge=1, le=10, description="Maximum retry attempts.")
    provider_params: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider-specific payload extensions.",
    )


class VideoResult(PublicModel):
    """Normalized video result."""

    output_path: Path = Field(description="Local filesystem path to the written output video.")
    metadata: dict[str, Any] = Field(description="Provider metadata for the completed job.")
