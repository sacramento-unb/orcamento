from __future__ import annotations

import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash


def authenticate(connection: sqlite3.Connection, username: str, password: str):
    row = connection.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return None
    return {"id": row["id"], "username": row["username"]}


def upsert_user(connection: sqlite3.Connection, username: str, password: str) -> None:
    username = username.strip().lower()
    if not username or not password:
        raise ValueError("Usuário e senha são obrigatórios.")
    connection.execute(
        """
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash
        """,
        (username, generate_password_hash(password)),
    )
    connection.commit()
