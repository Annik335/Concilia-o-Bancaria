from pathlib import Path
import pytest
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from app.services.importacao.fatura import import_invoice


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def test_santander_png_ocr_extracts_rows(tmp_path: Path):
    try:
        languages = set(pytesseract.get_languages(config=""))
    except Exception:
        pytest.skip("Tesseract OCR não instalado no ambiente de teste")
    if not ({"eng", "por"} & languages):
        pytest.skip("Pacotes de idioma OCR não instalados no ambiente de teste")

    image = Image.new("RGB", (2600, 700), "white")
    draw = ImageDraw.Draw(image)
    font = _font(76)
    draw.text((90, 120), "01/10/2026   MERCADO CENTRAL   120,00", fill="black", font=font)
    draw.text((90, 350), "02/10/2026   POSTO CENTRAL   80,50", fill="black", font=font)
    path = tmp_path / "santander.png"
    image.save(path)

    result = import_invoice(path, "santander", year_base=2026)
    assert result["imported"] == 2
    assert result["rows"][0]["date"] == "2026-10-01"
    assert result["rows"][0]["amount"] == "120.00"
    assert result["rows"][1]["amount"] == "80.50"
