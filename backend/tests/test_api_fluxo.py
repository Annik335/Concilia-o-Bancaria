from pathlib import Path
import fitz
from fastapi.testclient import TestClient
from openpyxl import Workbook
from app.main import app
from app.db.session import Base, engine
from app.core.config import settings


def test_reconciliation_works_without_auth_in_development_mode(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "integration-test-secret-key-long-enough")
    monkeypatch.setattr(settings, "auth_mode", "development")
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        response = client.post("/api/reconciliations", json={"name": "Sem login", "bank": "ITAU", "tolerance_days": 3})
        assert response.status_code == 200, response.text
        assert response.json()["bank"] == "ITAU"
    Base.metadata.drop_all(bind=engine)


def test_create_import_process_manual_audit_export_and_reprocess(tmp_path, monkeypatch):
    monkeypatch.setattr(settings,"secret_key","integration-test-secret-key-long-enough")
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        login=client.post("/api/auth/dev-login",json={"email":"test@grupoepa.local","display_name":"Teste API","role":"ANALISTA"})
        assert login.status_code==200, login.text
        headers={"Authorization":f"Bearer {login.json()['access_token']}"}
        created=client.post("/api/reconciliations",headers=headers,json={"name":"Teste API Itaú","bank":"ITAU","tolerance_days":3})
        assert created.status_code==200, created.text
        rid=created.json()["id"]

        pdf=tmp_path/"invoice.pdf"; doc=fitz.open(); page=doc.new_page()
        page.insert_text((45,80),"01/10/2026 MERCADO CENTRAL 120,00\n02/10/2026 POSTO CENTRAL 80,50\n10/10/2026 MERCADO LESTE 50,00",fontsize=12)
        doc.save(pdf); doc.close()
        with pdf.open("rb") as f:
            inv=client.post(f"/api/reconciliations/{rid}/imports/invoice",headers=headers,files={"file":("invoice.pdf",f,"application/pdf")})
        assert inv.status_code==200, inv.text
        assert inv.json()["imported"]==3

        xlsx=tmp_path/"odoo.xlsx"; wb=Workbook(); ws=wb.active
        ws.append(["Data","Parceiro","Rótulo","Débito","Crédito"])
        ws.append(["01/10/2026","Mercado Central","Compra cartão",120.0,0])
        ws.append(["02/10/2026","Posto Central","Abastecimento",80.5,0])
        ws.append(["20/10/2026","Mercado Leste","Compra",50.0,0])
        wb.save(xlsx)
        with xlsx.open("rb") as f:
            preview=client.post("/api/imports/odoo/preview",headers=headers,files={"file":("odoo.xlsx",f,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert preview.status_code==200, preview.text
        assert preview.json()["suggested_mapping"]["date"]=="Data"
        with xlsx.open("rb") as f:
            od=client.post(f"/api/reconciliations/{rid}/imports/odoo",headers=headers,files={"file":("odoo.xlsx",f,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert od.status_code==200, od.text
        before_process=client.get(f"/api/reconciliations/{rid}",headers=headers).json()
        invoice_id=before_process["transactions"]["invoice"][0]["id"]
        reviewed=client.patch(f"/api/reconciliations/{rid}/transactions/{invoice_id}",headers=headers,json={
            "merchant":"Mercado Central","amount":"120,00","justification":"Conferido com o arquivo bancário original."})
        assert reviewed.status_code==200, reviewed.text
        processed=client.post(f"/api/reconciliations/{rid}/process",headers=headers)
        assert processed.status_code==200, processed.text
        detail=client.get(f"/api/reconciliations/{rid}",headers=headers).json()
        assert detail["summary"]["CONCILIADO"]==2
        assert detail["summary"]["total_fatura"]==detail["summary"]["total_odoo"]
        only_f=next(x for x in detail["results"] if x["status"]=="SOMENTE_FATURA")
        only_o=next(x for x in detail["results"] if x["status"]=="SOMENTE_ODOO")
        manual=client.post(f"/api/reconciliations/{rid}/matches/manual",headers=headers,json={
            "invoice_transaction_id":only_f["invoice"]["id"],"odoo_transaction_id":only_o["odoo"]["id"],
            "status":"CONCILIADO","justification":"Correspondência conferida na documentação original."})
        assert manual.status_code==200, manual.text
        assert manual.json()["is_manual"] is True

        # Reprocessing preserves the reviewed manual match and replaces only automatic results.
        again=client.post(f"/api/reconciliations/{rid}/process",headers=headers)
        assert again.status_code==200, again.text
        detail=client.get(f"/api/reconciliations/{rid}",headers=headers).json()
        assert detail["summary"]["CONCILIADO"]==3
        assert len(detail["results"])==3
        manual_id=next(x["id"] for x in detail["results"] if x["is_manual"])
        undone=client.delete(f"/api/reconciliations/{rid}/matches/{manual_id}?justification=Revisao%20solicitada%20pelo%20analista",headers=headers)
        assert undone.status_code==200, undone.text
        assert client.get("/api/audit",headers=headers).status_code==200
        export=client.get(f"/api/reconciliations/{rid}/export?format=xlsx",headers=headers)
        assert export.status_code==200 and "spreadsheet" in export.headers["content-type"]
        duplicate=client.post(f"/api/reconciliations/{rid}/imports/odoo",headers=headers,files={"file":("odoo.xlsx",xlsx.read_bytes(),"application/octet-stream")})
        assert duplicate.status_code==409
    Base.metadata.drop_all(bind=engine)
