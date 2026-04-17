"""Local file helpers."""

from __future__ import annotations

from pathlib import Path

from .exceptions import InvalidParameterError


def ensure_parent_dir(path: str | Path) -> Path:
    """Create the parent directory for a destination file when needed."""

    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def read_file_bytes(path: str | Path, *, field_name: str) -> bytes:
    """Read a local file as bytes with clear validation."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise InvalidParameterError(f"The file passed in `{field_name}` does not exist: {resolved}")
    return resolved.read_bytes()


def write_file_bytes(path: str | Path, content: bytes) -> Path:
    """Persist bytes to the target path, creating parent directories as needed."""

    destination = ensure_parent_dir(path)
    destination.write_bytes(content)
    return destination


# Internal compatibility aliases used by the ported provider layer.
garantir_diretorio_pai = ensure_parent_dir
ler_bytes_de_arquivo = read_file_bytes
salvar_bytes = write_file_bytes
