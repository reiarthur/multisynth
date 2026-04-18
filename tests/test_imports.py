from easy_ai_api import EasyAiApi, audio, image, text, video


def test_public_import_smoke() -> None:
    client = EasyAiApi()
    assert text.generate.__name__ == "generate"
    assert audio.transcribe.__name__ == "transcribe"
    assert image.generate.__name__ == "generate"
    assert image.compose.__name__ == "compose"
    assert video.generate.__name__ == "generate"
    assert client.text is not None
    assert client.audio is not None
    assert client.image is not None
    assert client.image.compose is not None
    assert client.video is not None
