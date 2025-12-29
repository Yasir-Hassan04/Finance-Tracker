from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.db import Database


@dataclass(frozen=True)
class Budget:
    id: int
    category_id: int
    month: str          # YYYY-MM
    limit_cents: int


@dataclass
class BudgetsRepo:
    db: Database

    def upsert_budget(self, category_id: int, month: str, limit_cents: int) -> int:
        # If exists, update; else insert
        existing = self.db.query_one(
            "SELECT id FROM budgets WHERE category_id = ? AND month = ?;",
            (category_id, month),
        )
        if existing is None:
            cur = self.db.execute(
                "INSERT INTO budgets(category_id, month, limit_cents) VALUES(?, ?, ?);",
                (category_id, month, limit_cents),
            )
            return int(cur.lastrowid)

        budget_id = int(existing["id"])
        self.db.execute(
            "UPDATE budgets SET limit_cents = ? WHERE id = ?;",
            (limit_cents, budget_id),
        )
        return budget_id

    def delete_budget(self, budget_id: int) -> None:
        self.db.execute("DELETE FROM budgets WHERE id = ?;", (budget_id,))

    def list_budgets_for_month(self, month: str) -> list[Budget]:
        rows = self.db.query_all(
            """
            SELECT id, category_id, month, limit_cents
            FROM budgets
            WHERE month = ?
            ORDER BY category_id ASC;
            """,
            (month,),
        )
        return [
            Budget(
                id=int(r["id"]),
                category_id=int(r["category_id"]),
                month=str(r["month"]),
                limit_cents=int(r["limit_cents"]),
            )
            for r in rows
        ]

    def get_budget(self, category_id: int, month: str) -> Optional[Budget]:
        r = self.db.query_one(
            """
            SELECT id, category_id, month, limit_cents
            FROM budgets
            WHERE category_id = ? AND month = ?;
            """,
            (category_id, month),
        )
        if r is None:
            return None
        return Budget(
            id=int(r["id"]),
            category_id=int(r["category_id"]),
            month=str(r["month"]),
            limit_cents=int(r["limit_cents"]),
        )

    def month_spend_by_category(self, month: str) -> dict[int, int]:
        """
        Returns {category_id: spent_cents} for the month.
        Assumes expenses are stored as negative cents in transactions.
        We report spend as a POSITIVE number (abs sum of negatives).
        """
        rows = self.db.query_all(
            """
            SELECT category_id, SUM(amount_cents) AS total_cents
            FROM transactions
            WHERE substr(occurred_on, 1, 7) = ?
              AND category_id IS NOT NULL
            GROUP BY category_id;
            """,
            (month,),
        )

        out: dict[int, int] = {}
        for r in rows:
            cat_id = int(r["category_id"])
            total = int(r["total_cents"]) if r["total_cents"] is not None else 0
            # total will be negative for expense-heavy categories
            out[cat_id] = abs(total) if total < 0 else total
        return out
