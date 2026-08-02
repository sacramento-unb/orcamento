import io
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from backend.app import create_app
from backend.bank_import import parse_bank_file


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "SOURCE_SPREADSHEET": str(tmp_path / "missing.ods"),
            "EXPORT_DIR": str(tmp_path / "exports"),
        }
    )
    return app.test_client()


def sample_entry(**overrides):
    entry = {
        "description": "Aluguel",
        "amount": 1800,
        "entry_type": "expense",
        "category": "Moradia",
        "recurring": True,
        "start_month": "2026-07",
        "end_month": None,
        "notes": "",
    }
    entry.update(overrides)
    return entry


def test_create_update_delete_and_export(client):
    created = client.post("/api/entries", json=sample_entry())
    assert created.status_code == 201
    payload = created.get_json()
    assert payload["entry"]["description"] == "Aluguel"
    assert payload["export"]["filename"].endswith(".xlsx")

    entry_id = payload["entry"]["id"]
    updated = client.put(
        f"/api/entries/{entry_id}",
        json=sample_entry(amount=1950, description="Aluguel atualizado"),
    )
    assert updated.status_code == 200
    assert updated.get_json()["entry"]["amount"] == 1950

    summary = client.get("/api/summary?month=2026-07")
    assert summary.status_code == 200
    assert summary.get_json()["expenses"] == 1950

    deleted = client.delete(f"/api/entries/{entry_id}?month=2026-07")
    assert deleted.status_code == 200
    exports = client.get("/api/exports").get_json()
    assert len(exports) == 3

    downloaded = client.get(exports[1]["url"])
    assert downloaded.status_code == 200
    workbook_path = Path(client.application.config["EXPORT_DIR"]) / exports[1]["filename"]
    workbook = load_workbook(workbook_path, read_only=True)
    assert workbook.sheetnames == [
        "Visão geral",
        "Lançamentos",
        "Investimentos",
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    assert workbook["Visão geral"]["A4"].value == "Gastos"
    assert workbook["Julho"]["A1"].value == "Orçamento — Julho de 2026"
    assert workbook["Julho"]["A4"].value == "Aluguel atualizado"


def test_rejects_invalid_entry(client):
    response = client.post("/api/entries", json=sample_entry(amount=-1))
    assert response.status_code == 400
    assert "maior que zero" in response.get_json()["error"]


def test_bank_csv_preview_confirm_and_duplicate_protection(client):
    content = (
        "Data;Descrição;Valor\n"
        "15/07/2026;Supermercado Central;-245,90\n"
        "16/07/2026;Salário;5000,00\n"
    ).encode()
    preview = client.post(
        "/api/bank-import/preview",
        data={"file": (io.BytesIO(content), "extrato.csv")},
        content_type="multipart/form-data",
    )
    assert preview.status_code == 200
    preview_data = preview.get_json()
    assert len(preview_data["transactions"]) == 1
    assert preview_data["transactions"][0]["category"] == "Alimentação"
    assert preview_data["ignored_income_count"] == 1

    confirmed = client.post(
        "/api/bank-import/confirm",
        json={
            "filename": preview_data["filename"],
            "selected_month": "2026-07",
            "transactions": preview_data["transactions"],
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["imported_count"] == 1
    assert confirmed.get_json()["export"]["filename"].endswith(".xlsx")

    repeated = client.post(
        "/api/bank-import/confirm",
        json={
            "filename": preview_data["filename"],
            "selected_month": "2026-07",
            "transactions": preview_data["transactions"],
        },
    )
    assert repeated.get_json() == {
        "export": None,
        "imported_count": 0,
        "investments_imported_count": 0,
        "investments_skipped_count": 0,
        "reconciled_count": 0,
        "skipped_count": 1,
    }


def test_ofx_and_xlsx_bank_parsers():
    ofx = b"""
    <OFX><BANKTRANLIST><STMTTRN>
    <TRNTYPE>DEBIT
    <DTPOSTED>20260717120000
    <TRNAMT>-89.50
    <FITID>abc-123
    <MEMO>POSTO AVENIDA
    </STMTTRN></BANKTRANLIST></OFX>
    """
    parsed_ofx = parse_bank_file("conta.ofx", ofx)
    assert parsed_ofx["transactions"][0]["amount"] == 89.5
    assert parsed_ofx["transactions"][0]["category"] == "Transporte"

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Date", "Description", "Amount"])
    sheet.append(["2026-07-18", "Farmácia Popular", 52.3])
    investments_sheet = workbook.create_sheet("Investimentos")
    investments_sheet.append(["Data", "Produto", "Valor", "Tipo"])
    investments_sheet.append(["2026-07-19", "Tesouro Selic 2029", -750, "Aplicação"])
    stream = io.BytesIO()
    workbook.save(stream)
    parsed_xlsx = parse_bank_file("cartao.xlsx", stream.getvalue())
    assert parsed_xlsx["transactions"][0]["category"] == "Saúde"
    assert parsed_xlsx["investments"][0]["asset"] == "Tesouro Selic 2029"
    assert parsed_xlsx["investments"][0]["amount"] == 750


def test_bank_import_keeps_investments_separate_from_budget(client):
    content = (
        "Data;Descrição;Valor;Tipo;Ativo;Quantidade;Preço unitário\n"
        "15/07/2026;Aplicação CDB;-1000,00;Aplicação;CDB 110% CDI;1;1000,00\n"
        "16/07/2026;Supermercado Central;-245,90;Débito;;;;\n"
    ).encode()
    preview_response = client.post(
        "/api/bank-import/preview",
        data={"file": (io.BytesIO(content), "extrato_com_investimentos.csv")},
        content_type="multipart/form-data",
    )
    assert preview_response.status_code == 200
    preview = preview_response.get_json()
    assert len(preview["transactions"]) == 1
    assert len(preview["investments"]) == 1
    assert preview["investments"][0]["asset"] == "CDB 110% CDI"
    assert preview["investments"][0]["movement_type"] == "Aplicação"
    assert preview["investments"][0]["quantity"] == 1

    confirmed = client.post(
        "/api/bank-import/confirm",
        json={
            "filename": preview["filename"],
            "selected_month": "2026-07",
            "transactions": preview["transactions"],
            "investments": preview["investments"],
        },
    )
    assert confirmed.status_code == 200
    result = confirmed.get_json()
    assert result["imported_count"] == 1
    assert result["investments_imported_count"] == 1

    july = client.get("/api/summary?month=2026-07").get_json()
    assert july["expenses"] == 245.9
    investments = client.get("/api/investments?year=2026").get_json()
    assert len(investments) == 1
    assert investments[0]["amount"] == 1000
    assert investments[0]["source_file"] == "extrato_com_investimentos.csv"

    workbook_path = (
        Path(client.application.config["EXPORT_DIR"]) / result["export"]["filename"]
    )
    workbook = load_workbook(workbook_path, read_only=True)
    sheet = workbook["Investimentos"]
    assert sheet["D2"].value == "CDB 110% CDI"
    assert sheet["F2"].value == 1000

    repeated = client.post(
        "/api/bank-import/confirm",
        json={
            "filename": preview["filename"],
            "selected_month": "2026-07",
            "investments": preview["investments"],
        },
    ).get_json()
    assert repeated["investments_imported_count"] == 0
    assert repeated["investments_skipped_count"] == 1


def test_ofx_investment_transactions_are_parsed():
    ofx = b"""
    <OFX>
      <SECLIST>
        <STOCKINFO><SECINFO>
          <SECID><UNIQUEID>BRTESTCDB001<UNIQUEIDTYPE>CUSIP</SECID>
          <SECNAME>CDB Banco Teste
        </SECINFO></STOCKINFO>
      </SECLIST>
      <INVTRANLIST>
        <BUYOTHER>
          <INVBUY>
            <INVTRAN><FITID>inv-001<DTTRADE>20260715120000<MEMO>Aporte mensal</INVTRAN>
            <SECID><UNIQUEID>BRTESTCDB001<UNIQUEIDTYPE>CUSIP</SECID>
            <UNITS>2<UNITPRICE>500<TOTAL>-1000
          </INVBUY>
          <BUYTYPE>BUY
        </BUYOTHER>
      </INVTRANLIST>
    </OFX>
    """
    parsed = parse_bank_file("investimentos.ofx", ofx)
    assert parsed["transactions"] == []
    assert len(parsed["investments"]) == 1
    investment = parsed["investments"][0]
    assert investment["asset"] == "CDB Banco Teste"
    assert investment["movement_type"] == "Aplicação"
    assert investment["amount"] == 1000
    assert investment["quantity"] == 2
    assert investment["unit_price"] == 500


def test_bank_transaction_replaces_fixed_expense_only_in_its_month(client):
    fixed_response = client.post(
        "/api/entries",
        json=sample_entry(
            description="Aluguel",
            amount=1800,
            category="Moradia",
            start_month="2026-01",
        ),
    )
    fixed_id = fixed_response.get_json()["entry"]["id"]
    content = "Data;Descrição;Valor\n10/07/2026;ALUGUEL IMOBILIARIA;-1850,00\n".encode()
    preview = client.post(
        "/api/bank-import/preview",
        data={"file": (io.BytesIO(content), "conta.csv")},
        content_type="multipart/form-data",
    ).get_json()
    transaction = preview["transactions"][0]
    assert transaction["reconciled_entry_id"] == fixed_id
    assert transaction["reconciliation_options"][0]["entry_id"] == fixed_id

    confirmed = client.post(
        "/api/bank-import/confirm",
        json={
            "filename": preview["filename"],
            "selected_month": "2026-07",
            "transactions": [transaction],
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["reconciled_count"] == 1

    july = client.get("/api/summary?month=2026-07").get_json()
    august = client.get("/api/summary?month=2026-08").get_json()
    assert july["expenses"] == 1850
    assert july["entries_count"] == 1
    assert august["expenses"] == 1800

    bank_entry = next(
        entry
        for entry in client.get("/api/entries").get_json()
        if entry["source"] == "bank_import"
    )
    client.delete(f"/api/entries/{bank_entry['id']}?month=2026-07")
    assert client.get("/api/summary?month=2026-07").get_json()["expenses"] == 1800
