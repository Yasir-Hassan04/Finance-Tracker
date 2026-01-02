from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTableView
)

from core.db import Database
from core.repos.reports_repo import ReportsRepo


def cents_to_dollars_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}${cents // 100}.{cents % 100:02d}"


@dataclass(frozen=True)
class CategorySpendRow:
    category_name: str
    spent_cents: int


class CategorySpendModel(QAbstractTableModel):
    HEADERS = ["Category", "Spent"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[CategorySpendRow] = []

    def set_rows(self, rows: list[CategorySpendRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        r = self._rows[index.row()]
        c = index.column()

        if role == Qt.DisplayRole:
            if c == 0:
                return r.category_name
            if c == 1:
                return cents_to_dollars_str(r.spent_cents)

        if role == Qt.TextAlignmentRole and c == 1:
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)


class ReportsPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.repo = ReportsRepo(db)

        root = QVBoxLayout(self)

        top = QHBoxLayout()

        self.month_combo = QComboBox()
        for m in self._recent_months(24):
            self.month_combo.addItem(m, m)

        self.btn_refresh = QPushButton("Refresh")

        top.addWidget(QLabel("Month"))
        top.addWidget(self.month_combo)
        top.addWidget(self.btn_refresh)
        top.addStretch()
        root.addLayout(top)

        # Totals row
        totals_row = QHBoxLayout()
        self.lbl_income = QLabel("Income: $0.00")
        self.lbl_expense = QLabel("Expense: $0.00")
        self.lbl_net = QLabel("Net: $0.00")

        totals_row.addWidget(self.lbl_income)
        totals_row.addWidget(self.lbl_expense)
        totals_row.addWidget(self.lbl_net)
        totals_row.addStretch()
        root.addLayout(totals_row)

        # Table
        self.table = QTableView()
        self.model = CategorySpendModel()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_refresh.clicked.connect(self.refresh)
        self.month_combo.currentIndexChanged.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        month = str(self.month_combo.currentData())

        totals = self.repo.month_totals(month)
        self.lbl_income.setText(f"Income: {cents_to_dollars_str(totals.income_cents)}")
        self.lbl_expense.setText(f"Expense: {cents_to_dollars_str(totals.expense_cents)}")
        self.lbl_net.setText(f"Net: {cents_to_dollars_str(totals.net_cents)}")

        rows = [
            CategorySpendRow(category_name=name, spent_cents=spent)
            for (name, spent) in self.repo.month_spend_by_category(month)
        ]
        self.model.set_rows(rows)
        self.table.resizeColumnsToContents()

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
