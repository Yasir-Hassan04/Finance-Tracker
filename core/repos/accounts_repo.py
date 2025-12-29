from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.db import Database


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    type: str
    currency: str
    opening_balance_cents: int


@dataclass
class AccountsRepo:
    db: Database

    def list_accounts(self) -> list[Account]:
        rows = self.db.query_all(
            """
            SELECT id, name, type, currency, opening_balance_cents
            FROM accounts
            ORDER BY name ASC;
            """
        )
        return [
            Account(
                id=int(r["id"]),
                name=str(r["name"]),
                type=str(r["type"]),
                currency=str(r["currency"]),
                opening_balance_cents=int(r["opening_balance_cents"]),
            )
            for r in rows
        ]

    def create_account(self, name: str, type_: str, currency: str = "CAD", opening_balance_cents: int = 0) -> int:
        cur = self.db.execute(
            """
            INSERT INTO accounts(name, type, currency, opening_balance_cents)
            VALUES(?, ?, ?, ?);
            """,
            (name, type_, currency, opening_balance_cents),
        )
        return int(cur.lastrowid)

    def update_account(self, account_id: int, name: str, type_: str, currency: str, opening_balance_cents: int) -> None:
        self.db.execute(
            """
            UPDATE accounts
            SET name = ?, type = ?, currency = ?, opening_balance_cents = ?
            WHERE id = ?;
            """,
            (name, type_, currency, opening_balance_cents, account_id),
        )

    def delete_account(self, account_id: int) -> None:
        self.db.execute("DELETE FROM accounts WHERE id = ?;", (account_id,))

    def ensure_default_cash_account(self) -> int:
        row = self.db.query_one("SELECT id FROM accounts ORDER BY id ASC LIMIT 1;")
        if row is not None:
            return int(row["id"])
        return self.create_account("Cash", "cash", "CAD", 0)
