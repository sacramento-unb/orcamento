from __future__ import annotations

import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .bank_import import parse_bank_file
from .database import active_entries_query, connect, init_db
from .reconciliation import reconciliation_options
from .spreadsheet import (
    export_workbook,
    list_exports,
    migrate_imported_entries_to_year_start,
    seed_from_ods,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
ALLOWED_TYPES = {"expense", "income"}
ALLOWED_INVESTMENT_TYPES = {
    "Aplicação",
    "Resgate",
    "Rendimento",
    "Transferência",
    "Posição",
}


def _current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def _shift_month(month: str, offset: int) -> str:
    year, number = (int(part) for part in month.split("-"))
    absolute = year * 12 + number - 1 + offset
    return f"{absolute // 12:04d}-{absolute % 12 + 1:02d}"


def _serialize(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "description": row["description"],
        "amount": round(row["amount"], 2),
        "entry_type": row["entry_type"],
        "category": row["category"],
        "recurring": bool(row["recurring"]),
        "start_month": row["start_month"],
        "end_month": row["end_month"],
        "notes": row["notes"],
        "source": row["source"],
        "reconciled_entry_id": row["reconciled_entry_id"],
        "transaction_date": row["transaction_date"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _serialize_investment(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "date": row["transaction_date"],
        "description": row["description"],
        "amount": round(row["amount"], 2),
        "movement_type": row["movement_type"],
        "asset": row["asset"],
        "quantity": row["quantity"],
        "unit_price": row["unit_price"],
        "source_file": row["source_file"],
        "created_at": row["created_at"],
    }


def _validate_payload(payload: dict) -> tuple[dict | None, str | None]:
    description = str(payload.get("description", "")).strip()
    category = str(payload.get("category", "")).strip()
    entry_type = str(payload.get("entry_type", "")).strip()
    start_month = str(payload.get("start_month", "")).strip()
    end_month_raw = payload.get("end_month")
    end_month = str(end_month_raw).strip() if end_month_raw else None
    notes = str(payload.get("notes", "")).strip()

    try:
        amount = round(float(payload.get("amount")), 2)
    except (TypeError, ValueError):
        return None, "Informe um valor válido."
    if not description:
        return None, "A descrição é obrigatória."
    if not category:
        return None, "A categoria é obrigatória."
    if entry_type not in ALLOWED_TYPES:
        return None, "O tipo deve ser expense ou income."
    if amount <= 0:
        return None, "O valor deve ser maior que zero."
    if not MONTH_PATTERN.match(start_month):
        return None, "Informe o mês inicial no formato AAAA-MM."
    if end_month and not MONTH_PATTERN.match(end_month):
        return None, "Informe o mês final no formato AAAA-MM."
    if end_month and end_month < start_month:
        return None, "O mês final não pode ser anterior ao mês inicial."

    return (
        {
            "description": description,
            "amount": amount,
            "entry_type": entry_type,
            "category": category,
            "recurring": 1 if bool(payload.get("recurring", True)) else 0,
            "start_month": start_month,
            "end_month": end_month,
            "notes": notes,
        },
        None,
    )


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")
    app.config.update(
        DATABASE=os.getenv("BUDGET_DB_PATH", str(ROOT_DIR / "data" / "orcamento.db")),
        SOURCE_SPREADSHEET=os.getenv(
            "BUDGET_SOURCE_FILE", str(ROOT_DIR / "gastos mensais.ods")
        ),
        EXPORT_DIR=os.getenv("BUDGET_EXPORT_DIR", str(ROOT_DIR / "exports")),
        TESTING=False,
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    init_db(app.config["DATABASE"])
    source = Path(app.config["SOURCE_SPREADSHEET"])
    if source.exists():
        with connect(app.config["DATABASE"]) as connection:
            seeded = seed_from_ods(connection, source)
            migrated = migrate_imported_entries_to_year_start(connection)
            if seeded or migrated:
                export_workbook(
                    connection, app.config["EXPORT_DIR"], _current_month()
                )

    def db() -> sqlite3.Connection:
        return connect(app.config["DATABASE"])

    def export_after_change(connection: sqlite3.Connection, month: str) -> dict:
        exported = export_workbook(connection, app.config["EXPORT_DIR"], month)
        connection.commit()
        return next(
            item
            for item in list_exports(app.config["EXPORT_DIR"])
            if item["filename"] == exported.name
        )

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/entries")
    def get_entries():
        month = request.args.get("month")
        with db() as connection:
            if month:
                if not MONTH_PATTERN.match(month):
                    return jsonify({"error": "Mês inválido."}), 400
                query, params = active_entries_query(month)
                rows = connection.execute(query, params).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM entries ORDER BY entry_type, amount DESC"
                ).fetchall()
        return jsonify([_serialize(row) for row in rows])

    @app.get("/api/summary")
    def summary():
        month = request.args.get("month", _current_month())
        if not MONTH_PATTERN.match(month):
            return jsonify({"error": "Mês inválido."}), 400
        with db() as connection:
            query, params = active_entries_query(month)
            rows = connection.execute(query, params).fetchall()
            serialized = [_serialize(row) for row in rows]

            income = round(
                sum(item["amount"] for item in serialized if item["entry_type"] == "income"),
                2,
            )
            expenses = round(
                sum(
                    item["amount"]
                    for item in serialized
                    if item["entry_type"] == "expense"
                ),
                2,
            )
            categories: dict[str, float] = defaultdict(float)
            for item in serialized:
                if item["entry_type"] == "expense":
                    categories[item["category"]] += item["amount"]

            history = []
            for offset in range(-5, 1):
                history_month = _shift_month(month, offset)
                history_query, history_params = active_entries_query(history_month)
                history_rows = connection.execute(
                    history_query, history_params
                ).fetchall()
                history.append(
                    {
                        "month": history_month,
                        "income": round(
                            sum(
                                row["amount"]
                                for row in history_rows
                                if row["entry_type"] == "income"
                            ),
                            2,
                        ),
                        "expenses": round(
                            sum(
                                row["amount"]
                                for row in history_rows
                                if row["entry_type"] == "expense"
                            ),
                            2,
                        ),
                    }
                )

        balance = round(income - expenses, 2)
        savings_rate = round((balance / income) * 100, 1) if income else 0
        return jsonify(
            {
                "month": month,
                "income": income,
                "expenses": expenses,
                "balance": balance,
                "savings_rate": savings_rate,
                "category_totals": [
                    {"category": category, "amount": round(amount, 2)}
                    for category, amount in sorted(
                        categories.items(), key=lambda item: item[1], reverse=True
                    )
                ],
                "history": history,
                "entries_count": len(serialized),
            }
        )

    @app.get("/api/investments")
    def get_investments():
        year = request.args.get("year", "")
        if year and not re.fullmatch(r"\d{4}", year):
            return jsonify({"error": "Ano inválido."}), 400
        with db() as connection:
            if year:
                rows = connection.execute(
                    """
                    SELECT * FROM investments
                    WHERE substr(transaction_date, 1, 4) = ?
                    ORDER BY transaction_date DESC, id DESC
                    """,
                    (year,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM investments
                    ORDER BY transaction_date DESC, id DESC
                    """
                ).fetchall()
        return jsonify([_serialize_investment(row) for row in rows])

    @app.post("/api/entries")
    def create_entry():
        values, error = _validate_payload(request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400
        with db() as connection:
            cursor = connection.execute(
                """
                INSERT INTO entries (
                    description, amount, entry_type, category, recurring,
                    start_month, end_month, notes
                ) VALUES (
                    :description, :amount, :entry_type, :category, :recurring,
                    :start_month, :end_month, :notes
                )
                """,
                values,
            )
            row = connection.execute(
                "SELECT * FROM entries WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            export_info = export_after_change(connection, values["start_month"])
        return jsonify({"entry": _serialize(row), "export": export_info}), 201

    @app.put("/api/entries/<int:entry_id>")
    def update_entry(entry_id: int):
        values, error = _validate_payload(request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400
        with db() as connection:
            exists = connection.execute(
                "SELECT id FROM entries WHERE id = ?", (entry_id,)
            ).fetchone()
            if not exists:
                return jsonify({"error": "Lançamento não encontrado."}), 404
            connection.execute(
                """
                UPDATE entries SET
                    description = :description,
                    amount = :amount,
                    entry_type = :entry_type,
                    category = :category,
                    recurring = :recurring,
                    start_month = :start_month,
                    end_month = :end_month,
                    notes = :notes,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {**values, "id": entry_id},
            )
            row = connection.execute(
                "SELECT * FROM entries WHERE id = ?", (entry_id,)
            ).fetchone()
            export_info = export_after_change(connection, values["start_month"])
        return jsonify({"entry": _serialize(row), "export": export_info})

    @app.delete("/api/entries/<int:entry_id>")
    def delete_entry(entry_id: int):
        selected_month = request.args.get("month", _current_month())
        if not MONTH_PATTERN.match(selected_month):
            return jsonify({"error": "Mês inválido."}), 400
        with db() as connection:
            cursor = connection.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Lançamento não encontrado."}), 404
            export_info = export_after_change(connection, selected_month)
        return jsonify({"deleted": entry_id, "export": export_info})

    @app.get("/api/exports")
    def get_exports():
        return jsonify(list_exports(app.config["EXPORT_DIR"]))

    @app.post("/api/bank-import/preview")
    def preview_bank_import():
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return jsonify({"error": "Selecione um arquivo bancário."}), 400
        try:
            result = parse_bank_file(uploaded.filename, uploaded.read())
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        with db() as connection:
            existing_ids = {
                row["external_id"]
                for row in connection.execute(
                    """
                    SELECT external_id FROM entries
                    WHERE source = 'bank_import' AND external_id IS NOT NULL
                    """
                ).fetchall()
            }
            existing_investment_ids = {
                row["external_id"]
                for row in connection.execute(
                    "SELECT external_id FROM investments"
                ).fetchall()
            }
            duplicate_count = 0
            investment_duplicate_count = 0
            reserved: set[tuple[int, str]] = set()
            for transaction in result["transactions"]:
                transaction["duplicate"] = transaction["external_id"] in existing_ids
                if transaction["duplicate"]:
                    transaction["reconciliation_options"] = []
                    transaction["reconciled_entry_id"] = None
                    duplicate_count += 1
                    continue
                options, suggested_id = reconciliation_options(
                    connection, transaction, reserved
                )
                transaction["reconciliation_options"] = options
                transaction["reconciled_entry_id"] = suggested_id
                if suggested_id:
                    reserved.add((suggested_id, transaction["date"][:7]))
            for investment in result["investments"]:
                investment["duplicate"] = (
                    investment["external_id"] in existing_investment_ids
                )
                if investment["duplicate"]:
                    investment_duplicate_count += 1
        result["duplicate_count"] = duplicate_count
        result["investment_duplicate_count"] = investment_duplicate_count
        return jsonify(result)

    @app.post("/api/bank-import/confirm")
    def confirm_bank_import():
        payload = request.get_json(silent=True) or {}
        transactions = payload.get("transactions", [])
        investments = payload.get("investments", [])
        selected_month = str(payload.get("selected_month", _current_month()))
        filename = Path(str(payload.get("filename", "extrato bancário"))).name[:120]
        if not MONTH_PATTERN.match(selected_month):
            return jsonify({"error": "Mês selecionado inválido."}), 400
        if not isinstance(transactions, list) or not isinstance(investments, list):
            return jsonify({"error": "Os registros selecionados são inválidos."}), 400
        if not transactions and not investments:
            return (
                jsonify({"error": "Selecione ao menos um gasto ou investimento."}),
                400,
            )
        if len(transactions) + len(investments) > 1000:
            return jsonify({"error": "Importe no máximo 1.000 registros por vez."}), 400

        imported = 0
        skipped = 0
        reconciled = 0
        investments_imported = 0
        investments_skipped = 0
        with db() as connection:
            for item in transactions:
                description = str(item.get("description", "")).strip()[:180]
                category = str(item.get("category", "Outros")).strip()[:80]
                transaction_date = str(item.get("date", ""))
                external_id = str(item.get("external_id", ""))
                reconciled_entry_id_raw = item.get("reconciled_entry_id")
                try:
                    reconciled_entry_id = (
                        int(reconciled_entry_id_raw)
                        if reconciled_entry_id_raw not in (None, "")
                        else None
                    )
                except (TypeError, ValueError):
                    connection.rollback()
                    return jsonify({"error": "Conciliação selecionada inválida."}), 400
                try:
                    datetime.strptime(transaction_date, "%Y-%m-%d")
                    amount = round(abs(float(item.get("amount"))), 2)
                except (TypeError, ValueError):
                    connection.rollback()
                    return jsonify({"error": "Há uma transação com dados inválidos."}), 400
                if (
                    not description
                    or not category
                    or amount <= 0
                    or not re.fullmatch(r"[0-9a-f]{64}", external_id)
                ):
                    connection.rollback()
                    return jsonify({"error": "Há uma transação com dados inválidos."}), 400

                reconciled_description = None
                if reconciled_entry_id is not None:
                    fixed = connection.execute(
                        """
                        SELECT fixed.*
                        FROM entries AS fixed
                        WHERE fixed.id = ?
                          AND fixed.entry_type = 'expense'
                          AND fixed.recurring = 1
                          AND fixed.start_month <= ?
                          AND (
                              fixed.end_month IS NULL
                              OR fixed.end_month = ''
                              OR fixed.end_month >= ?
                          )
                          AND NOT EXISTS (
                              SELECT 1 FROM entries AS actual
                              WHERE actual.reconciled_entry_id = fixed.id
                                AND actual.start_month = ?
                          )
                        """,
                        (
                            reconciled_entry_id,
                            transaction_date[:7],
                            transaction_date[:7],
                            transaction_date[:7],
                        ),
                    ).fetchone()
                    if fixed is None:
                        connection.rollback()
                        return (
                            jsonify(
                                {
                                    "error": (
                                        "O gasto fixo escolhido já foi conciliado "
                                        "ou não vale para esse mês."
                                    )
                                }
                            ),
                            409,
                        )
                    reconciled_description = fixed["description"]

                note = f"Importado do arquivo bancário {filename}."
                if reconciled_description:
                    note = (
                        f"Valor realizado conciliado com {reconciled_description}. "
                        f"Origem: {filename}."
                    )
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO entries (
                        description, amount, entry_type, category, recurring,
                        start_month, end_month, notes, source, external_id,
                        reconciled_entry_id, transaction_date
                    ) VALUES (
                        ?, ?, 'expense', ?, 0, ?, NULL, ?, 'bank_import', ?, ?, ?
                    )
                    """,
                    (
                        description,
                        amount,
                        category,
                        transaction_date[:7],
                        note,
                        external_id,
                        reconciled_entry_id,
                        transaction_date,
                    ),
                )
                if cursor.rowcount:
                    imported += 1
                    if reconciled_entry_id is not None:
                        reconciled += 1
                else:
                    skipped += 1

            for item in investments:
                description = str(item.get("description", "")).strip()[:180]
                asset = str(item.get("asset", "")).strip()[:180]
                movement_type = str(item.get("movement_type", "")).strip()[:40]
                transaction_date = str(item.get("date", ""))
                external_id = str(item.get("external_id", ""))
                try:
                    datetime.strptime(transaction_date, "%Y-%m-%d")
                    amount = round(abs(float(item.get("amount"))), 2)
                    quantity = (
                        round(abs(float(item["quantity"])), 8)
                        if item.get("quantity") not in (None, "")
                        else None
                    )
                    unit_price = (
                        round(abs(float(item["unit_price"])), 8)
                        if item.get("unit_price") not in (None, "")
                        else None
                    )
                except (TypeError, ValueError):
                    connection.rollback()
                    return jsonify({"error": "Há um investimento com dados inválidos."}), 400
                if (
                    not description
                    or not asset
                    or movement_type not in ALLOWED_INVESTMENT_TYPES
                    or amount <= 0
                    or not re.fullmatch(r"[0-9a-f]{64}", external_id)
                ):
                    connection.rollback()
                    return jsonify({"error": "Há um investimento com dados inválidos."}), 400
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO investments (
                        transaction_date, description, amount, movement_type,
                        asset, quantity, unit_price, source_file, external_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transaction_date,
                        description,
                        amount,
                        movement_type,
                        asset,
                        quantity,
                        unit_price,
                        filename,
                        external_id,
                    ),
                )
                if cursor.rowcount:
                    investments_imported += 1
                else:
                    investments_skipped += 1

            export_info = (
                export_after_change(connection, selected_month)
                if imported or investments_imported
                else None
            )
        return jsonify(
            {
                "imported_count": imported,
                "skipped_count": skipped,
                "reconciled_count": reconciled,
                "investments_imported_count": investments_imported,
                "investments_skipped_count": investments_skipped,
                "export": export_info,
            }
        )

    @app.post("/api/export")
    def manual_export():
        month = (request.get_json(silent=True) or {}).get("month", _current_month())
        if not MONTH_PATTERN.match(month):
            return jsonify({"error": "Mês inválido."}), 400
        with db() as connection:
            path = export_workbook(connection, app.config["EXPORT_DIR"], month)
        info = next(
            item
            for item in list_exports(app.config["EXPORT_DIR"])
            if item["filename"] == path.name
        )
        return jsonify(info), 201

    @app.get("/api/exports/<path:filename>")
    def download_export(filename: str):
        if not re.fullmatch(r"gastos_mensais_v[\d_]+\.xlsx", filename):
            return jsonify({"error": "Arquivo inválido."}), 400
        return send_from_directory(
            app.config["EXPORT_DIR"], filename, as_attachment=True
        )

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        static_root = Path(app.static_folder)
        if path and (static_root / path).is_file():
            return app.send_static_file(path)
        if (static_root / "index.html").is_file():
            return app.send_static_file("index.html")
        return jsonify(
            {
                "message": "Frontend ainda não compilado.",
                "hint": "Execute npm run build dentro de frontend.",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
