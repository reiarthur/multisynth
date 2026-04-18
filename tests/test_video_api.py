from pathlib import Path

import pytest

from easy_ai_api import video
from easy_ai_api._core.exceptions import UnsupportedProviderError


class _FakeVideoAdapter:
    def resolve_model(self, model):
        return model or "gen4_turbo"

    def gerar(self, request):
        Path(request.caminho_saida).write_bytes(b"video")

    async def gerar_async(self, request):
        self.gerar(request)


class _FakeVideoRegistries:
    without_audio = {"runway": _FakeVideoAdapter()}
    with_audio = {"heygen": _FakeVideoAdapter()}
    lipsync = {"heygen": _FakeVideoAdapter()}


def test_generate_video_mocked(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(video, "build_video_registries", lambda credentials=None: _FakeVideoRegistries())
    result = video.generate(provider="runway", output_path=tmp_path / "video.mp4", prompt="shot")
    assert result.output_path.exists()


@pytest.mark.asyncio
async def test_lipsync_async_mocked(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(video, "build_video_registries", lambda credentials=None: _FakeVideoRegistries())
    result = await video.lipsync_async(
        provider="heygen",
        output_path=tmp_path / "lip.mp4",
        image=b"image",
        audio=b"audio",
    )
    assert result.output_path.exists()


def test_generate_video_rejects_wrong_registry(tmp_path) -> None:
    with pytest.raises(UnsupportedProviderError):
        video.generate(provider="google", output_path=tmp_path / "video.mp4", prompt="shot")
