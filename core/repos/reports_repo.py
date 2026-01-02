from __future__ import annotations

from dataclasses import dataclass

from core.db import Database


@dataclass(frozen=True)
class MonthTotals:
    month: str          # YYYY-MM
    income_cents: int   # positive
    expense_cents: int  # positive
    net_cents: int      # income - expense


@dataclass
class ReportsRepo:
    db: Database

    def month_totals(self, month: str) -> MonthTotals:
        # income = sum of positive amounts
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

        # expenses are stored negative -> convert to positive total
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

        return MonthTotals(
            month=month,
            income_cents=income,
            expense_cents=expense,
            net_cents=income - expense,
        )

    def month_spend_by_category(self, month: str) -> list[tuple[str, int]]:
        """
        Returns list of (category_name, spent_cents) sorted desc by spent.
        spent_cents is positive.
        """
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
            ORDER BY ABS(COALESCE(SUM(t.amount_cents), 0)) DESC;
            """,
            (month,),
        )

        out: list[tuple[str, int]] = []
        for r in rows:
            name = str(r["category_name"])
            total = int(r["total_cents"])
            out.append((name, abs(total)))
        return out
