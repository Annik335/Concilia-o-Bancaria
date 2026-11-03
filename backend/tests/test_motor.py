from datetime import date
from decimal import Decimal
from app.services.conciliacao.motor import Transaction, reconcile

def tx(i,day,name,amount,kind=""):
    return Transaction(str(i),date.fromisoformat(day),name,Decimal(amount),name,"",kind,{})

def test_exact_unique_match():
    r=reconcile([tx(1,"2026-10-01","Mercado Central", "120.00","COMPRA")],
                [tx(2,"2026-10-02","Mercado Central Ltda", "-120.00","DEBITO")],3)
    assert r.summary["CONCILIADO"] == 1
    assert r.summary["DIVERGENTE"] == 0

def test_value_difference_is_divergence_not_match():
    r=reconcile([tx(1,"2026-10-01","Mercado Central", "120.00","COMPRA")],
                [tx(2,"2026-10-01","Mercado Central", "-125.00","DEBITO")],3)
    assert r.summary["DIVERGENTE"] == 1
    assert r.summary["CONCILIADO"] == 0

def test_date_outside_tolerance_is_not_matched():
    r=reconcile([tx(1,"2026-10-01","Mercado Central", "120.00","COMPRA")],
                [tx(2,"2026-10-05","Mercado Central", "-120.00","DEBITO")],3)
    assert r.summary["CONCILIADO"] == 0
    assert r.summary["SOMENTE_FATURA"] == 1
    assert r.summary["SOMENTE_ODOO"] == 1

def test_same_item_never_used_twice_and_ambiguity_pending():
    inv=[tx(1,"2026-10-01","Mercado Central", "120.00","COMPRA")]
    od=[tx(2,"2026-10-01","Mercado Central", "-120.00","DEBITO"),tx(3,"2026-10-01","Mercado Central", "-120.00","DEBITO")]
    r=reconcile(inv,od,3)
    assert r.summary["CONCILIADO"] == 0
    assert r.summary["PENDENTE_REVISAO"] >= 1
    used_f=[m.invoice.id for m in r.matches if m.invoice]
    assert len(used_f)==len(set(used_f))

def test_reference_can_support_match():
    a=tx(1,"2026-10-01","", "50.00","COMPRA");b=tx(2,"2026-10-02","", "-50.00","DEBITO")
    a.reference=b.reference="REF-001"
    r=reconcile([a],[b],3)
    assert r.summary["CONCILIADO"] == 1

def test_weak_unique_candidate_stays_pending():
    r=reconcile([tx(1,"2026-10-01","MERCADO ABCDEF", "100.00","COMPRA")],
                [tx(2,"2026-10-01","MERCADO ABXYZF", "-100.00","DEBITO")],3)
    assert r.summary["PENDENTE_REVISAO"] == 1
    assert r.summary["CONCILIADO"] == 0
    assert r.matches[0].invoice is not None and r.matches[0].odoo is not None

def test_business_totals_normalize_debit_credit_conventions():
    from app.services.conciliacao.motor import normalized_financial_amount
    assert normalized_financial_amount(Decimal("120.00"),"COMPRA") == Decimal("120.00")
    assert normalized_financial_amount(Decimal("-120.00"),"DEBITO") == Decimal("120.00")
    assert normalized_financial_amount(Decimal("15.00"),"ESTORNO") == Decimal("-15.00")
