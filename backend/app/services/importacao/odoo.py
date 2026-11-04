from __future__ import annotations
from pathlib import Path
from typing import Any
from openpyxl import load_workbook
from app.services.normalizacao import parse_date, parse_money

ALIASES = {
    "date": ["data", "date", "data do lançamento", "data lançamento"],
    "name": ["parceiro", "partner", "contato", "estabelecimento", "nome"],
    "description": ["rotulo", "label", "descricao", "descrição", "historico", "histórico", "memo"],
    "reference": ["referencia", "referência", "ref", "numero", "número", "number"],
    "debit": ["debito", "débito", "debit"],
    "credit": ["credito", "crédito", "credit"],
    "amount": ["total", "valor", "amount", "saldo", "balance"],
    "company": ["empresa", "company"],
    "kind": ["tipo", "natureza", "movimento", "tipo de lancamento", "tipo lancamento", "kind", "type", "operation"],
}

def _norm(s: object) -> str:
    import unicodedata, re
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()

def import_odoo(path: str | Path, mapping: dict[str, str] | None = None) -> dict[str, Any]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in {".xlsx", ".xlsm"}:
        raise ValueError("Esta versão da API aceita planilhas .xlsx/.xlsm. CSV será habilitado no importador seguinte.")
    wb = load_workbook(path, read_only=True, data_only=True)
    best = None
    for ws in wb.worksheets:
        for header_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row or 40, 40), values_only=True), 1):
            header_labels = [str(v or "").strip() for v in row]
            headers = [_norm(v) for v in row]
            detected: dict[str, int] = {}
            for field, aliases in ALIASES.items():
                for idx, header in enumerate(headers):
                    if not header:
                        continue
                    if any(_norm(alias) == header or _norm(alias) in header for alias in aliases):
                        detected[field] = idx
                        break
            score = sum(1 for x in ("date", "name", "description", "debit", "credit", "amount") if x in detected)
            if best is None or score > best[0]:
                best = (score, ws, header_idx, headers, detected, header_labels)
    if not best or best[0] < 3:
        raise ValueError("Não foi possível identificar uma linha de cabeçalho suficiente na planilha Odoo.")
    _, ws, header_row, headers, detected, header_labels = best
    if mapping:
        # Manual mapping uses exact header labels, never numeric positions from the caller.
        normalized_to_idx = {h: i for i, h in enumerate(headers) if h}
        for field, label in mapping.items():
            idx = normalized_to_idx.get(_norm(label))
            if idx is not None:
                detected[field] = idx
    if "date" not in detected:
        raise ValueError("A coluna de data não foi identificada. Faça o mapeamento manual.")
    rows, errors = [], []
    for excel_row, values in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), header_row + 1):
        if not values or not any(v not in (None, "") for v in values):
            continue
        get = lambda key: values[detected[key]] if key in detected and detected[key] < len(values) else None
        dt = parse_date(get("date"))
        partner = str(get("name") or "").strip()
        description = str(get("description") or "").strip()
        reference = str(get("reference") or "").strip()
        # Prefer explicit debit/credit columns over a generic Total/Valor column.
        # Odoo exports often include both a signed total and separate accounting columns;
        # the debit/credit pair is the clearest source for the transaction's nature.
        debit = parse_money(get("debit")) if "debit" in detected else None
        credit = parse_money(get("credit")) if "credit" in detected else None
        has_accounting_values = bool((debit is not None and debit != 0) or (credit is not None and credit != 0))
        explicit_kind = str(get("kind") or "").strip() if "kind" in detected else ""

        if has_accounting_values:
            debit_abs = abs(debit or 0)
            credit_abs = abs(credit or 0)
            amount = credit_abs - debit_abs
            if debit_abs > 0 and credit_abs == 0:
                kind = "DEBITO"
            elif credit_abs > 0 and debit_abs == 0:
                kind = "CREDITO"
            else:
                # A row with both sides populated requires an analyst to inspect it.
                kind = "INDEFINIDO"
        else:
            amount = parse_money(get("amount")) if "amount" in detected else None
            # A source type/nature column is stronger evidence than the sign of a generic
            # amount. Without it, do not guess whether a positive value is debit or credit.
            kind = explicit_kind or "INDEFINIDO"

        if explicit_kind and has_accounting_values:
            # Preserve the source label only when it agrees with a recognized accounting side.
            normalized_kind = _norm(explicit_kind)
            if any(token in normalized_kind for token in ("credito", "credit", "estorno", "refund")) and kind == "DEBITO":
                kind = "INDEFINIDO"
            elif any(token in normalized_kind for token in ("debito", "debit", "compra", "taxa", "iof")) and kind == "CREDITO":
                kind = "INDEFINIDO"

        if dt is None or amount is None:
            errors.append({"row": excel_row, "reason": "Data ou valor inválido/ausente"})
            continue
        rows.append({"date": dt.isoformat(), "merchant": partner or description or "Sem parceiro informado", "description": description,
                     "reference": reference, "amount": str(amount), "kind": kind,
                     "raw": {str(headers[i] or f"coluna_{i+1}"): str(v) if v is not None else None for i, v in enumerate(values)}})
    unknown = [h for h in headers if h and not any(_norm(a) == h or _norm(a) in h for aliases in ALIASES.values() for a in aliases)]
    wb.close()
    if not rows:
        raise ValueError("Nenhum lançamento válido foi identificado. A importação não foi considerada bem-sucedida.")
    return {"rows": rows, "sheet": ws.title, "header_row": header_row, "detected_columns": detected, "header_labels": header_labels,
            "unknown_columns": unknown, "errors": errors, "imported": len(rows), "ignored": len(errors)}
