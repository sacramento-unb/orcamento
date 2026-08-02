from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook


DATE_ALIASES = {
    "data",
    "date",
    "data da compra",
    "data do lancamento",
    "data lancamento",
    "transaction date",
}
DESCRIPTION_ALIASES = {
    "descricao",
    "description",
    "estabelecimento",
    "historico",
    "memo",
    "nome",
    "name",
    "titulo",
    "transacao",
    "transaction",
}
AMOUNT_ALIASES = {
    "valor",
    "amount",
    "valor da compra",
    "valor do lancamento",
    "transaction amount",
}
TYPE_ALIASES = {"tipo", "type", "natureza", "transaction type", "credito debito"}
ID_ALIASES = {"id", "identificador", "fitid", "transaction id"}
ASSET_ALIASES = {
    "ativo",
    "asset",
    "produto",
    "investimento",
    "fundo",
    "papel",
    "ticker",
}
QUANTITY_ALIASES = {"quantidade", "quantity", "qtd", "cotas", "units"}
UNIT_PRICE_ALIASES = {
    "preco unitario",
    "valor unitario",
    "unit price",
    "unitprice",
    "preco da cota",
    "valor da cota",
}

INVESTMENT_TERMS = (
    "aplicacao",
    "aporte",
    "investimento",
    "resgate",
    "rendimento",
    "dividendo",
    "juros sobre capital",
    "jcp",
    "tesouro direto",
    "cdb",
    "lci",
    "lca",
    "rdb",
    "fundo de investimento",
    "compra de titulo",
    "venda de titulo",
    "compra titulo",
    "venda titulo",
    "posicao",
    "custodia",
)


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char))
        .casefold()
        .strip()
        .split()
    )


def _parse_amount(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip()
    if not raw:
        return None
    negative_parentheses = raw.startswith("(") and raw.endswith(")")
    raw = re.sub(r"[^\d,.\-+]", "", raw)
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        pieces = raw.split(",")
        if len(pieces[-1]) in (1, 2):
            raw = "".join(pieces[:-1]) + "." + pieces[-1]
        else:
            raw = "".join(pieces)
    try:
        amount = float(raw)
    except ValueError:
        return None
    return -abs(amount) if negative_parentheses else amount


def _parse_date(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw[:10]
    for pattern in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d/%m/%y",
    ):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            continue
    compact = re.match(r"^(\d{4})(\d{2})(\d{2})", re.sub(r"\D", "", raw))
    if compact:
        try:
            return date(*(int(part) for part in compact.groups())).isoformat()
        except ValueError:
            return None
    return None


def _find_column(headers: list[str], aliases: set[str]) -> int | None:
    normalized = [_normalized(header) for header in headers]
    for index, header in enumerate(normalized):
        if header in aliases:
            return index
    for index, header in enumerate(normalized):
        if any(alias in header for alias in aliases):
            return index
    return None


def _infer_category(description: str) -> str:
    value = _normalized(description)
    rules = [
        (
            "Transporte",
            (
                "uber",
                "99app",
                "posto",
                "gasolina",
                "estacionamento",
                "pedagio",
                "seguro auto",
                "seguro carro",
            ),
        ),
        ("Alimentação", ("mercado", "supermercado", "ifood", "restaurante", "padaria")),
        (
            "Saúde",
            ("farmacia", "hospital", "clinica", "laboratorio", "unimed", "plano de saude"),
        ),
        ("Educação", ("escola", "colegio", "curso", "faculdade", "livraria")),
        ("Assinaturas", ("netflix", "spotify", "amazon prime", "google one", "icloud")),
        ("Moradia", ("aluguel", "condominio", "energia", "saneamento", "internet")),
        ("Lazer", ("cinema", "ingresso", "steam", "playstation")),
    ]
    for category, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return category
    return "Outros"


def _investment_movement(value: str, signed_amount: float) -> str | None:
    normalized = _normalized(value)
    if not any(term in normalized for term in INVESTMENT_TERMS):
        return None
    if any(term in normalized for term in ("posicao", "custodia", "saldo investido")):
        return "Posição"
    if any(
        term in normalized
        for term in ("rendimento", "dividendo", "juros sobre capital", "jcp", "cupom")
    ):
        return "Rendimento"
    if any(term in normalized for term in ("resgate", "venda", "sell")):
        return "Resgate"
    if any(term in normalized for term in ("aplicacao", "aporte", "compra", "buy")):
        return "Aplicação"
    return "Aplicação" if signed_amount < 0 else "Resgate"


def _external_id(
    transaction_date: str,
    description: str,
    amount: float,
    bank_id: str | None = None,
) -> str:
    normalized_transaction = (
        f"{transaction_date}|{_normalized(description)}|{amount:.2f}"
    )
    base = (
        f"{bank_id}|{normalized_transaction}" if bank_id else normalized_transaction
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _rows_to_transactions(
    headers: list[str], rows: Iterable[list[object]]
) -> tuple[list[dict], list[dict], int]:
    date_index = _find_column(headers, DATE_ALIASES)
    description_index = _find_column(headers, DESCRIPTION_ALIASES)
    amount_index = _find_column(headers, AMOUNT_ALIASES)
    type_index = _find_column(headers, TYPE_ALIASES)
    id_index = _find_column(headers, ID_ALIASES)
    asset_index = _find_column(headers, ASSET_ALIASES)
    quantity_index = _find_column(headers, QUANTITY_ALIASES)
    unit_price_index = _find_column(headers, UNIT_PRICE_ALIASES)
    if (
        date_index is None
        or (description_index is None and asset_index is None)
        or amount_index is None
    ):
        raise ValueError(
            "Não encontrei as colunas de data, descrição/ativo e valor no arquivo."
        )
    effective_description_index = (
        description_index if description_index is not None else asset_index
    )
    assert effective_description_index is not None

    parsed = []
    for row in rows:
        if max(date_index, effective_description_index, amount_index) >= len(row):
            continue
        transaction_date = _parse_date(row[date_index])
        description = str(row[effective_description_index] or "").strip()
        amount = _parse_amount(row[amount_index])
        if not transaction_date or not description or amount is None or amount == 0:
            continue
        type_value = (
            _normalized(row[type_index]) if type_index is not None and type_index < len(row) else ""
        )
        bank_id = (
            str(row[id_index]).strip()
            if id_index is not None and id_index < len(row) and row[id_index]
            else None
        )
        parsed.append(
            {
                "date": transaction_date,
                "description": description[:180],
                "signed_amount": amount,
                "type_hint": type_value,
                "bank_id": bank_id,
                "asset": (
                    str(row[asset_index]).strip()
                    if asset_index is not None
                    and asset_index < len(row)
                    and row[asset_index]
                    else ""
                ),
                "quantity": (
                    _parse_amount(row[quantity_index])
                    if quantity_index is not None and quantity_index < len(row)
                    else None
                ),
                "unit_price": (
                    _parse_amount(row[unit_price_index])
                    if unit_price_index is not None and unit_price_index < len(row)
                    else None
                ),
            }
        )

    has_negative = any(item["signed_amount"] < 0 for item in parsed)
    expenses = []
    investments = []
    ignored = 0
    for item in parsed:
        hint = item["type_hint"]
        investment_movement = _investment_movement(
            f"{hint} {item['description']} {item['asset']}",
            item["signed_amount"],
        )
        if investment_movement or item["asset"]:
            amount = round(abs(item["signed_amount"]), 2)
            asset = item["asset"] or item["description"]
            investments.append(
                {
                    "date": item["date"],
                    "description": item["description"],
                    "amount": amount,
                    "movement_type": investment_movement or (
                        "Posição"
                        if any(
                            term in hint
                            for term in ("posicao", "custodia", "saldo", "patrimonio")
                        )
                        else "Aplicação"
                        if item["signed_amount"] < 0
                        else "Resgate"
                    ),
                    "asset": asset[:180],
                    "quantity": (
                        round(abs(item["quantity"]), 8)
                        if item["quantity"] is not None
                        else None
                    ),
                    "unit_price": (
                        round(abs(item["unit_price"]), 8)
                        if item["unit_price"] is not None
                        else None
                    ),
                    "external_id": _external_id(
                        item["date"],
                        f"investimento|{item['description']}|{asset}",
                        amount,
                        item["bank_id"],
                    ),
                }
            )
            continue
        explicit_income = any(
            word in hint for word in ("credito", "credit", "entrada", "receita", "recebido")
        )
        explicit_expense = any(
            word in hint for word in ("debito", "debit", "saida", "compra", "pagamento")
        )
        is_expense = explicit_expense or (
            not explicit_income and (item["signed_amount"] < 0 or not has_negative)
        )
        if not is_expense:
            ignored += 1
            continue
        amount = round(abs(item["signed_amount"]), 2)
        expenses.append(
            {
                "date": item["date"],
                "description": item["description"],
                "amount": amount,
                "category": _infer_category(item["description"]),
                "external_id": _external_id(
                    item["date"], item["description"], amount, item["bank_id"]
                ),
            }
        )
    return expenses, investments, ignored


def _read_csv(content: bytes) -> tuple[list[dict], list[dict], int]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        reader = csv.reader(io.StringIO(text), dialect)
    except csv.Error:
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    nonempty = [row for row in rows if any(str(cell).strip() for cell in row)]
    if len(nonempty) < 2:
        raise ValueError("O arquivo CSV está vazio ou não possui transações.")
    return _rows_to_transactions(nonempty[0], nonempty[1:])


def _read_xlsx(content: bytes) -> tuple[list[dict], list[dict], int]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    transactions: list[dict] = []
    investments: list[dict] = []
    ignored = 0
    valid_sheets = 0
    for sheet in workbook.worksheets:
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        nonempty = [row for row in rows if any(cell not in (None, "") for cell in row)]
        if len(nonempty) < 2:
            continue
        headers = [str(cell or "") for cell in nonempty[0]]
        try:
            sheet_transactions, sheet_investments, sheet_ignored = (
                _rows_to_transactions(headers, nonempty[1:])
            )
        except ValueError:
            continue
        valid_sheets += 1
        transactions.extend(sheet_transactions)
        investments.extend(sheet_investments)
        ignored += sheet_ignored
    if not valid_sheets:
        raise ValueError("A planilha está vazia ou não possui transações.")
    return transactions, investments, ignored


def _ofx_value(block: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*([^<\r\n]+)", block, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _read_ofx_investments(text: str) -> list[dict]:
    security_names: dict[str, str] = {}
    for block in re.findall(
        r"<SECINFO>(.*?)</SECINFO>", text, flags=re.IGNORECASE | re.DOTALL
    ):
        unique_id = _ofx_value(block, "UNIQUEID")
        name = _ofx_value(block, "SECNAME") or _ofx_value(block, "TICKER")
        if unique_id and name:
            security_names[unique_id] = name

    tag_pattern = (
        r"BUYDEBT|BUYMF|BUYOPT|BUYOTHER|BUYSTOCK|"
        r"SELLDEBT|SELLMF|SELLOPT|SELLOTHER|SELLSTOCK|"
        r"INCOME|REINVEST|TRANSFER|"
        r"POSDEBT|POSMF|POSOPT|POSOTHER|POSSTOCK"
    )
    investments = []
    for match in re.finditer(
        rf"<({tag_pattern})>(.*?)</\1>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        tag = match.group(1).upper()
        block = match.group(2)
        transaction_date = _parse_date(
            _ofx_value(block, "DTTRADE")
            or _ofx_value(block, "DTSETTLE")
            or _ofx_value(block, "DTPOSTED")
            or _ofx_value(block, "DTPRICEASOF")
        )
        amount = _parse_amount(
            _ofx_value(block, "TOTAL")
            or _ofx_value(block, "TRNAMT")
            or _ofx_value(block, "MKTVAL")
        )
        if not transaction_date or amount in (None, 0):
            continue
        unique_id = _ofx_value(block, "UNIQUEID")
        asset = (
            security_names.get(unique_id)
            or _ofx_value(block, "TICKER")
            or unique_id
            or "Investimento"
        )
        description = _ofx_value(block, "MEMO") or asset
        movement_type = (
            "Aplicação"
            if tag.startswith("BUY") or tag == "REINVEST"
            else "Resgate"
            if tag.startswith("SELL")
            else "Rendimento"
            if tag == "INCOME"
            else "Posição"
            if tag.startswith("POS")
            else "Transferência"
        )
        value = round(abs(amount), 2)
        investments.append(
            {
                "date": transaction_date,
                "description": description[:180],
                "amount": value,
                "movement_type": movement_type,
                "asset": asset[:180],
                "quantity": (
                    round(abs(parsed), 8)
                    if (parsed := _parse_amount(_ofx_value(block, "UNITS"))) is not None
                    else None
                ),
                "unit_price": (
                    round(abs(parsed), 8)
                    if (parsed := _parse_amount(_ofx_value(block, "UNITPRICE"))) is not None
                    else None
                ),
                "external_id": _external_id(
                    transaction_date,
                    f"investimento|{tag}|{description}|{asset}",
                    value,
                    _ofx_value(block, "FITID") or None,
                ),
            }
        )
    return investments


def _read_ofx(content: bytes) -> tuple[list[dict], list[dict], int]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    blocks = re.findall(
        r"<STMTTRN>(.*?)(?=<STMTTRN>|</BANKTRANLIST>|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    raw_rows = []
    for block in blocks:
        raw_rows.append(
            [
                _ofx_value(block, "DTPOSTED"),
                _ofx_value(block, "MEMO") or _ofx_value(block, "NAME"),
                _ofx_value(block, "TRNAMT"),
                _ofx_value(block, "TRNTYPE"),
                _ofx_value(block, "FITID"),
            ]
        )
    investments = _read_ofx_investments(text)
    if not raw_rows and not investments:
        raise ValueError("Não encontrei transações válidas no arquivo OFX.")
    if raw_rows:
        transactions, bank_investments, ignored = _rows_to_transactions(
            ["data", "descricao", "valor", "tipo", "fitid"], raw_rows
        )
        investments.extend(bank_investments)
        return transactions, investments, ignored
    return [], investments, 0


def parse_bank_file(filename: str, content: bytes) -> dict:
    if not content:
        raise ValueError("O arquivo enviado está vazio.")
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("O arquivo deve ter no máximo 10 MB.")
    extension = Path(filename).suffix.casefold()
    if extension == ".csv":
        transactions, investments, ignored = _read_csv(content)
        file_type = "CSV"
    elif extension in {".xlsx", ".xlsm"}:
        transactions, investments, ignored = _read_xlsx(content)
        file_type = "Excel"
    elif extension == ".ofx":
        transactions, investments, ignored = _read_ofx(content)
        file_type = "OFX"
    else:
        raise ValueError("Formato não suportado. Use CSV, OFX ou XLSX.")
    if not transactions and not investments:
        raise ValueError("Nenhum gasto ou investimento foi identificado nesse arquivo.")
    if len(transactions) + len(investments) > 1000:
        raise ValueError(
            "O arquivo possui mais de 1.000 registros. Divida-o em partes."
        )
    return {
        "filename": Path(filename).name,
        "file_type": file_type,
        "transactions": transactions,
        "investments": investments,
        "ignored_income_count": ignored,
    }
