from __future__ import annotations
from pathlib import Path
from datetime import date
from decimal import Decimal
import re
import uuid
import fitz
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from app.services.normalizacao import parse_date, parse_money, normalize_text

DATE_RE = re.compile(r"(?<!\d)(\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?|\d{4}-\d{2}-\d{2})(?!\d)")
MONEY_RE = re.compile(r"(?<![\w])(?:R\$\s*)?(?:\(?-?\s*(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}\)?-?|\(?-?\s*\d{1,3}(?:,\d{3})+\.\d{2}\)?-?)(?!\w)")

def _ocr_languages() -> str:
    """Use Brazilian Portuguese + English when available; otherwise degrade to English."""
    try:
        languages = set(pytesseract.get_languages(config=""))
    except Exception as exc:
        raise RuntimeError("Tesseract OCR não está instalado ou configurado neste ambiente.") from exc
    if "por" in languages and "eng" in languages:
        return "por+eng"
    if "eng" in languages:
        return "eng"
    if "por" in languages:
        return "por"
    raise RuntimeError("O Tesseract não possui pacote de idioma português nem inglês instalado.")


def _clean_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("L")
    # Upscale small images; do not crop or alter the original stored upload.
    if image.width < 1800:
        ratio = 1800 / image.width
        image = image.resize((1800, int(image.height * ratio)))
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.35)
    return image.filter(ImageFilter.SHARPEN)

def _extract_rows(text: str, year_base: int | None = None) -> tuple[list[dict], list[str]]:
    year_base = year_base or date.today().year
    rows, ignored = [], []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 8:
            continue
        dm = DATE_RE.search(line)
        amounts = list(MONEY_RE.finditer(line))
        if not dm or not amounts:
            if re.search(r"\d{1,2}[/.]\d{1,2}", line) and len(ignored) < 300:
                ignored.append(line[:240])
            continue
        # Select the last financial token: statement rows commonly put values at the end.
        am = amounts[-1]
        raw_date = dm.group(1)
        if re.fullmatch(r"\d{1,2}[/.\-]\d{1,2}", raw_date):
            raw_date = f"{raw_date}/{year_base}"
        dt = parse_date(raw_date)
        amount = parse_money(am.group(0))
        desc = (line[:dm.start()] + " " + line[dm.end():am.start()]).strip(" -|·")
        desc = re.sub(r"\s+", " ", desc).strip()
        if dt is None or amount is None or not desc:
            if len(ignored) < 300:
                ignored.append(line[:240])
            continue
        normalized = normalize_text(desc)
        if any(x in normalized for x in ["total da fatura", "pagamento minimo", "vencimento", "melhor dia", "limite disponivel", "resumo da fatura"]):
            continue
        kind = "ESTORNO" if any(x in normalized for x in ["estorno", "cancelamento", "credito", "anuidade diferenci"]) else ("DEBITO" if amount < 0 else "COMPRA")
        rows.append({"date": dt.isoformat(), "merchant": desc, "description": desc, "reference": "", "amount": str(amount), "kind": kind,
                     "raw": {"source_line": line}})
    return rows, ignored

def import_invoice(path: str | Path, bank: str, year_base: int | None = None) -> dict:
    path = Path(path)
    ext = path.suffix.lower()
    if bank.lower() == "itau" and ext != ".pdf":
        raise ValueError("Para Itaú, envie uma fatura em PDF.")
    if bank.lower() == "santander" and ext not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("Para Santander, envie uma imagem PNG ou JPG.")
    if ext == ".pdf":
        doc = fitz.open(path)
        all_text, ocr_pages = [], []
        try:
            for page_no, page in enumerate(doc, 1):
                text = page.get_text("text", sort=True).strip()
                native_rows = len(DATE_RE.findall(text)) if text else 0
                if len(text) < 30 or (native_rows == 0 and len(text) < 200):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    import io
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    text = pytesseract.image_to_string(_clean_image(img), lang=_ocr_languages(), config="--psm 6")
                    ocr_pages.append(page_no)
                all_text.append(f"\n{text}")
        finally:
            page_count = len(doc)
            doc.close()
        source_text = "\n".join(all_text)
    elif ext in {".png", ".jpg", ".jpeg"}:
        with Image.open(path) as img:
            source_text = pytesseract.image_to_string(_clean_image(img), lang=_ocr_languages(), config="--psm 6")
        page_count, ocr_pages = 1, [1]
    else:
        raise ValueError("Formato de fatura não suportado.")
    rows, ignored = _extract_rows(source_text, year_base)
    if not rows:
        raise ValueError("Nenhum lançamento foi reconhecido com segurança. Confira o arquivo; a importação não foi confirmada.")
    return {"rows": rows, "page_count": page_count, "ocr_pages": ocr_pages, "ignored_lines": ignored,
            "source_text_chars": len(source_text), "imported": len(rows), "ignored": len(ignored)}
