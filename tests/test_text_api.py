import pytest

from multisynth import text
from multisynth._core.exceptions import IncompatibleParameterError
from multisynth._core.schemas import TextoParaTextoResultado
from multisynth.models import TextGenerationRequest


class _FakeTextAdapter:
    provider = "openai"
    default_model = "gpt-5-mini"

    def gerar(self, request):
        return TextoParaTextoResultado(texto=f"echo:{request.instrucoes}", custo_usd="0.123")

    async def gerar_async(self, request):
        return TextoParaTextoResultado(texto=f"async:{request.instrucoes}", custo_usd="0.456")


def test_generate_text_with_fake_registry(monkeypatch) -> None:
    monkeypatch.setattr(text, "build_text_registry", lambda credentials=None: {"openai": _FakeTextAdapter()})
    result = text.generate(provider="openai", instructions="hello")
    assert result.text == "echo:hello"


@pytest.mark.asyncio
async def test_generate_text_async_with_fake_registry(monkeypatch) -> None:
    monkeypatch.setattr(text, "build_text_registry", lambda credentials=None: {"openai": _FakeTextAdapter()})
    result = await text.generate_async(provider="openai", instructions="hello")
    assert result.text == "async:hello"


def test_batch_generate_requires_same_provider() -> None:
    with pytest.raises(IncompatibleParameterError):
        text.batch_generate(
            [
                TextGenerationRequest(provider="openai", instructions="a"),
                TextGenerationRequest(provider="google", instructions="b"),
            ]
        )
