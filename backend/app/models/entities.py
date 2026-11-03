from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Integer, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.db.session import Base

def now_utc(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(30), default="ANALISTA")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class ReconciliationRecord(Base):
    __tablename__ = "reconciliations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    bank: Mapped[str] = mapped_column(String(30))
    period_start: Mapped[str | None] = mapped_column(String(10), nullable=True)
    period_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="RASCUNHO")
    tolerance_days: Mapped[int] = mapped_column(Integer, default=3)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ImportFile(Base):
    __tablename__ = "import_files"
    __table_args__ = (UniqueConstraint("sha256", "reconciliation_id", name="uq_file_hash_recon"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int] = mapped_column(ForeignKey("reconciliations.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(String(500))
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="IMPORTADO")
    error_message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class TransactionRecord(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transaction_recon_source", "reconciliation_id", "source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int] = mapped_column(ForeignKey("reconciliations.id", ondelete="CASCADE"))
    import_file_id: Mapped[int] = mapped_column(ForeignKey("import_files.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(20))
    source_row_id: Mapped[str] = mapped_column(String(80))
    transaction_date: Mapped[str] = mapped_column(String(10))
    merchant: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[object] = mapped_column(Numeric(18, 2))
    kind: Mapped[str] = mapped_column(String(30), default="")
    reference: Mapped[str] = mapped_column(String(120), default="")
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)

class MatchRecord(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("invoice_transaction_id", name="uq_match_invoice"),
        UniqueConstraint("odoo_transaction_id", name="uq_match_odoo"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int] = mapped_column(ForeignKey("reconciliations.id", ondelete="CASCADE"))
    invoice_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    odoo_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    difference: Mapped[object | None] = mapped_column(Numeric(18, 2), nullable=True)
    confidence: Mapped[object] = mapped_column(Numeric(5, 4), default=0)
    rule: Mapped[str] = mapped_column(String(180))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliations.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    before_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    justification: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
