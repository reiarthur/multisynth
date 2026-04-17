import pytest

from multisynth import image


class _FakeImageAdapter:
    def resolve_model(self, model):
        return model or "gpt-image-1"

    def gerar(self, request):
        return "ZmFrZS1pbWFnZQ=="

    async def gerar_async(self, request):
        return self.gerar(request)


class _FakeRegistries:
    generate = {"openai": _FakeImageAdapter()}
    transform = {"openai": _FakeImageAdapter()}
    edit_without_mask = {"openai": _FakeImageAdapter()}
    edit_with_mask = {"openai": _FakeImageAdapter()}


def test_generate_and_edit_mocked(monkeypatch) -> None:
    monkeypatch.setattr(image, "build_image_registries", lambda credentials=None: _FakeRegistries())
    generated = image.generate(provider="openai", prompt="cat")
    edited = image.edit(provider="openai", prompt="cat", image=b"img")
    assert generated.image_base64 == "ZmFrZS1pbWFnZQ=="
    assert edited.metadata["provider"] == "openai"


@pytest.mark.asyncio
async def test_transform_async_mocked(monkeypatch) -> None:
    monkeypatch.setattr(image, "build_image_registries", lambda credentials=None: _FakeRegistries())
    transformed = await image.transform_async(provider="openai", prompt="cat", image=b"img")
    assert transformed.image_base64 == "ZmFrZS1pbWFnZQ=="
