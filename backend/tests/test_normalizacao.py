from decimal import Decimal
from datetime import date
from app.services.normalizacao import parse_money, parse_date, normalize_merchant, text_similarity

def test_parse_brazilian_money():
    assert parse_money("R$ 1.234,56") == Decimal("1234.56")
    assert parse_money("-1.234,56") == Decimal("-1234.56")
    assert parse_money("(1.234,56)") == Decimal("-1234.56")

def test_parse_international_money():
    assert parse_money("1,234.56") == Decimal("1234.56")

def test_parse_dates():
    assert parse_date("03/11/2026") == date(2026,11,3)
    assert parse_date("2026-11-03") == date(2026,11,3)

def test_merchant_normalization():
    assert normalize_merchant("  LOJA  São   João LTDA ") == "sao joao"
    assert text_similarity("POSTO ABC LTDA", "Posto ABC") >= .82
