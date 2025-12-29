from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTableView, QMessageBox
)

from core.db import Database
from core.repos.budgets_repo import BudgetsRepo
from core.repos.categories_repo import CategoriesRepo


@dataclass(frozen=True)
class BudgetRow:
    category_id: int
    category_name: str
    limit_cents: int
    spent_cents: int

    @property
    def remaining_cents(self) -> int:
        return self.limit_cents - self.spent_cents


def cents_to_dollars_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}${cents // 100}.{cents % 100:02d}"


class BudgetsTableModel(QAbstractTableModel):
    HEADERS = ["Category", "Limit", "Spent", "Remaining"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[BudgetRow] = []

    def set_rows(self, rows: list[BudgetRow]) -> None:
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
                return cents_to_dollars_str(r.limit_cents)
            if c == 2:
                return cents_to_dollars_str(r.spent_cents)
            if c == 3:
                return cents_to_dollars_str(r.remaining_cents)

        if role == Qt.TextAlignmentRole and c in (1, 2, 3):
            return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.ForegroundRole and r.remaining_cents < 0:
            return QColor("red")

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)


class BudgetsPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.budgets_repo = BudgetsRepo(db)
        self.categories_repo = CategoriesRepo(db)

        root = QVBoxLayout(self)

        top = QHBoxLayout()

        self.month_combo = QComboBox()
        for m in self._recent_months(18):
            self.month_combo.addItem(m, m)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Only active (budget or spend)", "active")
        self.filter_combo.addItem("All categories", "all")

        self.category_combo = QComboBox()
        self._load_categories()

        self.limit_edit = QLineEdit()
        self.limit_edit.setPlaceholderText("e.g., 500.00")

        self.btn_save = QPushButton("Save budget")
        self.btn_delete = QPushButton("Delete budget")
        self.btn_refresh = QPushButton("Refresh")

        top.addWidget(QLabel("Month"))
        top.addWidget(self.month_combo)
        top.addWidget(QLabel("View"))
        top.addWidget(self.filter_combo)
        top.addWidget(QLabel("Category"))
        top.addWidget(self.category_combo, 1)
        top.addWidget(QLabel("Limit ($)"))
        top.addWidget(self.limit_edit)
        top.addWidget(self.btn_save)
        top.addWidget(self.btn_delete)
        top.addWidget(self.btn_refresh)
        root.addLayout(top)

        self.table = QTableView()
        self.model = BudgetsTableModel()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_save.clicked.connect(self.save_budget)
        self.btn_delete.clicked.connect(self.delete_budget)
        self.btn_refresh.clicked.connect(self.refresh)
        self.month_combo.currentIndexChanged.connect(self.refresh)
        self.filter_combo.currentIndexChanged.connect(self.refresh)

        self.refresh()

    def _load_categories(self) -> None:
        self.category_combo.clear()
        cats = self.categories_repo.list_categories()
        cats = [c for c in cats if c.kind == "expense"]
        for c in cats:
            self.category_combo.addItem(c.name, c.id)

    def save_budget(self) -> None:
        month = str(self.month_combo.currentData())
        cat_id = self.category_combo.currentData()

        if cat_id is None:
            QMessageBox.warning(self, "Missing category", "Choose a category.")
            return

        text = self.limit_edit.text().strip().replace("$", "")
        if not text:
            QMessageBox.warning(self, "Missing limit", "Enter a limit like 500.00")
            return

        try:
            limit_cents = self._dollars_to_cents(text)
        except ValueError:
            QMessageBox.warning(self, "Invalid limit", "Limit must be a number like 500.00")
            return

        self.budgets_repo.upsert_budget(int(cat_id), month, limit_cents)
        self.limit_edit.setText("")
        self.refresh()

    def delete_budget(self) -> None:
        month = str(self.month_combo.currentData())
        cat_id = self.category_combo.currentData()
        if cat_id is None:
            return

        b = self.budgets_repo.get_budget(int(cat_id), month)
        if b is None:
            QMessageBox.information(self, "No budget", "No budget exists for that category/month.")
            return

        self.budgets_repo.delete_budget(b.id)
        self.refresh()

    def refresh(self) -> None:
        month = str(self.month_combo.currentData())
        view = str(self.filter_combo.currentData())  # "active" or "all"

        cats = self.categories_repo.list_categories()
        cats = [c for c in cats if c.kind == "expense"]

        budgets = self.budgets_repo.list_budgets_for_month(month)
        budget_by_cat: dict[int, int] = {b.category_id: b.limit_cents for b in budgets}

        spent_by_cat = self.budgets_repo.month_spend_by_category(month)

        rows: list[BudgetRow] = []
        for c in cats:
            limit = budget_by_cat.get(c.id, 0)
            spent = spent_by_cat.get(c.id, 0)

            if view == "active" and limit == 0 and spent == 0:
                continue

            rows.append(BudgetRow(
                category_id=c.id,
                category_name=c.name,
                limit_cents=limit,
                spent_cents=spent,
            ))

        rows.sort(key=lambda r: (r.remaining_cents >= 0, r.category_name.lower()))
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

    @staticmethod
    def _dollars_to_cents(s: str) -> int:
        val = float(s)
        return int(round(val * 100))
