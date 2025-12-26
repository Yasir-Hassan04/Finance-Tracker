from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.db import Database


# ---------- Small helpers ----------
def dollars_to_cents(amount: float) -> int:
    # Safer than int(amount * 100) because of float rounding
    return int(round(amount * 100))


def cents_to_dollars_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents_abs = abs(cents)
    return f"{sign}${cents_abs // 100}.{cents_abs % 100:02d}"


# ---------- Lightweight “view models” ----------
@dataclass(frozen=True)
class Account:
    id: int
    name: str
    type: str
    currency: str
    opening_balance_cents: int


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    kind: str  # 'income' or 'expense'


@dataclass(frozen=True)
class TransactionRow:
    id: int
    occurred_on: str          # YYYY-MM-DD
    description: str
    account_name: str
    category_name: str        # "Uncategorized" if NULL
    amount_cents: int


# ---------- Repos ----------
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

    def ensure_default_cash_account(self) -> int:
        """
        Creates a default 'Cash' account if no accounts exist yet.
        Returns the id of an existing or newly created default account.
        """
        row = self.db.query_one("SELECT id FROM accounts ORDER BY id ASC LIMIT 1;")
        if row is not None:
            return int(row["id"])

        cur = self.db.execute(
            """
            INSERT INTO accounts(name, type, currency, opening_balance_cents)
            VALUES(?, ?, ?, ?);
            """,
            ("Cash", "cash", "CAD", 0),
        )
        return int(cur.lastrowid)


@dataclass
class CategoriesRepo:
    db: Database

    def list_categories(self, kind: Optional[str] = None) -> list[Category]:
        if kind is None:
            rows = self.db.query_all(
                "SELECT id, name, kind FROM categories ORDER BY kind ASC, name ASC;"
            )
        else:
            rows = self.db.query_all(
                "SELECT id, name, kind FROM categories WHERE kind = ? ORDER BY name ASC;",
                (kind,),
            )

        return [
            Category(id=int(r["id"]), name=str(r["name"]), kind=str(r["kind"]))
            for r in rows
        ]


@dataclass
class TransactionsRepo:
    db: Database

    def list_transactions(
        self,
        limit: int = 200,
        account_id: Optional[int] = None,
    ) -> list[TransactionRow]:
        sql = """
            SELECT
                t.id,
                t.occurred_on,
                COALESCE(t.description, '') AS description,
                a.name AS account_name,
                COALESCE(c.name, 'Uncategorized') AS category_name,
                t.amount_cents
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            LEFT JOIN categories c ON c.id = t.category_id
        """
        params: list[object] = []

        if account_id is not None:
            sql += " WHERE t.account_id = ? "
            params.append(account_id)

        sql += """
            ORDER BY t.occurred_on DESC, t.id DESC
            LIMIT ?;
        """
        params.append(limit)

        rows = self.db.query_all(sql, params)
        return [
            TransactionRow(
                id=int(r["id"]),
                occurred_on=str(r["occurred_on"]),
                description=str(r["description"]),
                account_name=str(r["account_name"]),
                category_name=str(r["category_name"]),
                amount_cents=int(r["amount_cents"]),
            )
            for r in rows
        ]

    def add_transaction(
        self,
        account_id: int,
        amount_cents: int,
        occurred_on: str,  # YYYY-MM-DD
        description: str = "",
        category_id: Optional[int] = None,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO transactions(account_id, category_id, amount_cents, description, occurred_on)
            VALUES(?, ?, ?, ?, ?);
            """,
            (account_id, category_id, amount_cents, description, occurred_on),
        )
        return int(cur.lastrowid)

    def delete_transaction(self, transaction_id: int) -> None:
        self.db.execute("DELETE FROM transactions WHERE id = ?;", (transaction_id,))
