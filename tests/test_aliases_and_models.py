import pytest

from easy_ai_api._core.aliases import normalizar_api
from easy_ai_api.models import TextGenerationRequest


def test_normalize_provider_aliases() -> None:
    assert normalizar_api("gemini") == "google"
    assert normalizar_api("open-ai") == "openai"
    assert normalizar_api("d-id") == "did"


def test_text_request_rejects_conflicting_token_limits() -> None:
    with pytest.raises(ValueError):
        TextGenerationRequest(
            provider="openai",
            instructions="hello",
            max_tokens=10,
            max_output_tokens=20,
        )
