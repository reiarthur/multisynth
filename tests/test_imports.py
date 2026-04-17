from multisynth import Multisynth, audio, image, text, video


def test_public_import_smoke() -> None:
    client = Multisynth()
    assert text.generate.__name__ == "generate"
    assert audio.transcribe.__name__ == "transcribe"
    assert image.generate.__name__ == "generate"
    assert video.generate.__name__ == "generate"
    assert client.text is not None
    assert client.audio is not None
    assert client.image is not None
    assert client.video is not None
