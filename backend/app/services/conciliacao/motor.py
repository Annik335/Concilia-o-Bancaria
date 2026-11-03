from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from decimal import Decimal
from typing import Any
from app.services.normalizacao import compatible_merchant, text_similarity

@dataclass(slots=True)
class Transaction:
    id: str
    date: date
    merchant: str
    amount: Decimal
    description: str = ""
    reference: str = ""
    kind: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class Match:
    status: str
    invoice: Transaction | None
    odoo: Transaction | None
    difference: Decimal | None
    confidence: float
    rule: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class Reconciliation:
    matches: list[Match]
    summary: dict[str, Any]


def _same_reference(a: Transaction, b: Transaction) -> bool:
    return bool(a.reference and b.reference and a.reference.strip().casefold() == b.reference.strip().casefold())

def _kind_group(tx: Transaction) -> str | None:
    kind = (tx.kind or "").strip().upper()
    if any(token in kind for token in ("ESTORNO", "CREDITO", "CRÉDITO", "CREDIT")):
        return "CREDITO"
    if any(token in kind for token in ("COMPRA", "DEBITO", "DÉBITO", "DEBIT")):
        return "DEBITO"
    return None

def normalized_financial_amount(amount: Decimal, kind: str) -> Decimal:
    """Put debit/credit conventions from bank and Odoo on one economic sign basis."""
    value = (kind or "").strip().upper()
    if any(token in value for token in ("ESTORNO", "CREDITO", "CRÉDITO", "CREDIT")):
        return -abs(amount)
    if any(token in value for token in ("COMPRA", "DEBITO", "DÉBITO", "DEBIT")):
        return abs(amount)
    return amount

def _same_kind(a: Transaction, b: Transaction) -> bool:
    ka, kb = _kind_group(a), _kind_group(b)
    if ka and kb:
        return ka == kb
    if a.amount == 0 or b.amount == 0:
        return True
    return (a.amount > 0) == (b.amount > 0)

def reconcile(invoice: list[Transaction], odoo: list[Transaction], tolerance_days: int = 3, amount_tolerance: Decimal = Decimal("0.00")) -> Reconciliation:
    if tolerance_days < 0 or tolerance_days > 31:
        raise ValueError("A tolerância de data deve estar entre 0 e 31 dias.")
    if amount_tolerance < 0:
        raise ValueError("A tolerância de valor não pode ser negativa.")

    available_f, available_o = set(range(len(invoice))), set(range(len(odoo)))
    matches: list[Match] = []
    candidate_edges: dict[tuple[int, int], dict[str, Any]] = {}

    def evaluate(i: int, j: int) -> dict[str, Any] | None:
        f, o = invoice[i], odoo[j]
        day_gap = abs((f.date - o.date).days)
        reference = _same_reference(f, o)
        name_score = max(text_similarity(f.merchant, o.merchant), text_similarity(f.description, o.merchant))
        name_ok = compatible_merchant(f.merchant or f.description, o.merchant)
        # Compare magnitudes only after transaction nature (debit/credit) is compatible.
        # Original signed values remain intact in the source records and reports.
        value_gap = abs(abs(f.amount) - abs(o.amount))
        value_ok = value_gap <= amount_tolerance
        if day_gap > tolerance_days or not _same_kind(f, o):
            return None
        # Reference can identify the counterpart; otherwise require merchant evidence.
        # We retain weak textual candidates for manual review; similarity alone never auto-matches.
        if not reference and name_score < 0.72:
            return None
        return {"day_gap": day_gap, "reference_match": reference, "name_similarity": round(name_score, 4),
                "merchant_match": name_ok, "amount_gap": str(value_gap), "amount_match": value_ok,
                "date_tolerance_days": tolerance_days, "amount_tolerance": str(amount_tolerance)}

    # Build candidate graph first. No greedy/order-based pairing is permitted.
    for i in available_f:
        for j in available_o:
            ev = evaluate(i, j)
            if ev:
                candidate_edges[(i, j)] = ev

    def neighbors_f(i: int, remaining_o: set[int]) -> list[int]:
        return [j for (fi, j) in candidate_edges if fi == i and j in remaining_o]
    def neighbors_o(j: int, remaining_f: set[int]) -> list[int]:
        return [i for (i, oj) in candidate_edges if oj == j and i in remaining_f]

    # Phase A: auto-match only exact-value, high-evidence, unique reciprocal pairs.
    exact_pairs = []
    for i in sorted(available_f):
        for j in neighbors_f(i, available_o):
            ev = candidate_edges[(i, j)]
            high_evidence = ev["reference_match"] or (ev["merchant_match"] and ev["name_similarity"] >= 0.82)
            if ev["amount_match"] and high_evidence:
                f_candidates = [x for x in available_f if (x, j) in candidate_edges]
                o_candidates = [x for x in available_o if (i, x) in candidate_edges]
                if len(f_candidates) == 1 and len(o_candidates) == 1:
                    exact_pairs.append((i, j))
    for i, j in exact_pairs:
        if i not in available_f or j not in available_o:
            continue
        ev = candidate_edges[(i, j)]
        available_f.remove(i); available_o.remove(j)
        confidence = 0.99 if ev["reference_match"] else min(0.99, 0.90 + ev["name_similarity"] * 0.09)
        rule = "Referência + valor + data" if ev["reference_match"] else "Valor + estabelecimento + data"
        matches.append(Match("CONCILIADO", invoice[i], odoo[j], Decimal("0.00"), confidence, rule,
                             "Valor compatível, data dentro da tolerância e identificação única nos dois sentidos.", ev))

    # Phase B: amount-different but otherwise strong unique counterpart -> divergence.
    # It is never converted into a successful match.
    diverged = []
    for i in sorted(available_f):
        cand = neighbors_f(i, available_o)
        if len(cand) != 1 or candidate_edges[(i, cand[0])]["amount_match"]:
            continue
        j = cand[0]
        reverse = neighbors_o(j, available_f)
        if len(reverse) == 1 and reverse[0] == i:
            ev = candidate_edges[(i, j)]
            # Difference is a candidate only when amount mismatch is the remaining material conflict.
            if ev["reference_match"] or (ev["merchant_match"] and ev["name_similarity"] >= 0.82):
                diverged.append((i, j))
    for i, j in diverged:
        if i not in available_f or j not in available_o:
            continue
        ev = candidate_edges[(i, j)]
        available_f.remove(i); available_o.remove(j)
        diff = (abs(invoice[i].amount) - abs(odoo[j].amount)).quantize(Decimal("0.01"))
        matches.append(Match("DIVERGENTE", invoice[i], odoo[j], diff, 0.88 if ev["reference_match"] else 0.84,
                             "Identificação + data; valor diferente", "Possível contraparte identificada, mas os valores não são iguais.", ev))

    # Phase C: connected candidate components that are not safe to auto-match stay pending.
    # A unique one-to-one candidate is shown together on a single review row.
    remaining_f, remaining_o = set(available_f), set(available_o)
    visited_f: set[int] = set(); visited_o: set[int] = set()
    while True:
        seed_f = next((i for i in sorted(remaining_f) if neighbors_f(i, remaining_o)), None)
        if seed_f is None:
            break
        comp_f: set[int] = set(); comp_o: set[int] = set()
        queue_f, queue_o = [seed_f], []
        while queue_f or queue_o:
            while queue_f:
                i = queue_f.pop()
                if i in comp_f: continue
                comp_f.add(i)
                for j in neighbors_f(i, remaining_o):
                    if j not in comp_o: queue_o.append(j)
            while queue_o:
                j = queue_o.pop()
                if j in comp_o: continue
                comp_o.add(j)
                for i in neighbors_o(j, remaining_f):
                    if i not in comp_f: queue_f.append(i)
        remaining_f -= comp_f; remaining_o -= comp_o
        if len(comp_f) == 1 and len(comp_o) == 1:
            i, j = next(iter(comp_f)), next(iter(comp_o))
            ev = candidate_edges[(i, j)]
            confidence = min(0.75, max(ev["name_similarity"], 0.45))
            matches.append(Match("PENDENTE_REVISAO", invoice[i], odoo[j], None, confidence,
                "Candidato único sem evidência suficiente para conciliação automática",
                "Há uma possível contraparte, mas a identificação não atingiu o nível de segurança exigido. Confirme manualmente.", ev))
        else:
            for i in sorted(comp_f):
                cand = [j for j in neighbors_f(i, comp_o)]
                evidence = [{"odoo_id": odoo[j].id, **candidate_edges[(i, j)]} for j in cand]
                best = max((candidate_edges[(i, j)]["name_similarity"] for j in cand), default=0.0)
                matches.append(Match("PENDENTE_REVISAO", invoice[i], None, None, min(0.75, best),
                    "Múltiplos candidatos", "Há mais de uma associação possível. Revise antes de confirmar.", {"candidates": evidence}))
            for j in sorted(comp_o):
                cand = [i for i in neighbors_o(j, comp_f)]
                evidence = [{"invoice_id": invoice[i].id, **candidate_edges[(i, j)]} for i in cand]
                best = max((candidate_edges[(i, j)]["name_similarity"] for i in cand), default=0.0)
                matches.append(Match("PENDENTE_REVISAO", None, odoo[j], None, min(0.75, best),
                    "Múltiplos candidatos", "Há mais de uma associação possível. Revise antes de confirmar.", {"candidates": evidence}))
    available_f = remaining_f
    available_o = remaining_o

    for i in sorted(available_f):
        matches.append(Match("SOMENTE_FATURA", invoice[i], None, None, 1.0, "Sem correspondência encontrada", "Nenhum lançamento compatível localizado no Odoo.", {}))
    for j in sorted(available_o):
        matches.append(Match("SOMENTE_ODOO", None, odoo[j], None, 1.0, "Sem correspondência encontrada", "Nenhum lançamento compatível localizado na fatura.", {}))

    counts = {key: sum(1 for m in matches if m.status == key) for key in
              ["CONCILIADO", "DIVERGENTE", "SOMENTE_ODOO", "SOMENTE_FATURA", "PENDENTE_REVISAO"]}
    total_f = sum((normalized_financial_amount(t.amount, t.kind) for t in invoice), Decimal("0.00"))
    total_o = sum((normalized_financial_amount(t.amount, t.kind) for t in odoo), Decimal("0.00"))
    total_matched = sum((normalized_financial_amount(m.invoice.amount, m.invoice.kind) for m in matches if m.status == "CONCILIADO" and m.invoice), Decimal("0.00"))
    summary = {**counts, "total_fatura": str(total_f), "total_odoo": str(total_o),
               "diferenca_fontes": str(total_f - total_o), "valor_conciliado": str(total_matched),
               "total_lancamentos_fatura": len(invoice), "total_lancamentos_odoo": len(odoo)}
    return Reconciliation(matches, summary)
