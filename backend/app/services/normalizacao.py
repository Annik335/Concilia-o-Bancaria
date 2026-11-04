from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
import re
import unicodedata

CENT = Decimal("0.01")

def parse_money(value: object) -> Decimal | None:
    """Parse BRL/recognized international values without binary floats."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
    if isinstance(value, (int, float)):
        # String conversion avoids importing the binary approximation into Decimal.
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    raw = str(value).strip().replace("R$", "").replace("\u00a0", "")
    if not raw or raw in {"-", "—", "–"}:
        return None
    negative = raw.startswith("-") or raw.endswith("-") or (raw.startswith("(") and raw.endswith(")"))
    raw = raw.strip("() ").replace("-", "")
    raw = re.sub(r"[^\d,.]", "", raw)
    if not raw or not re.search(r"\d", raw):
        return None
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "." in raw:
        # Dot is a thousands separator only when exactly 3 digits follow it.
        parts = raw.split(".")
        if len(parts) > 2:
            raw = "".join(parts[:-1]) + "." + parts[-1]
        elif len(parts[-1]) == 3 and len(parts[0]) >= 1:
            raw = raw.replace(".", "")
    try:
        amount = Decimal(raw)
        if negative:
            amount = -amount
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None

def parse_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 1 <= value <= 100000:
        # Excel serial date (1900 date system).
        from datetime import timedelta
        return date(1899, 12, 30) + timedelta(days=int(value))
    raw = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            pass
    # ISO timestamps are accepted only when the year comes first.
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None

def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

LEGAL_TOKENS = {"ltda", "limitada", "sa", "s", "a", "eireli", "me", "epp", "matriz", "filial", "comercio", "servicos", "servico", "de", "do", "da", "e", "para", "brasil", "loja"}

def normalize_merchant(value: object) -> str:
    text = normalize_text(value)
    text = re.sub(r"\b(pg|pay|pgt|cartao|compra|debito|credito)\b", " ", text)
    tokens = [t for t in text.split() if t not in LEGAL_TOKENS]
    return " ".join(tokens)

def text_similarity(a: object, b: object) -> float:
    na, nb = normalize_merchant(a), normalize_merchant(b)
    if not na or not nb:
        return 0.0
    if na == nb or na in nb or nb in na:
        return 1.0
    # Compare strings and meaningful token overlap, but not as a standalone match criterion.
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    overlap = len(ta & tb) / max(1, len(ta | tb))
    return max(seq, overlap)

def compatible_merchant(a: object, b: object, threshold: float = 0.82) -> bool:
    na, nb = normalize_merchant(a), normalize_merchant(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    return text_similarity(a, b) >= threshold
