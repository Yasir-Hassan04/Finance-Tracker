from __future__ import annotations


from dataclasses import dataclass
from datetime import date

from core.db import Database


@dataclass(frozen=True)
class DashboardSummary:
    month: str
    income_cents: int
    expense_cents: int
    net_cents: int


@dataclass(frozen=True)
class RecentTx:
    id: int
    occurred_on: str
    description: str
    category_name: str
    account_name: str
    amount_cents: int


@dataclass
class DashboardRepo:
    db: Database

    @staticmethod
    def current_month() -> str:
        d = date.today()
        return f"{d.year:04d}-{d.month:02d}"

    def month_summary(self, month: str) -> DashboardSummary:
        row_income = self.db.query_one(
            """
            SELECT COALESCE(SUM(amount_cents), 0) AS total
            FROM transactions
            WHERE substr(occurred_on, 1, 7) = ?
              AND amount_cents > 0;
            """,
            (month,),
        )
        income = int(row_income["total"]) if row_income else 0

        row_exp = self.db.query_one(
            """
            SELECT COALESCE(SUM(amount_cents), 0) AS total
            FROM transactions
            WHERE substr(occurred_on, 1, 7) = ?
              AND amount_cents < 0;
            """,
            (month,),
        )
        exp_raw = int(row_exp["total"]) if row_exp else 0
        expense = abs(exp_raw)

        return DashboardSummary(
            month=month,
            income_cents=income,
            expense_cents=expense,
            net_cents=income - expense,
        )

    def top_spend_categories(self, month: str, limit: int = 5) -> list[tuple[str, int]]:
        rows = self.db.query_all(
            """
            SELECT
                COALESCE(c.name, 'Uncategorized') AS category_name,
                COALESCE(SUM(t.amount_cents), 0) AS total_cents
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE substr(t.occurred_on, 1, 7) = ?
              AND t.amount_cents < 0
            GROUP BY COALESCE(c.name, 'Uncategorized')
            ORDER BY ABS(COALESCE(SUM(t.amount_cents), 0)) DESC
            LIMIT ?;
            """,
            (month, int(limit)),
        )
        return [(str(r["category_name"]), abs(int(r["total_cents"]))) for r in rows]

    def recent_transactions(self, limit: int = 10) -> list[RecentTx]:
        rows = self.db.query_all(
            """
            SELECT
                t.id,
                t.occurred_on,
                COALESCE(t.description, '') AS description,
                COALESCE(c.name, 'Uncategorized') AS category_name,
                a.name AS account_name,
                t.amount_cents
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            LEFT JOIN categories c ON c.id = t.category_id
            ORDER BY t.occurred_on DESC, t.id DESC
            LIMIT ?;
            """,
            (int(limit),),
        )
        out: list[RecentTx] = []
        for r in rows:
            out.append(
                RecentTx(
                    id=int(r["id"]),
                    occurred_on=str(r["occurred_on"]),
                    description=str(r["description"]),
                    category_name=str(r["category_name"]),
                    account_name=str(r["account_name"]),
                    amount_cents=int(r["amount_cents"]),
                )
            )
        return out
