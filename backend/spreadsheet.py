from __future__ import annotations

import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .database import active_entries_query


TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
NS = {"table": TABLE_NS, "office": OFFICE_NS, "text": TEXT_NS}
MONTH_NAMES = [
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


def _year_start() -> str:
    return datetime.now().strftime("%Y-01")


def _cell_value(cell: ElementTree.Element) -> str | float | None:
    value_type = cell.attrib.get(f"{{{OFFICE_NS}}}value-type")
    if value_type == "float":
        raw = cell.attrib.get(f"{{{OFFICE_NS}}}value")
        return float(raw) if raw is not None else None
    paragraphs = ["".join(p.itertext()) for p in cell.findall(".//text:p", NS)]
    text = " ".join(part.strip() for part in paragraphs if part.strip())
    return text or None


def read_ods_rows(source_path: str | Path) -> list[list[str | float | None]]:
    """Lê valores básicos de uma planilha ODS sem alterar o arquivo original."""
    with zipfile.ZipFile(source_path) as archive:
        xml = archive.read("content.xml")

    root = ElementTree.fromstring(xml)
    table = root.find(".//table:table", NS)
    if table is None:
        return []

    rows: list[list[str | float | None]] = []
    for row in table.findall("table:table-row", NS):
        row_repeat = int(row.attrib.get(f"{{{TABLE_NS}}}number-rows-repeated", "1"))
        values: list[str | float | None] = []
        for cell in row.findall("table:table-cell", NS):
            cell_repeat = int(
                cell.attrib.get(f"{{{TABLE_NS}}}number-columns-repeated", "1")
            )
            values.extend([_cell_value(cell)] * min(cell_repeat, 64))
        values = values[:64]
        for _ in range(min(row_repeat, 64)):
            rows.append(list(values))
    return rows


def initial_entries_from_ods(source_path: str | Path) -> list[dict]:
    rows = read_ods_rows(source_path)
    month = _year_start()
    entries: list[dict] = []
    categories = {
        "plano de saúde": "Saúde",
        "gasolina": "Transporte",
        "seguro carro": "Transporte",
        "ipva": "Transporte",
        "escola": "Educação",
    }

    # Na planilha original, os gastos ocupam A2:B6.
    for row in rows[1:6]:
        if len(row) < 2 or not isinstance(row[0], str) or not isinstance(row[1], float):
            continue
        description = row[0].strip()
        entries.append(
            {
                "description": description,
                "amount": round(row[1], 2),
                "entry_type": "expense",
                "category": categories.get(description.casefold(), "Outros"),
                "recurring": 1,
                "start_month": month,
                "end_month": None,
                "notes": "Importado da planilha original.",
            }
        )

    # As receitas aparecem como rótulo em I2/I5 e valor em I3/I6.
    for label_index, value_index in ((1, 2), (4, 5)):
        if value_index >= len(rows):
            continue
        label_row, value_row = rows[label_index], rows[value_index]
        if len(label_row) < 9 or len(value_row) < 9:
            continue
        label, value = label_row[8], value_row[8]
        if isinstance(label, str) and isinstance(value, float):
            entries.append(
                {
                    "description": label.strip(),
                    "amount": round(value, 2),
                    "entry_type": "income",
                    "category": "Salário",
                    "recurring": 1,
                    "start_month": month,
                    "end_month": None,
                    "notes": "Importado da planilha original.",
                }
            )
    return entries


def seed_from_ods(connection: sqlite3.Connection, source_path: str | Path) -> int:
    existing = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    if existing:
        return 0
    entries = initial_entries_from_ods(source_path)
    for entry in entries:
        connection.execute(
            """
            INSERT INTO entries (
                description, amount, entry_type, category, recurring,
                start_month, end_month, notes
            ) VALUES (
                :description, :amount, :entry_type, :category, :recurring,
                :start_month, :end_month, :notes
            )
            """,
            entry,
        )
    connection.execute(
        "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('source_file', ?)",
        (str(Path(source_path).name),),
    )
    connection.commit()
    return len(entries)


def migrate_imported_entries_to_year_start(connection: sqlite3.Connection) -> bool:
    """Faz os valores fixos importados valerem desde janeiro uma única vez."""
    migrated = connection.execute(
        "SELECT value FROM app_meta WHERE key = 'monthly_tabs_v1'"
    ).fetchone()
    if migrated:
        return False
    connection.execute(
        """
        UPDATE entries
        SET start_month = ?, updated_at = CURRENT_TIMESTAMP
        WHERE recurring = 1 AND notes = 'Importado da planilha original.'
        """,
        (_year_start(),),
    )
    connection.execute(
        "INSERT INTO app_meta (key, value) VALUES ('monthly_tabs_v1', 'done')"
    )
    connection.commit()
    return True


def _totals_for_month(connection: sqlite3.Connection, month: str) -> tuple[float, float]:
    query, params = active_entries_query(month)
    rows = connection.execute(query, params).fetchall()
    expenses = sum(row["amount"] for row in rows if row["entry_type"] == "expense")
    income = sum(row["amount"] for row in rows if row["entry_type"] == "income")
    return round(expenses, 2), round(income, 2)


def _style_sheet(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="0B3B36")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(vertical="center")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        width = max(len(str(cell.value or "")) for cell in column) + 2
        sheet.column_dimensions[get_column_letter(column[0].column)].width = min(
            max(width, 12), 42
        )


def _create_month_sheet(
    workbook: Workbook,
    connection: sqlite3.Connection,
    year: int,
    month_number: int,
) -> None:
    month_name = MONTH_NAMES[month_number - 1]
    month = f"{year:04d}-{month_number:02d}"
    sheet = workbook.create_sheet(month_name)
    sheet.sheet_view.showGridLines = False
    sheet.merge_cells("A1:F1")
    title = sheet["A1"]
    title.value = f"Orçamento — {month_name} de {year}"
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill("solid", fgColor="0B3B36")
    title.alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 30

    sheet.append([])
    sheet.append(["Descrição", "Tipo", "Categoria", "Valor", "Frequência", "Observações"])
    header_fill = PatternFill("solid", fgColor="DDE9E3")
    for cell in sheet[3]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="234139")

    query, params = active_entries_query(month)
    rows = connection.execute(query, params).fetchall()
    for row in rows:
        sheet.append(
            [
                row["description"],
                "Gasto" if row["entry_type"] == "expense" else "Receita",
                row["category"],
                row["amount"],
                (
                    "Real conciliado"
                    if row["reconciled_entry_id"]
                    else "Mensal" if row["recurring"] else "Somente este mês"
                ),
                row["notes"],
            ]
        )

    expenses = round(
        sum(row["amount"] for row in rows if row["entry_type"] == "expense"), 2
    )
    income = round(
        sum(row["amount"] for row in rows if row["entry_type"] == "income"), 2
    )
    totals_row = len(rows) + 5
    sheet.cell(totals_row, 3, "Receitas")
    sheet.cell(totals_row, 4, income)
    sheet.cell(totals_row + 1, 3, "Gastos")
    sheet.cell(totals_row + 1, 4, expenses)
    sheet.cell(totals_row + 2, 3, "Balanço")
    sheet.cell(totals_row + 2, 4, round(income - expenses, 2))
    for row_number in range(totals_row, totals_row + 3):
        sheet.cell(row_number, 3).font = Font(bold=True)
        sheet.cell(row_number, 4).font = Font(bold=True)
        sheet.cell(row_number, 4).number_format = 'R$ #,##0.00'

    for cell in sheet["D"][3:]:
        if isinstance(cell.value, (int, float)):
            cell.number_format = 'R$ #,##0.00'
    sheet.freeze_panes = "A4"
    if rows:
        sheet.auto_filter.ref = f"A3:F{len(rows) + 3}"
    widths = [30, 14, 18, 16, 20, 42]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def export_workbook(
    connection: sqlite3.Connection,
    export_dir: str | Path,
    selected_month: str | None = None,
) -> Path:
    selected_month = selected_month or _month_now()
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"gastos_mensais_v{stamp}.xlsx"
    final_path = export_path / filename

    workbook = Workbook()
    overview = workbook.active
    overview.title = "Visão geral"
    overview.append(["Indicador", "Valor"])
    expenses, income = _totals_for_month(connection, selected_month)
    overview.append(["Mês de referência", selected_month])
    overview.append(["Receitas", income])
    overview.append(["Gastos", expenses])
    overview.append(["Balanço", round(income - expenses, 2)])
    overview.append(["Gerado em", datetime.now().astimezone().isoformat(timespec="seconds")])
    for cell in overview["B"][2:]:
        if isinstance(cell.value, (int, float)):
            cell.number_format = 'R$ #,##0.00'
    _style_sheet(overview)

    entries_sheet = workbook.create_sheet("Lançamentos")
    entries_sheet.append(
        [
            "ID",
            "Descrição",
            "Tipo",
            "Categoria",
            "Valor",
            "Recorrente",
            "Mês inicial",
            "Mês final",
            "Data da transação",
            "Conciliado com",
            "Observações",
            "Origem",
            "Atualizado em",
        ]
    )
    rows = connection.execute(
        "SELECT * FROM entries ORDER BY entry_type, description COLLATE NOCASE"
    ).fetchall()
    descriptions_by_id = {row["id"]: row["description"] for row in rows}
    for row in rows:
        entries_sheet.append(
            [
                row["id"],
                row["description"],
                "Gasto" if row["entry_type"] == "expense" else "Receita",
                row["category"],
                row["amount"],
                "Sim" if row["recurring"] else "Não",
                row["start_month"],
                row["end_month"] or "",
                row["transaction_date"] or "",
                descriptions_by_id.get(row["reconciled_entry_id"], ""),
                row["notes"],
                "Importação bancária" if row["source"] == "bank_import" else "Manual",
                row["updated_at"],
            ]
        )
    for cell in entries_sheet["E"][1:]:
        cell.number_format = 'R$ #,##0.00'
    _style_sheet(entries_sheet)

    investments_sheet = workbook.create_sheet("Investimentos")
    investments_sheet.append(
        [
            "ID",
            "Data",
            "Movimentação",
            "Ativo / produto",
            "Descrição",
            "Valor",
            "Quantidade",
            "Preço unitário",
            "Arquivo de origem",
            "Importado em",
        ]
    )
    investment_rows = connection.execute(
        """
        SELECT * FROM investments
        ORDER BY transaction_date DESC, id DESC
        """
    ).fetchall()
    for row in investment_rows:
        investments_sheet.append(
            [
                row["id"],
                row["transaction_date"],
                row["movement_type"],
                row["asset"],
                row["description"],
                row["amount"],
                row["quantity"],
                row["unit_price"],
                row["source_file"],
                row["created_at"],
            ]
        )
    for column in ("F", "H"):
        for cell in investments_sheet[column][1:]:
            if isinstance(cell.value, (int, float)):
                cell.number_format = 'R$ #,##0.00'
    _style_sheet(investments_sheet)

    selected_year = int(selected_month.split("-")[0])
    for month_number in range(1, 13):
        _create_month_sheet(workbook, connection, selected_year, month_number)

    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", dir=export_path, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        workbook.save(temporary_path)
        os.replace(temporary_path, final_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return final_path


def list_exports(export_dir: str | Path) -> list[dict]:
    path = Path(export_dir)
    if not path.exists():
        return []
    result = []
    for item in sorted(path.glob("gastos_mensais_v*.xlsx"), reverse=True):
        match = re.search(r"_v(\d{8})_(\d{6})_", item.name)
        created_at = datetime.fromtimestamp(item.stat().st_mtime).astimezone()
        if match:
            created_at = datetime.strptime(
                "".join(match.groups()), "%Y%m%d%H%M%S"
            ).astimezone()
        result.append(
            {
                "filename": item.name,
                "created_at": created_at.isoformat(timespec="seconds"),
                "size": item.stat().st_size,
                "url": f"/api/exports/{item.name}",
            }
        )
    return result
