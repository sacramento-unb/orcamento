from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    entry_type TEXT NOT NULL CHECK (entry_type IN ('expense', 'income')),
    category TEXT NOT NULL,
    recurring INTEGER NOT NULL DEFAULT 1 CHECK (recurring IN (0, 1)),
    start_month TEXT NOT NULL,
    end_month TEXT,
    notes TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    external_id TEXT,
    reconciled_entry_id INTEGER REFERENCES entries(id) ON DELETE SET NULL,
    transaction_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    movement_type TEXT NOT NULL,
    asset TEXT NOT NULL,
    quantity REAL,
    unit_price REAL,
    source_file TEXT NOT NULL DEFAULT '',
    external_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(entries)")
        }
        if "source" not in columns:
            connection.execute(
                "ALTER TABLE entries ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'"
            )
        if "external_id" not in columns:
            connection.execute("ALTER TABLE entries ADD COLUMN external_id TEXT")
        if "reconciled_entry_id" not in columns:
            connection.execute(
                """
                ALTER TABLE entries ADD COLUMN reconciled_entry_id INTEGER
                REFERENCES entries(id) ON DELETE SET NULL
                """
            )
        if "transaction_date" not in columns:
            connection.execute("ALTER TABLE entries ADD COLUMN transaction_date TEXT")
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_external_source
            ON entries(source, external_id)
            WHERE external_id IS NOT NULL
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_reconciled_month
            ON entries(reconciled_entry_id, start_month)
            WHERE reconciled_entry_id IS NOT NULL
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_investments_external_id
            ON investments(external_id)
            """
        )


def active_entries_query(month: str) -> tuple[str, tuple[str, str, str, str]]:
    return (
        """
        SELECT *
        FROM entries
        WHERE (
            (
                recurring = 1
                AND start_month <= ?
                AND (end_month IS NULL OR end_month = '' OR end_month >= ?)
            ) OR (
                recurring = 0
                AND start_month = ?
            )
        )
        AND NOT (
            recurring = 1
            AND EXISTS (
                SELECT 1
                FROM entries AS actual
                WHERE actual.reconciled_entry_id = entries.id
                  AND actual.start_month = ?
                  AND actual.entry_type = 'expense'
            )
        )
        ORDER BY entry_type, amount DESC, description COLLATE NOCASE
        """,
        (month, month, month, month),
    )
