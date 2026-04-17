"""Binary/media normalization helpers safe for Python 3.12+."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image

from .exceptions import IncompatibleParameterError, InvalidParameterError
from .files import read_file_bytes

_IMAGE_MIME_BY_PIL_FORMAT = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "GIF": "image/gif",
    "WEBP": "image/webp",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
}


@dataclass(frozen=True, slots=True)
class NormalizedBinaryContent:
    data: bytes
    mime_type: str | None
    source: str

    @property
    def dados(self) -> bytes:
        return self.data


def _looks_like_base64(text: str) -> bool:
    raw = text.strip()
    if raw.startswith("data:") and ";base64," in raw:
        return True
    if len(raw) < 16 or len(raw) % 4 != 0:
        return False
    try:
        base64.b64decode(raw, validate=True)
        return True
    except (binascii.Error, ValueError):
        return False


def _strip_base64_prefix(text: str) -> str:
    raw = text.strip()
    if raw.startswith("data:") and ";base64," in raw:
        return raw.split(";base64,", maxsplit=1)[1]
    return raw


def infer_mime_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"RIFF") and b"WAVE" in content[:16]:
        return "audio/wav"
    if content.startswith(b"ID3") or content[:2] == b"\xff\xfb":
        return "audio/mpeg"
    if content.startswith(b"OggS"):
        return "audio/ogg"
    if len(content) > 8 and content[4:8] == b"ftyp":
        return "video/mp4"
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    try:
        image = Image.open(BytesIO(content))
        image.load()
    except Exception:  # noqa: BLE001
        return None
    return _IMAGE_MIME_BY_PIL_FORMAT.get((image.format or "").upper())


def normalizar_entrada_binaria(valor: str | bytes | Path, *, nome_campo: str) -> NormalizedBinaryContent:
    if isinstance(valor, bytes):
        return NormalizedBinaryContent(valor, infer_mime_type(valor), "bytes")
    if isinstance(valor, Path):
        dados = read_file_bytes(valor, field_name=nome_campo)
        return NormalizedBinaryContent(dados, infer_mime_type(dados), "path")
    if not isinstance(valor, str):
        raise InvalidParameterError(f"`{nome_campo}` must be bytes, a base64 string, or a local file path.")
    path = Path(valor).expanduser()
    if path.exists() and path.is_file():
        dados = read_file_bytes(path, field_name=nome_campo)
        return NormalizedBinaryContent(dados, infer_mime_type(dados), "path")
    if _looks_like_base64(valor):
        dados = base64.b64decode(_strip_base64_prefix(valor))
        return NormalizedBinaryContent(dados, infer_mime_type(dados), "base64")
    raise InvalidParameterError(f"`{nome_campo}` is neither an existing file path nor valid base64.")


def codificar_base64(conteudo: bytes) -> str:
    return base64.b64encode(conteudo).decode("ascii")


def abrir_imagem(conteudo: bytes) -> Image.Image:
    imagem = Image.open(BytesIO(conteudo))
    imagem.load()
    return imagem


def obter_dimensoes_imagem(conteudo: bytes) -> tuple[int, int]:
    return abrir_imagem(conteudo).size


def validar_mascara_compativel(imagem_base: bytes, mascara: bytes) -> None:
    if obter_dimensoes_imagem(imagem_base) != obter_dimensoes_imagem(mascara):
        raise IncompatibleParameterError("Mask and base image must have exactly the same dimensions.")


ConteudoBinarioNormalizado = NormalizedBinaryContent
encode_base64 = codificar_base64
open_image = abrir_imagem
get_image_dimensions = obter_dimensoes_imagem
validate_compatible_mask = validar_mascara_compativel
normalize_binary_input = normalizar_entrada_binaria
