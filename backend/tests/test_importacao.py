from pathlib import Path
from openpyxl import Workbook
import fitz
from app.services.importacao.odoo import import_odoo
from app.services.importacao.fatura import import_invoice


def test_odoo_header_mapping_by_name(tmp_path: Path):
    path=tmp_path/"odoo.xlsx"
    wb=Workbook(); ws=wb.active; ws.title="Lançamentos"
    ws.append(["Exportação Odoo"])
    ws.append(["Data","Parceiro","Rótulo","Débito","Crédito","Referência","Campo extra"])
    ws.append(["01/10/2026","Mercado Central","Compra cartão",120.0,0,"R-10","X"])
    wb.save(path)
    data=import_odoo(path)
    assert data["imported"]==1
    assert data["rows"][0]["merchant"]=="Mercado Central"
    assert data["rows"][0]["amount"]=="-120.00"
    assert "campo extra" in data["unknown_columns"]


def test_pdf_text_all_pages(tmp_path: Path):
    path=tmp_path/"fatura.pdf"
    doc=fitz.open()
    for line in ["01/10/2026 MERCADO CENTRAL 120,00", "02/10/2026 POSTO CENTRAL 80,50"]:
        page=doc.new_page(); page.insert_text((50,80),line)
    doc.save(path); doc.close()
    data=import_invoice(path,"itau",year_base=2026)
    assert data["page_count"]==2
    assert data["imported"]==2
    assert data["rows"][0]["amount"]=="120.00"


def test_invoice_rejects_wrong_bank_format(tmp_path: Path):
    path=tmp_path/"wrong.xlsx"; path.write_bytes(b"not a real file")
    try:
        import_invoice(path,"itau")
    except ValueError as exc:
        assert "PDF" in str(exc)
    else:
        raise AssertionError("Formato deveria ser rejeitado")
