from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame
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

        self.range_combo = QComboBox()
        self.range_combo.addItem("1 month", 1)
        self.range_combo.addItem("Last 3 months", 3)
        self.range_combo.addItem("Last 6 months", 6)
        self.range_combo.addItem("Last 12 months", 12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Spending", "spend")  # expenses only
        self.mode_combo.addItem("Income", "income")   # income only
        self.mode_combo.addItem("Net", "net")         # income - spending

        self.topn_combo = QComboBox()
        for n in (5, 10, 15, 20):
            self.topn_combo.addItem(f"Top {n}", n)

        self.uncat_combo = QComboBox()
        self.uncat_combo.addItem("Include", True)
        self.uncat_combo.addItem("Hide", False)

        top.addWidget(QLabel("Month"))
        top.addWidget(self.month_combo)
        top.addWidget(QLabel("Range"))
        top.addWidget(self.range_combo)
        top.addWidget(QLabel("Mode"))
        top.addWidget(self.mode_combo)
        top.addWidget(QLabel("Show"))
        top.addWidget(self.topn_combo)
        top.addWidget(QLabel("Uncategorized"))
        top.addWidget(self.uncat_combo)
        top.addStretch()
        root.addLayout(top)

        # Totals row
        totals = QHBoxLayout()
        self.lbl_income = QLabel("Income: $0.00")
        self.lbl_spend = QLabel("Spending: $0.00")
        self.lbl_net = QLabel("Net: $0.00")

        for w in (self.lbl_income, self.lbl_spend, self.lbl_net):
            w.setStyleSheet("font-size: 13px; color: #dddddd;")

        totals.addWidget(self.lbl_income)
        totals.addSpacing(16)
        totals.addWidget(self.lbl_spend)
        totals.addSpacing(16)
        totals.addWidget(self.lbl_net)
        totals.addStretch()
        root.addLayout(totals)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        root.addWidget(line)

        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        root.addWidget(self.canvas, 1)

        self.month_combo.currentIndexChanged.connect(self.refresh)
        self.range_combo.currentIndexChanged.connect(self.refresh)
        self.mode_combo.currentIndexChanged.connect(self.refresh)
        self.topn_combo.currentIndexChanged.connect(self.refresh)
        self.uncat_combo.currentIndexChanged.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        month = str(self.month_combo.currentData())
        months_back = int(self.range_combo.currentData())
        mode = str(self.mode_combo.currentData())  # spend / income / net
        topn = int(self.topn_combo.currentData())
        include_uncat = bool(self.uncat_combo.currentData())

        inc_cents, spend_cents, net_cents = self._month_totals(month, months_back)
        self.lbl_income.setText(f"Income: ${inc_cents / 100:.2f}")
        self.lbl_spend.setText(f"Spending: ${spend_cents / 100:.2f}")
        self.lbl_net.setText(f"Net: ${net_cents / 100:.2f}")

        rows = self._category_rows(month, months_back, mode, include_uncat)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not rows:
            ax.text(0.5, 0.5, "No data for this range.", ha="center", va="center")
            ax.set_axis_off()
            self.canvas.draw()
            return

        # sort and keep top N (by absolute magnitude so net works nicely)
        rows = sorted(rows, key=lambda r: abs(r.cents), reverse=True)[:topn]

        cats = [r.category for r in rows]
        vals = [cents_to_dollars(r.cents) for r in rows]

        ax.bar(cats, vals)
        ax.axhline(0)
        title_range = month if months_back == 1 else f"{month} (last {months_back} months)"
        ax.set_title(f"{self._mode_title(mode)} by Category ({title_range})")
        ax.set_ylabel("Dollars")
        ax.tick_params(axis="x", rotation=35)

        self.figure.tight_layout()
        self.canvas.draw()

    # ---------------- Queries ----------------
    def _category_rows(self, month: str, months_back: int, mode: str, include_uncat: bool) -> list[CategoryRow]:
        start, end = self._range_bounds(month, months_back)

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
        out = [CategoryRow(category=str(r["category"]), cents=int(r["cents"])) for r in rows]
        if not include_uncat:
            out = [r for r in out if r.category != "Uncategorized"]
        return out

    def _month_totals(self, month: str, months_back: int) -> tuple[int, int, int]:
        start, end = self._range_bounds(month, months_back)

        row = self.db.query_one(
            """
            SELECT
              SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END) AS income_cents,
              SUM(CASE WHEN amount_cents < 0 THEN -amount_cents ELSE 0 END) AS spend_cents,
              SUM(amount_cents) AS net_cents
            FROM transactions
            WHERE occurred_on >= ? AND occurred_on < ?;
            """,
            (start, end),
        )
        income = int(row["income_cents"] or 0)
        spend = int(row["spend_cents"] or 0)
        net = int(row["net_cents"] or 0)
        return income, spend, net

    @staticmethod
    def _range_bounds(month: str, months_back: int) -> tuple[str, str]:
        # end = first day of next month
        y = int(month[:4])
        m = int(month[5:7])
        end_y = y + 1 if m == 12 else y
        end_m = 1 if m == 12 else (m + 1)
        end = f"{end_y:04d}-{end_m:02d}-01"

        # start = first day of (month - (months_back-1))
        start_y, start_m = y, m
        for _ in range(months_back - 1):
            start_m -= 1
            if start_m == 0:
                start_m = 12
                start_y -= 1
        start = f"{start_y:04d}-{start_m:02d}-01"

        return start, end

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
