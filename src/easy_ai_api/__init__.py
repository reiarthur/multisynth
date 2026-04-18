"""Exports públicos do pacote easy-ai-api.

Última atualização: 2026-04-18
"""

from ._core.config import VERSION
from .client import EasyAiApi
from .exceptions import (
    ConfigurationError,
    EasyAiApiError,
    IncompatibleParameterError,
    InvalidParameterError,
    InvalidProviderResponseError,
    JobFailedError,
    MissingCredentialError,
    PricingUnavailableError,
    ProviderTimeoutError,
    TemporaryDownloadError,
    UnsupportedModelError,
    UnsupportedProviderError,
)
from .models import (
    ImageCompositionRequest,
    ImageEditRequest,
    ImageGenerationRequest,
    ImageResult,
    ImageTransformationRequest,
    LipSyncRequest,
    MusicGenerationRequest,
    MusicGenerationResult,
    SpeakerSegment,
    SpeechSynthesisRequest,
    SpeechSynthesisResult,
    SpeechTranscriptionRequest,
    SpeechTranscriptionResult,
    TextGenerationRequest,
    TextGenerationResult,
    VideoGenerationRequest,
    VideoResult,
    WordTiming,
)

__all__ = [
    "ConfigurationError",
    "EasyAiApi",
    "EasyAiApiError",
    "ImageCompositionRequest",
    "ImageEditRequest",
    "ImageGenerationRequest",
    "ImageResult",
    "ImageTransformationRequest",
    "IncompatibleParameterError",
    "InvalidParameterError",
    "InvalidProviderResponseError",
    "JobFailedError",
    "LipSyncRequest",
    "MissingCredentialError",
    "MusicGenerationRequest",
    "MusicGenerationResult",
    "PricingUnavailableError",
    "ProviderTimeoutError",
    "SpeakerSegment",
    "SpeechSynthesisRequest",
    "SpeechSynthesisResult",
    "SpeechTranscriptionRequest",
    "SpeechTranscriptionResult",
    "TemporaryDownloadError",
    "TextGenerationRequest",
    "TextGenerationResult",
    "UnsupportedModelError",
    "UnsupportedProviderError",
    "VideoGenerationRequest",
    "VideoResult",
    "WordTiming",
]

__version__ = VERSION
