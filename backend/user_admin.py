from __future__ import annotations

import os
import sys
from getpass import getpass

from .auth import upsert_user
from .database import connect, init_db


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m backend.user_admin USUARIO")
    username = sys.argv[1]
    password = getpass(f"Senha para {username}: ")
    init_db(os.getenv("BUDGET_DB_PATH", "data/orcamento.db"))
    with connect(os.getenv("BUDGET_DB_PATH", "data/orcamento.db")) as connection:
        upsert_user(connection, username, password)
    print(f"Usuário {username.lower()} atualizado.")


if __name__ == "__main__":
    main()
