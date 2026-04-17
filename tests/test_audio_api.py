import pytest

from multisynth import audio
from multisynth._core.schemas import (
    AudioParaTextoResultado,
    PalavraTemporizada,
    TextoParaAudioResultado,
    TrechoSpeaker,
)


class _FakeTranscriptionAdapter:
    def transcrever(self, request):
        palavra = PalavraTemporizada(indice=0, texto="hello", inicio_s="0", fim_s="1")
        speaker = TrechoSpeaker(speaker="speaker_1", inicio_s="0", fim_s="1", texto="hello")
        return AudioParaTextoResultado(texto="hello", palavras=[palavra], trechos_por_speaker=[speaker], metadata={"provider": "deepgram"})

    async def transcrever_async(self, request):
        return self.transcrever(request)


class _FakeSynthesisAdapter:
    def sintetizar(self, request):
        palavra = PalavraTemporizada(indice=0, texto="hello", inicio_s="0", fim_s="1")
        return TextoParaAudioResultado(audio_base64="ZmFrZQ==", palavras=[palavra], metadata={"provider": "cartesia"})

    async def sintetizar_async(self, request):
        return self.sintetizar(request)


class _FakeMusicAdapter:
    def resolve_model(self, model):
        return model or "music_v1"

    def gerar(self, request):
        return "ZmFrZS1tdXNpYw=="

    async def gerar_async(self, request):
        return self.gerar(request)


class _FakeRegistries:
    transcription = {"deepgram": _FakeTranscriptionAdapter()}
    synthesis = {"cartesia": _FakeSynthesisAdapter()}
    music = {"elevenlabs": _FakeMusicAdapter()}


def test_transcribe_mocked(monkeypatch) -> None:
    monkeypatch.setattr(audio, "build_audio_registries", lambda credentials=None: _FakeRegistries())
    result = audio.transcribe(provider="deepgram", audio=b"123")
    assert result.text == "hello"
    assert result.words[0].text == "hello"


@pytest.mark.asyncio
async def test_synthesize_and_compose_async_mocked(monkeypatch) -> None:
    monkeypatch.setattr(audio, "build_audio_registries", lambda credentials=None: _FakeRegistries())
    synthesis = await audio.synthesize_async(provider="cartesia", text="hello")
    music = await audio.compose_async(provider="elevenlabs", prompt="lofi")
    assert synthesis.audio_base64 == "ZmFrZQ=="
    assert music.audio_base64 == "ZmFrZS1tdXNpYw=="
