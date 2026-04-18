from easy_ai_api.audio.providers import build_audio_registries
from easy_ai_api.text.providers import build_text_registry


def test_text_registry_resolves_env_lazily(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    registry = build_text_registry()
    assert registry["openai"].api_key == "env-openai"


def test_audio_registry_prefers_explicit_credentials(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "env-google")
    registries = build_audio_registries({"GOOGLE_API_KEY": "explicit-google"})
    assert registries.music["google"].api_key == "explicit-google"
