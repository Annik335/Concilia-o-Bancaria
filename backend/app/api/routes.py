from __future__ import annotations
import csv, hashlib, io, os, re, uuid, json, tempfile
from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from app.core.config import settings
from app.core.security import create_access_token, get_current_user, require_roles
from app.db.session import get_db
from app.models.entities import User, ReconciliationRecord, ImportFile, TransactionRecord, MatchRecord, AuditLog
from app.schemas.api import DevLoginRequest, ReconciliationCreate, ManualMatchRequest, TransactionUpdateRequest
from app.services.importacao.fatura import import_invoice
from app.services.importacao.odoo import import_odoo
from app.services.conciliacao.motor import Transaction, reconcile, normalized_financial_amount
from app.services.normalizacao import parse_date, parse_money

router = APIRouter(prefix="/api")


def _owned_reconciliation(db: Session, reconciliation_id: int, user: User) -> ReconciliationRecord:
    rec = db.get(ReconciliationRecord, reconciliation_id)
    if not rec or (user.role != "ADMIN" and rec.created_by != user.id):
        raise HTTPException(404, "Conciliação não encontrada.")
    return rec


def _json_decimal(v):
    return str(v) if isinstance(v, Decimal) else v


def _transaction_dict(tx: TransactionRecord | None):
    if tx is None: return None
    return {"id": tx.id, "source": tx.source, "date": tx.transaction_date, "merchant": tx.merchant,
            "description": tx.description, "amount": str(tx.amount), "kind": tx.kind, "reference": tx.reference}


def _match_dict(db: Session, m: MatchRecord):
    f = db.get(TransactionRecord, m.invoice_transaction_id) if m.invoice_transaction_id else None
    o = db.get(TransactionRecord, m.odoo_transaction_id) if m.odoo_transaction_id else None
    return {"id": m.id, "status": m.status, "is_manual": m.is_manual, "difference": str(m.difference) if m.difference is not None else None,
            "confidence": float(m.confidence or 0), "rule": m.rule, "reason": m.reason, "evidence": m.evidence or {},
            "invoice": _transaction_dict(f), "odoo": _transaction_dict(o)}


def _summary(matches: list[MatchRecord], invoice: list[TransactionRecord], odoo: list[TransactionRecord]):
    keys = ["CONCILIADO", "DIVERGENTE", "SOMENTE_ODOO", "SOMENTE_FATURA", "PENDENTE_REVISAO"]
    counts = {k: sum(m.status == k for m in matches) for k in keys}
    # The totals are computed with Decimal from persisted source records.
    total_f = sum((normalized_financial_amount(Decimal(str(t.amount)), t.kind) for t in invoice), Decimal("0.00"))
    total_o = sum((normalized_financial_amount(Decimal(str(t.amount)), t.kind) for t in odoo), Decimal("0.00"))
    matched = sum((normalized_financial_amount(Decimal(str(db_tx.amount)), db_tx.kind) for m in matches if m.status == "CONCILIADO" and m.invoice_transaction_id
                   for db_tx in invoice if db_tx.id == m.invoice_transaction_id), Decimal("0.00"))
<<<<<<< HEAD
    summary = {**counts, "total_fatura": str(total_f), "total_odoo": str(total_o), "valor_conciliado": str(matched),
               "diferenca_fontes": str(total_f - total_o), "total_lancamentos_fatura": len(invoice), "total_lancamentos_odoo": len(odoo),
               "percentual_conciliado": round(100 * counts["CONCILIADO"] / max(1, len(invoice)), 1) if invoice else 0,
               "total_invoice": len(invoice), "total_odoo_count": len(odoo),
               "conciliated": counts["CONCILIADO"], "divergent": counts["DIVERGENTE"],
               "pending": counts["PENDENTE_REVISAO"], "only_invoice": counts["SOMENTE_FATURA"], "only_odoo": counts["SOMENTE_ODOO"]}
    return summary
=======
    return {**counts, "total_fatura": str(total_f), "total_odoo": str(total_o), "valor_conciliado": str(matched),
            "diferenca_fontes": str(total_f - total_o), "total_lancamentos_fatura": len(invoice), "total_lancamentos_odoo": len(odoo),
            "percentual_conciliado": round(100 * counts["CONCILIADO"] / max(1, len(invoice)), 1) if invoice else 0}
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f


def _audit(db: Session, user: User, rec_id: int | None, action: str, entity_type: str, entity_id: str = "",
           before: dict | None = None, after: dict | None = None, justification: str = ""):
    db.add(AuditLog(reconciliation_id=rec_id, user_id=user.id, action=action, entity_type=entity_type,
                    entity_id=entity_id, before_data=before, after_data=after, justification=justification))


@router.get("/health")
def health(): return {"status": "ok", "environment": settings.environment}


@router.post("/auth/dev-login")
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)):
    if settings.auth_mode.lower() != "development":
        raise HTTPException(403, "Login de desenvolvimento desabilitado. Configure a autenticação corporativa antes da implantação.")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        user = User(email=payload.email.lower(), display_name=payload.display_name, role=payload.role)
        db.add(user)
    else:
        user.display_name, user.role, user.active = payload.display_name, payload.role, True
    db.commit(); db.refresh(user)
    return {"access_token": create_access_token(user), "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "name": user.display_name, "role": user.role},
            "warning": "Sessão de desenvolvimento. Não representa autenticação corporativa."}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.display_name, "role": user.role}


@router.post("/reconciliations")
def create_reconciliation(payload: ReconciliationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = ReconciliationRecord(name=payload.name, bank=payload.bank, period_start=payload.period_start,
<<<<<<< HEAD
        period_end=payload.period_end, 
tolerance_days=payload.tolerance_days, 
created_by=user.id
)
=======
        period_end=payload.period_end, tolerance_days=payload.tolerance_days, created_by=user.id)
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
    db.add(rec); db.flush()
    _audit(db, user, rec.id, "CRIAR_CONCILIACAO", "reconciliation", str(rec.id), after={"name":rec.name,"bank":rec.bank})
    db.commit(); db.refresh(rec)
    return {"id": rec.id, "name": rec.name, "bank": rec.bank, "status": rec.status, "tolerance_days": rec.tolerance_days}


def _validate_upload(file: UploadFile, content: bytes, allowed: set[str]):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed: raise HTTPException(415, f"Formato não suportado. Formatos aceitos: {', '.join(sorted(allowed))}.")
    if not content: raise HTTPException(400, "O arquivo está vazio.")
    if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, f"O arquivo excede {settings.max_upload_mb} MB.")
    if ext == ".pdf" and not content.startswith(b"%PDF-"): raise HTTPException(415, "O conteúdo enviado não é um PDF válido.")
    if ext in {".png"} and not content.startswith(b"\x89PNG\r\n\x1a\n"): raise HTTPException(415, "O conteúdo enviado não é uma imagem PNG válida.")
    if ext in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"): raise HTTPException(415, "O conteúdo enviado não é uma imagem JPG válida.")
    if ext in {".xlsx", ".xlsm"} and not content.startswith(b"PK\x03\x04"): raise HTTPException(415, "O conteúdo enviado não é uma planilha Excel válida.")
    return ext


async def _store_upload(file: UploadFile, reconciliation_id: int, source: str, allowed: set[str], db: Session, user: User, rec: ReconciliationRecord, mapping: dict | None = None):
<<<<<<< HEAD
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"O arquivo excede {settings.max_upload_mb} MB.")
=======
    content = await file.read()
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
    ext = _validate_upload(file, content, allowed)
    digest = hashlib.sha256(content).hexdigest()
    duplicate = db.scalar(select(ImportFile).where(ImportFile.reconciliation_id == rec.id, ImportFile.sha256 == digest))
    if duplicate: raise HTTPException(409, "Este arquivo já foi importado nesta conciliação.")
    base_dir = Path(settings.storage_path).resolve() / f"reconciliation_{rec.id}"
    base_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file.filename or f"upload{ext}").name)[:180]
    stored_path = base_dir / f"{uuid.uuid4().hex}_{safe_name}"
    stored_path.write_bytes(content)
    imp = ImportFile(reconciliation_id=rec.id, source=source, filename=safe_name, sha256=digest, path=str(stored_path), status="PROCESSANDO")
    db.add(imp); db.flush()
    try:
        year_base = int(rec.period_start[:4]) if rec.period_start else None
        parsed = import_invoice(stored_path, rec.bank.lower(), year_base=year_base) if source == "FATURA" else import_odoo(stored_path, mapping=mapping)
        imp.imported_count = len(parsed["rows"]); imp.status = "IMPORTADO"
        imp.metadata_json = {k:v for k,v in parsed.items() if k != "rows"}
        for idx, row in enumerate(parsed["rows"], 1):
            db.add(TransactionRecord(reconciliation_id=rec.id, import_file_id=imp.id, source=source,
                source_row_id=str(idx), transaction_date=row["date"], merchant=(row.get("merchant") or "").strip()[:255] or "Sem nome informado",
                description=row.get("description", ""), amount=Decimal(str(row["amount"])), kind=row.get("kind", ""),
                reference=row.get("reference", ""), raw_data=row.get("raw", {})))
        _audit(db, user, rec.id, "IMPORTAR_ARQUIVO", "import_file", str(imp.id), after={"source":source,"filename":safe_name,"count":imp.imported_count})
        db.commit(); db.refresh(imp)
        return {"import_id": imp.id, "filename": imp.filename, "source": source, "imported": imp.imported_count,
                "status": imp.status, "metadata": imp.metadata_json}
    except Exception as exc:
        imp.status = "FALHA_RECONHECIMENTO"; imp.error_message = str(exc)[:1000]
        _audit(db, user, rec.id, "FALHA_IMPORTACAO", "import_file", str(imp.id), after={"filename":safe_name,"error":imp.error_message})
        db.commit()
        raise HTTPException(422, f"Arquivo armazenado, mas a leitura não foi confirmada: {imp.error_message}")


@router.post("/reconciliations/{reconciliation_id}/imports/invoice")
async def upload_invoice(reconciliation_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    allowed = {".pdf"} if rec.bank == "ITAU" else {".png", ".jpg", ".jpeg"}
    return await _store_upload(file, reconciliation_id, "FATURA", allowed, db, user, rec)


@router.post("/imports/odoo/preview")
async def preview_odoo(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
<<<<<<< HEAD
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"O arquivo excede {settings.max_upload_mb} MB.")
=======
    content = await file.read()
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
    ext = _validate_upload(file, content, {".xlsx", ".xlsm"})
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp:
            temp.write(content); temp_path = temp.name
        parsed = import_odoo(temp_path)
        headers = [h or f"Coluna {i+1}" for i,h in enumerate(parsed.get("header_labels", []))]
        suggestions = {field: headers[idx] for field,idx in parsed.get("detected_columns", {}).items() if idx < len(headers) and headers[idx]}
        return {"sheet":parsed["sheet"],"header_row":parsed["header_row"],"columns":headers,
                "suggested_mapping":suggestions,"unknown_columns":parsed["unknown_columns"],
                "sample":parsed["rows"][:5],"total_detected":parsed["imported"],"ignored":parsed["ignored"]}
    except Exception as exc:
        raise HTTPException(422, f"Não foi possível analisar a estrutura do Excel: {str(exc)[:800]}")
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)


@router.post("/reconciliations/{reconciliation_id}/imports/odoo")
async def upload_odoo(reconciliation_id: int, file: UploadFile = File(...), mapping_json: str | None = Form(default=None), db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    mapping = None
    if mapping_json:
        try: mapping = json.loads(mapping_json)
        except json.JSONDecodeError: raise HTTPException(422, "Mapeamento manual inválido.")
<<<<<<< HEAD
        allowed_fields = {"date","name","description","reference","debit","credit","amount","company","kind"}
=======
        allowed_fields = {"date","name","description","reference","debit","credit","amount","company"}
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
        if not isinstance(mapping,dict) or set(mapping)-allowed_fields:
            raise HTTPException(422, "O mapeamento contém campos não reconhecidos.")
    return await _store_upload(file, reconciliation_id, "ODOO", {".xlsx", ".xlsm"}, db, user, rec, mapping=mapping)


@router.post("/reconciliations/{reconciliation_id}/process")
def process_reconciliation(reconciliation_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    invoice_rows = list(db.scalars(select(TransactionRecord).where(TransactionRecord.reconciliation_id == rec.id, TransactionRecord.source == "FATURA").order_by(TransactionRecord.id)))
    odoo_rows = list(db.scalars(select(TransactionRecord).where(TransactionRecord.reconciliation_id == rec.id, TransactionRecord.source == "ODOO").order_by(TransactionRecord.id)))
    if not invoice_rows or not odoo_rows:
        raise HTTPException(409, "Importe a fatura e a planilha Odoo antes de executar a conciliação.")
    # Keep analyst-confirmed associations; re-evaluate only automatic results.
    manual = list(db.scalars(select(MatchRecord).where(MatchRecord.reconciliation_id == rec.id, MatchRecord.is_manual == True)))
    reserved_f = {m.invoice_transaction_id for m in manual if m.invoice_transaction_id}
    reserved_o = {m.odoo_transaction_id for m in manual if m.odoo_transaction_id}
    invoice_available = [t for t in invoice_rows if t.id not in reserved_f]
    odoo_available = [t for t in odoo_rows if t.id not in reserved_o]
    db.execute(delete(MatchRecord).where(MatchRecord.reconciliation_id == rec.id, MatchRecord.is_manual == False))
    tx_f = [Transaction(str(t.id), date.fromisoformat(t.transaction_date), t.merchant, Decimal(str(t.amount)), t.description, t.reference, t.kind, t.raw_data or {}) for t in invoice_available]
    tx_o = [Transaction(str(t.id), date.fromisoformat(t.transaction_date), t.merchant, Decimal(str(t.amount)), t.description, t.reference, t.kind, t.raw_data or {}) for t in odoo_available]
    result = reconcile(tx_f, tx_o, tolerance_days=rec.tolerance_days)
    for match in result.matches:
        db.add(MatchRecord(reconciliation_id=rec.id, invoice_transaction_id=int(match.invoice.id) if match.invoice else None,
            odoo_transaction_id=int(match.odoo.id) if match.odoo else None, status=match.status, is_manual=False,
            difference=match.difference, confidence=Decimal(str(round(match.confidence,4))), rule=match.rule,
            reason=match.reason, evidence=match.evidence))
    rec.status = "PROCESSADA"; rec.processed_at = datetime.now(timezone.utc)
    _audit(db, user, rec.id, "EXECUTAR_CONCILIACAO", "reconciliation", str(rec.id), after={"matches":len(result.matches),"summary":result.summary})
    db.commit()
    return {"reconciliation_id": rec.id, "status": rec.status, "summary": get_summary(db, rec.id), "results": result.summary}


def get_summary(db: Session, reconciliation_id: int):
    invoice = list(db.scalars(select(TransactionRecord).where(TransactionRecord.reconciliation_id == reconciliation_id, TransactionRecord.source == "FATURA")))
    odoo = list(db.scalars(select(TransactionRecord).where(TransactionRecord.reconciliation_id == reconciliation_id, TransactionRecord.source == "ODOO")))
    matches = list(db.scalars(select(MatchRecord).where(MatchRecord.reconciliation_id == reconciliation_id)))
    return _summary(matches, invoice, odoo)


@router.get("/reconciliations")
def list_reconciliations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ReconciliationRecord).order_by(ReconciliationRecord.created_at.desc())
    if user.role != "ADMIN": stmt = stmt.where(ReconciliationRecord.created_by == user.id)
    rows = list(db.scalars(stmt))
    return [{"id":r.id,"name":r.name,"bank":r.bank,"status":r.status,"created_at":r.created_at.isoformat(),"period_start":r.period_start,
             "period_end":r.period_end,"tolerance_days":r.tolerance_days,"summary":get_summary(db,r.id)} for r in rows]


@router.get("/reconciliations/{reconciliation_id}")
def get_reconciliation(reconciliation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    imports = list(db.scalars(select(ImportFile).where(ImportFile.reconciliation_id == rec.id).order_by(ImportFile.id)))
    matches = list(db.scalars(select(MatchRecord).where(MatchRecord.reconciliation_id == rec.id).order_by(MatchRecord.id)))
    invoice = list(db.scalars(select(TransactionRecord).where(TransactionRecord.reconciliation_id == rec.id, TransactionRecord.source == "FATURA")))
    odoo = list(db.scalars(select(TransactionRecord).where(TransactionRecord.reconciliation_id == rec.id, TransactionRecord.source == "ODOO")))
    return {"id":rec.id,"name":rec.name,"bank":rec.bank,"status":rec.status,"period_start":rec.period_start,"period_end":rec.period_end,
            "tolerance_days":rec.tolerance_days,"created_at":rec.created_at.isoformat(),"processed_at":rec.processed_at.isoformat() if rec.processed_at else None,
            "summary":_summary(matches,invoice,odoo),"imports":[{"id":i.id,"filename":i.filename,"source":i.source,"status":i.status,"imported_count":i.imported_count,
            "error_message":i.error_message,"metadata":i.metadata_json} for i in imports], "transactions":{"invoice":[_transaction_dict(t) for t in invoice],"odoo":[_transaction_dict(t) for t in odoo]}, "results":[_match_dict(db,m) for m in matches]}


@router.patch("/reconciliations/{reconciliation_id}/transactions/{transaction_id}")
def update_imported_transaction(reconciliation_id: int, transaction_id: int, payload: TransactionUpdateRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    if rec.status == "PROCESSADA":
        raise HTTPException(409, "Para preservar a rastreabilidade, os dados importados não podem ser alterados após a conciliação. Desfaça/registre uma revisão antes de reimportar.")
    tx = db.get(TransactionRecord, transaction_id)
    if not tx or tx.reconciliation_id != rec.id:
        raise HTTPException(404, "Lançamento não encontrado nesta conciliação.")
    before = _transaction_dict(tx)
    if payload.transaction_date is not None:
        parsed_date = parse_date(payload.transaction_date)
        if parsed_date is None: raise HTTPException(422, "Data inválida. Use DD/MM/AAAA ou AAAA-MM-DD.")
        tx.transaction_date = parsed_date.isoformat()
    if payload.merchant is not None:
        if not payload.merchant.strip(): raise HTTPException(422, "Informe o nome do estabelecimento/parceiro.")
        tx.merchant = payload.merchant.strip()[:255]
    if payload.description is not None: tx.description = payload.description.strip()[:2000]
    if payload.amount is not None:
        parsed_amount = parse_money(payload.amount)
        if parsed_amount is None: raise HTTPException(422, "Valor monetário inválido.")
        tx.amount = parsed_amount
    if payload.kind is not None: tx.kind = payload.kind.strip()[:30]
    if payload.reference is not None: tx.reference = payload.reference.strip()[:120]
    after = _transaction_dict(tx)
    _audit(db,user,rec.id,"REVISAR_LANCAMENTO_IMPORTADO","transaction",str(tx.id),before=before,after=after,justification=payload.justification)
    db.commit(); db.refresh(tx)
    return _transaction_dict(tx)


@router.post("/reconciliations/{reconciliation_id}/matches/manual")
def manual_match(reconciliation_id: int, payload: ManualMatchRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    f = db.get(TransactionRecord, payload.invoice_transaction_id); o = db.get(TransactionRecord, payload.odoo_transaction_id)
    if not f or not o or f.reconciliation_id != rec.id or o.reconciliation_id != rec.id or f.source != "FATURA" or o.source != "ODOO":
        raise HTTPException(422, "Selecione um lançamento da fatura e um lançamento do Odoo desta conciliação.")
    occupied = list(db.scalars(select(MatchRecord).where(MatchRecord.reconciliation_id == rec.id,
        ((MatchRecord.invoice_transaction_id == f.id) | (MatchRecord.odoo_transaction_id == o.id)))))
    for previous in occupied:
        if previous.status not in {"SOMENTE_FATURA", "SOMENTE_ODOO", "PENDENTE_REVISAO"}:
            raise HTTPException(409, "Um dos lançamentos já está associado a um resultado confirmado. Desfaça essa associação primeiro.")
    for previous in occupied:
        _audit(db,user,rec.id,"SUBSTITUIR_PENDENCIA_POR_ASSOCIACAO_MANUAL","match",str(previous.id),
               before=_match_dict(db,previous),justification=payload.justification)
        db.delete(previous)
    if occupied: db.flush()
<<<<<<< HEAD
    difference = (normalized_financial_amount(Decimal(str(f.amount)), f.kind) -
                  normalized_financial_amount(Decimal(str(o.amount)), o.kind)).quantize(Decimal("0.01"))
    if payload.status == "CONCILIADO":
        if difference != 0:
            raise HTTPException(422, "Não é possível confirmar como conciliado: os valores financeiros normalizados são diferentes.")
        def group(kind: str):
            value=(kind or "").upper()
            if any(x in value for x in ("ESTORNO","CREDITO","CRÉDITO","CREDIT")): return "CREDITO"
            if any(x in value for x in ("COMPRA","DEBITO","DÉBITO","DEBIT","IOF","TAXA","ENCARGO","FEE")): return "DEBITO"
=======
    difference = (abs(Decimal(str(f.amount))) - abs(Decimal(str(o.amount)))).quantize(Decimal("0.01"))
    if payload.status == "CONCILIADO":
        if difference != 0:
            raise HTTPException(422, "Não é possível confirmar como conciliado: os valores absolutos são diferentes.")
        def group(kind: str):
            value=(kind or "").upper()
            if any(x in value for x in ("ESTORNO","CREDITO","CRÉDITO","CREDIT")): return "CREDITO"
            if any(x in value for x in ("COMPRA","DEBITO","DÉBITO","DEBIT")): return "DEBITO"
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
            return None
        gf,go=group(f.kind),group(o.kind)
        if gf and go and gf != go:
            raise HTTPException(422, "A natureza do lançamento não é compatível. Registre como divergente ou revise os dados.")
    m = MatchRecord(reconciliation_id=rec.id, invoice_transaction_id=f.id, odoo_transaction_id=o.id,
        status=payload.status, is_manual=True, difference=difference, confidence=Decimal("1.0000"), rule="Associação manual",
        reason="Associação confirmada por usuário. Justificativa registrada na auditoria.", evidence={"manual":True})
    db.add(m); db.flush()
    _audit(db,user,rec.id,"ASSOCIAR_MANUALMENTE","match",str(m.id),after={"invoice_id":f.id,"odoo_id":o.id,"status":m.status},justification=payload.justification)
    db.commit(); db.refresh(m)
    return _match_dict(db,m)


@router.delete("/reconciliations/{reconciliation_id}/matches/{match_id}")
def undo_match(reconciliation_id: int, match_id: int, justification: str, db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "ANALISTA"))):
    rec = _owned_reconciliation(db, reconciliation_id, user)
    if len(justification.strip()) < 8: raise HTTPException(422, "Informe uma justificativa com pelo menos 8 caracteres.")
    m = db.scalar(select(MatchRecord).where(MatchRecord.id == match_id, MatchRecord.reconciliation_id == rec.id))
    if not m: raise HTTPException(404, "Resultado não encontrado.")
    before = _match_dict(db,m)
    _audit(db,user,rec.id,"DESFAZER_ASSOCIACAO","match",str(m.id),before=before,justification=justification)
    db.delete(m); db.commit()
    return {"status":"REMOVIDO","message":"Associação removida e registrada na auditoria."}


@router.get("/audit")
def audit_logs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(300)
    if user.role != "ADMIN": stmt = stmt.where(AuditLog.user_id == user.id)
    return [{"id":a.id,"reconciliation_id":a.reconciliation_id,"user_id":a.user_id,"action":a.action,"entity_type":a.entity_type,
             "entity_id":a.entity_id,"justification":a.justification,"created_at":a.created_at.isoformat()} for a in db.scalars(stmt)]


@router.get("/reconciliations/{reconciliation_id}/export")
def export_reconciliation(reconciliation_id: int, format: str = "xlsx", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = _owned_reconciliation(db,reconciliation_id,user)
    data = get_reconciliation(reconciliation_id,db,user)
    results = data["results"]
    fmt = format.lower()
    if fmt == "csv":
        out=io.StringIO(); w=csv.writer(out,delimiter=";")
        w.writerow(["Status","Data fatura","Estabelecimento fatura","Valor fatura","Data Odoo","Parceiro Odoo","Valor Odoo","Diferença","Regra","Motivo"])
        for r in results:
            f,o=r["invoice"],r["odoo"]
            w.writerow([r["status"],f and f["date"],f and f["merchant"],f and f["amount"],o and o["date"],o and o["merchant"],o and o["amount"],r["difference"],r["rule"],r["reason"]])
        return StreamingResponse(iter(["\ufeff"+out.getvalue()]),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":f'attachment; filename="conciliacao_{rec.id}.csv"'})
    if fmt == "xlsx":
        wb=Workbook(); ws=wb.active; ws.title="Resultados"
        ws.append(["Identificação",rec.name]); ws.append(["Banco",rec.bank]); ws.append(["Período",f"{rec.period_start or ''} a {rec.period_end or ''}"])
        ws.append([]); ws.append(["Indicador","Valor"])
        for k,v in data["summary"].items(): ws.append([k,v])
        ws2=wb.create_sheet("Lançamentos"); ws2.append(["Status","Data fatura","Estabelecimento fatura","Valor fatura","Data Odoo","Parceiro Odoo","Valor Odoo","Diferença","Regra","Motivo"])
        for r in results:
            f,o=r["invoice"],r["odoo"]
            ws2.append([r["status"],f and f["date"],f and f["merchant"],f and float(f["amount"]),o and o["date"],o and o["merchant"],o and float(o["amount"]),float(r["difference"]) if r["difference"] else None,r["rule"],r["reason"]])
        bio=io.BytesIO(); wb.save(bio); bio.seek(0)
        return StreamingResponse(bio,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="conciliacao_{rec.id}.xlsx"'})
    if fmt == "pdf":
        bio=io.BytesIO(); c=canvas.Canvas(bio,pagesize=landscape(A4)); width,height=landscape(A4)
        c.setTitle(f"Conciliação {rec.name}"); c.setFont("Helvetica-Bold",16); c.drawString(36,height-40,"Grupo EPA | Relatório de Conciliação")
        c.setFont("Helvetica",10); c.drawString(36,height-60,f"{rec.name} • {rec.bank} • Processamento: {rec.processed_at or 'não processada'}")
        y=height-95
        for key,val in data["summary"].items():
            c.drawString(40,y,f"{key}: {val}"); y-=16
            if y<50: c.showPage(); y=height-40
        y-=10; c.setFont("Helvetica-Bold",9); c.drawString(40,y,"STATUS | DATA FATURA | ESTABELECIMENTO | VALOR FATURA | DATA ODOO | PARCEIRO | VALOR ODOO | DIFERENÇA"); y-=18
        c.setFont("Helvetica",8)
        for r in results:
            f,o=r["invoice"],r["odoo"]
            line=f"{r['status']} | {f and f['date'] or '-'} | {f and f['merchant'] or '-'} | {f and f['amount'] or '-'} | {o and o['date'] or '-'} | {o and o['merchant'] or '-'} | {o and o['amount'] or '-'} | {r['difference'] or '-'}"
            c.drawString(40,y,line[:180]); y-=13
            if y<35: c.showPage(); y=height-40; c.setFont("Helvetica",8)
        c.save(); bio.seek(0)
        return StreamingResponse(bio,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="conciliacao_{rec.id}.pdf"'})
    raise HTTPException(400,"Formato de exportação inválido. Use xlsx, csv ou pdf.")
