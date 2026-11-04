from pydantic import AliasChoices, BaseModel, Field

class DevLoginRequest(BaseModel):
    email: str = Field(default="analista@grupoepa.local", max_length=255)
    display_name: str = Field(default="Analista de desenvolvimento", max_length=160)
    role: str = Field(default="ANALISTA", pattern="^(ADMIN|ANALISTA|VISUALIZADOR)$")

class ReconciliationCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    bank: str = Field(pattern="^(ITAU|SANTANDER)$")
    period_start: str | None = None
    period_end: str | None = None
    tolerance_days: int = Field(default=3, ge=0, le=60, validation_alias=AliasChoices("tolerance_days", "tolerancia_dias"), description="Tolerância de data em dias")


class ManualMatchRequest(BaseModel):
    invoice_transaction_id: int
    odoo_transaction_id: int
    status: str = Field(default="CONCILIADO", pattern="^(CONCILIADO|DIVERGENTE)$")
    justification: str = Field(min_length=8, max_length=1000)


class TransactionUpdateRequest(BaseModel):
    transaction_date: str | None = None
    merchant: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    amount: str | None = None
    kind: str | None = Field(default=None, max_length=30)
    reference: str | None = Field(default=None, max_length=120)
    justification: str = Field(min_length=8, max_length=1000)
