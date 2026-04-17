import base64
from decimal import Decimal

from multisynth._core.media import infer_mime_type, normalizar_entrada_binaria
from multisynth._core.pricing import TokenUsage, calcular_custo_usd

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WnR0WQAAAAASUVORK5CYII="
)


def test_infer_mime_type_for_png_without_imghdr() -> None:
    assert infer_mime_type(_ONE_PIXEL_PNG) == "image/png"


def test_normalize_binary_input_from_base64() -> None:
    encoded = base64.b64encode(_ONE_PIXEL_PNG).decode("ascii")
    normalized = normalizar_entrada_binaria(encoded, nome_campo="image")
    assert normalized.dados == _ONE_PIXEL_PNG
    assert normalized.mime_type == "image/png"


def test_calculate_text_cost_usd() -> None:
    cost = calcular_custo_usd(
        "openai",
        "gpt-5-mini",
        TokenUsage(prompt_tokens=1000, completion_tokens=500, cached_prompt_tokens=0),
    )
    assert cost == Decimal("0.0012500")
