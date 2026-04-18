from __future__ import annotations

import re
from pathlib import Path

import pytest

from easy_ai_api import text
from easy_ai_api._core.provider_catalog import KNOWN_CREDENTIAL_ENV_VARS, PROVIDER_SPECS
from easy_ai_api.exceptions import MissingCredentialError

ROOT = Path(__file__).resolve().parents[1]


def _python_blocks(markdown: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", markdown, flags=re.DOTALL)


def test_missing_credential_error_is_typed(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingCredentialError) as exc_info:
        text.generate(provider="openai", instructions="hello")
    assert exc_info.value.provider == "openai"
    assert exc_info.value.env_vars == ("OPENAI_API_KEY",)


def test_env_example_matches_known_credentials() -> None:
    env_lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    exported_names = {
        line.split("=", maxsplit=1)[0]
        for line in env_lines
        if line and not line.startswith("#") and "=" in line
    }
    assert exported_names == KNOWN_CREDENTIAL_ENV_VARS


def test_readme_mentions_every_provider() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for spec in PROVIDER_SPECS:
        assert f"`{spec.provider}`" in readme


def test_documentation_python_blocks_are_valid_syntax() -> None:
    markdown_files = [
        ROOT / "README.md",
        ROOT / "docs" / "configuration.md",
        ROOT / "docs" / "errors.md",
    ]
    for file_path in markdown_files:
        for block in _python_blocks(file_path.read_text(encoding="utf-8")):
            compile(block, str(file_path), "exec")


def test_source_tree_does_not_import_nova() -> None:
    assert not (ROOT / "nova").exists()
    pattern = re.compile(r"^\s*(from|import)\s+nova\b", flags=re.MULTILINE)
    for file_path in (ROOT / "src").rglob("*.py"):
        assert not pattern.search(file_path.read_text(encoding="utf-8")), file_path
