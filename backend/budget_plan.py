from __future__ import annotations

import sqlite3
import os

from .database import active_entries_query

INCOME = [
    {"description": "Salário demonstrativo", "amount": 6000.0, "category": "Salário"},
    {"description": "Renda autônoma 1", "amount": 2500.0, "category": "Salário"},
    {"description": "Renda autônoma 2", "amount": 1500.0, "category": "Salário"},
]

FIXED = [
    {"description": "Educação 1", "amount": 900.0, "category": "Educação"},
    {"description": "Plano de saúde", "amount": 650.0, "category": "Saúde"},
    {"description": "Educação 2", "amount": 180.0, "category": "Educação"},
    {"description": "Educação 3", "amount": 200.0, "category": "Educação"},
    {"description": "Cuidados de saúde", "amount": 400.0, "category": "Saúde"},
    {"description": "Proteção 1", "amount": 150.0, "category": "Proteção"},
    {"description": "Proteção 2", "amount": 120.0, "category": "Proteção"},
]

ALLOCATIONS = [
    {
        "key": "living",
        "description": "Despesas variáveis essenciais",
        "amount": 2000.0,
        "category": "Orçamento de vida",
        "notes": "Provisão inicial: alimentação, casa, transporte, lazer e pessoais.",
    },
    {
        "key": "emergency",
        "description": "Reserva de emergência",
        "amount": 1000.0,
        "category": "Reserva",
        "notes": "Manter até formar 6 meses do custo essencial; depois redirecionar.",
    },
    {
        "key": "retirement",
        "description": "Aposentadoria turbinada",
        "amount": 1500.0,
        "category": "Aposentadoria",
        "notes": "Aporte de longo prazo de 20% da renda; carteira depende do perfil.",
    },
    {
        "key": "property",
        "description": "Fundo para imóvel próprio",
        "amount": 1500.0,
        "category": "Imóvel",
        "notes": "Fundo separado para entrada e custos de compra.",
    },
    {
        "key": "investments",
        "description": "Investimentos diversificados",
        "amount": 400.0,
        "category": "Investimentos",
        "notes": "Aportes fora do fundo do imóvel e da aposentadoria.",
    },
]

LEGACY_ALIASES = {
    "Educação 1": ["Escola"],
    "Salário demonstrativo": ["Salário anterior 1"],
    "Renda autônoma 1": ["Renda anterior 1"],
}

CDI_ANNUAL_RATE = float(os.getenv("ORCA_CDI_ANNUAL_RATE", "0.10"))


def _previous_month(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    absolute = year * 12 + number - 2
    return f"{absolute // 12:04d}-{absolute % 12 + 1:02d}"


def _property_projection(monthly_amount: float, months: int = 60) -> list[dict]:
    monthly_rate = (1 + CDI_ANNUAL_RATE) ** (1 / 12) - 1
    balance = 0.0
    projection = []
    for month in range(months + 1):
        if month:
            balance = balance * (1 + monthly_rate) + monthly_amount
        projection.append(
            {
                "month": month,
                "contributed": round(monthly_amount * month, 2),
                "balance": round(balance, 2),
            }
        )
    return projection


def build_budget_plan(
    connection: sqlite3.Connection | None = None, month: str | None = None
) -> dict:
    income = INCOME
    fixed = FIXED
    if connection and month:
        query, params = active_entries_query(month)
        rows = connection.execute(query, params).fetchall()
        income = [
            {
                "description": row["description"],
                "amount": row["amount"],
                "category": row["category"],
            }
            for row in rows
            if row["entry_type"] == "income"
        ] or INCOME
        fixed = [
            {
                "description": row["description"],
                "amount": row["amount"],
                "category": row["category"],
            }
            for row in rows
            if row["entry_type"] == "expense" and row["recurring"]
        ] or FIXED

    income_total = round(sum(item["amount"] for item in income), 2)
    fixed_total = round(sum(item["amount"] for item in fixed), 2)
    allocation_scale = income_total / sum(item["amount"] for item in INCOME)
    allocations = [
        {
            **item,
            "amount": round(item["amount"] * allocation_scale, 2),
            "percentage": round(item["amount"] * allocation_scale / income_total * 100, 1),
        }
        for item in ALLOCATIONS
    ]
    base_plan_total = round(fixed_total + sum(item["amount"] for item in allocations), 2)
    surplus = max(0, round(income_total - base_plan_total, 2))
    property_allocation = next(item for item in allocations if item["key"] == "property")
    property_allocation["amount"] = round(property_allocation["amount"] + surplus, 2)
    property_allocation["percentage"] = round(
        property_allocation["amount"] / income_total * 100, 1
    )
    plan_total = round(fixed_total + sum(item["amount"] for item in allocations), 2)
    preserved_theoretical = round(
        sum(
            item["amount"]
            for item in allocations
            if item["key"] in {"emergency", "retirement", "property", "investments"}
        ),
        2,
    )
    return {
        "income": income,
        "income_total": income_total,
        "fixed": fixed,
        "fixed_total": fixed_total,
        "allocations": allocations,
        "plan_total": plan_total,
        "free_balance": round(income_total - plan_total, 2),
        "preserved_theoretical": {
            "description": "Renda total preservada teórica",
            "amount": preserved_theoretical,
            "percentage": round(preserved_theoretical / income_total * 100, 1),
        },
        "property": next(item for item in allocations if item["key"] == "property"),
        "retirement": next(item for item in allocations if item["key"] == "retirement"),
        "investments": next(item for item in allocations if item["key"] == "investments"),
        "cdi_annual_rate": CDI_ANNUAL_RATE,
        "property_projection": _property_projection(property_allocation["amount"]),
    }


def seed_personal_plan(connection: sqlite3.Connection, start_month: str) -> bool:
    already_seeded = connection.execute(
        "SELECT 1 FROM app_meta WHERE key = 'personal_plan_v1'"
    ).fetchone()
    if already_seeded:
        connection.execute(
            """
            UPDATE entries SET start_month = ?, end_month = ?
            WHERE notes = 'Importado da planilha original.'
              AND description IN ('Gasolina', 'IPVA')
            """,
            (f"{start_month[:4]}-01", _previous_month(start_month)),
        )
        connection.commit()
        return False

    for item in [*INCOME, *FIXED]:
        aliases = [item["description"], *LEGACY_ALIASES.get(item["description"], [])]
        row = connection.execute(
            "SELECT id FROM entries WHERE description IN ({}) ORDER BY id LIMIT 1".format(
                ",".join("?" for _ in aliases)
            ),
            aliases,
        ).fetchone()
        values = {
            **item,
            "entry_type": "income" if item in INCOME else "expense",
            "recurring": 1,
            "start_month": start_month,
            "end_month": None,
            "notes": (
                "Renda informada pelo usuário; confirme o líquido após impostos."
                if item in INCOME
                else "Gasto fixo informado pelo usuário."
            ),
        }
        if row:
            connection.execute(
                """
                UPDATE entries SET description = :description, amount = :amount,
                    entry_type = :entry_type, category = :category, recurring = 1,
                    start_month = :start_month, end_month = NULL, notes = :notes,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {**values, "id": row["id"]},
            )
        else:
            connection.execute(
                """
                INSERT INTO entries (
                    description, amount, entry_type, category, recurring,
                    start_month, end_month, notes
                ) VALUES (:description, :amount, :entry_type, :category, 1,
                    :start_month, NULL, :notes)
                """,
                values,
            )

    connection.execute(
        """
        UPDATE entries SET start_month = ?, end_month = ?
        WHERE notes = 'Importado da planilha original.'
          AND description IN ('Gasolina', 'IPVA')
        """,
        (f"{start_month[:4]}-01", _previous_month(start_month)),
    )
    connection.execute(
        "INSERT INTO app_meta (key, value) VALUES ('personal_plan_v1', 'done')"
    )
    connection.commit()
    return True
