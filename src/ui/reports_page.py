from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox

from matplotlib.figure import Figure

# backend import (works across setups)
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except Exception:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from core.db import Database


@dataclass(frozen=True)
class CategoryRow:
    category: str
    cents: int  # may be positive or negative depending on mode


def cents_to_dollars(cents: int) -> float:
    return int(cents) / 100.0


class ReportsPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db

        root = QVBoxLayout(self)

        top = QHBoxLayout()

        self.month_combo = QComboBox()
        for m in self._recent_months(18):
            self.month_combo.addItem(m, m)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Spending", "spend")  # expenses only
        self.mode_combo.addItem("Income", "income")   # income only
        self.mode_combo.addItem("Net", "net")         # income - spending

        self.topn_combo = QComboBox()
        for n in (5, 10, 15, 20):
            self.topn_combo.addItem(f"Top {n}", n)

        top.addWidget(QLabel("Month"))
        top.addWidget(self.month_combo)
        top.addWidget(QLabel("Mode"))
        top.addWidget(self.mode_combo)
        top.addWidget(QLabel("Show"))
        top.addWidget(self.topn_combo)
        top.addStretch()
        root.addLayout(top)

        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        root.addWidget(self.canvas, 1)

        self.month_combo.currentIndexChanged.connect(self.refresh)
        self.mode_combo.currentIndexChanged.connect(self.refresh)
        self.topn_combo.currentIndexChanged.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        month = str(self.month_combo.currentData())
        mode = str(self.mode_combo.currentData())  # spend / income / net
        topn = int(self.topn_combo.currentData())

        rows = self._category_rows(month, mode)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not rows:
            ax.text(0.5, 0.5, "No data for this month.", ha="center", va="center")
            ax.set_axis_off()
            self.canvas.draw()
            return

        # sort and keep top N (by absolute magnitude so net works nicely)
        rows = sorted(rows, key=lambda r: abs(r.cents), reverse=True)[:topn]

        cats = [r.category for r in rows]
        vals = [cents_to_dollars(r.cents) for r in rows]

        ax.bar(cats, vals)
        ax.axhline(0)  # helpful for Net mode
        ax.set_title(f"{self._mode_title(mode)} by Category ({month})")
        ax.set_ylabel("Dollars")
        ax.tick_params(axis="x", rotation=35)

        self.figure.tight_layout()
        self.canvas.draw()

    def _category_rows(self, month: str, mode: str) -> list[CategoryRow]:
        start = f"{month}-01"
        y = int(month[:4])
        m = int(month[5:7])
        end = f"{y+1:04d}-01-01" if m == 12 else f"{y:04d}-{m+1:02d}-01"

        if mode == "spend":
            sql = """
                SELECT COALESCE(c.name, 'Uncategorized') AS category,
                       SUM(CASE WHEN t.amount_cents < 0 THEN -t.amount_cents ELSE 0 END) AS cents
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.occurred_on >= ? AND t.occurred_on < ?
                GROUP BY category
                HAVING cents > 0
                ORDER BY cents DESC;
            """
        elif mode == "income":
            sql = """
                SELECT COALESCE(c.name, 'Uncategorized') AS category,
                       SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) AS cents
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.occurred_on >= ? AND t.occurred_on < ?
                GROUP BY category
                HAVING cents > 0
                ORDER BY cents DESC;
            """
        else:  # net
            sql = """
                SELECT COALESCE(c.name, 'Uncategorized') AS category,
                       SUM(t.amount_cents) AS cents
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.occurred_on >= ? AND t.occurred_on < ?
                GROUP BY category
                HAVING cents != 0
                ORDER BY ABS(cents) DESC;
            """

        rows = self.db.query_all(sql, (start, end))
        return [CategoryRow(category=str(r["category"]), cents=int(r["cents"])) for r in rows]

    @staticmethod
    def _mode_title(mode: str) -> str:
        if mode == "spend":
            return "Spending"
        if mode == "income":
            return "Income"
        return "Net"

    @staticmethod
    def _recent_months(n: int) -> list[str]:
        today = date.today()
        y, m = today.year, today.month
        out: list[str] = []
        for _ in range(n):
            out.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        return out
