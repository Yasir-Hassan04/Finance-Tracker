from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QFrame
)
from PySide6.QtCore import QAbstractTableModel, QModelIndex

from core.db import Database
from core.repos.dashboard_repo import DashboardRepo, RecentTx


def cents_to_dollars_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}${cents // 100}.{cents % 100:02d}"


class RecentTxModel(QAbstractTableModel):
    HEADERS = ["Date", "Description", "Category", "Account", "Amount"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[RecentTx] = []

    def set_rows(self, rows: list[RecentTx]) -> None:
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
                return r.occurred_on
            if c == 1:
                return r.description
            if c == 2:
                return r.category_name
            if c == 3:
                return r.account_name
            if c == 4:
                return cents_to_dollars_str(r.amount_cents)

        if role == Qt.TextAlignmentRole and c == 4:
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)


class DashboardPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.repo = DashboardRepo(db)

        root = QVBoxLayout(self)

        # header
        header = QHBoxLayout()
        self.lbl_title = QLabel("Dashboard")
        self.lbl_title.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("color: #888888;")

        self.btn_refresh = QPushButton("Refresh")

        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_sub)
        header.addWidget(self.btn_refresh)
        root.addLayout(header)

        # cards row
        cards = QHBoxLayout()
        self.card_income = self._make_card("Income", "$0.00")
        self.card_expense = self._make_card("Expense", "$0.00")
        self.card_net = self._make_card("Net", "$0.00")
        self.card_top = self._make_card("Top spend", "—")

        cards.addWidget(self.card_income)
        cards.addWidget(self.card_expense)
        cards.addWidget(self.card_net)
        cards.addWidget(self.card_top)
        root.addLayout(cards)

        # recent tx table
        root.addWidget(QLabel("Recent transactions"))
        self.table = QTableView()
        self.model = RecentTxModel()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_refresh.clicked.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        month = self.repo.current_month()
        self.lbl_sub.setText(month)

        summary = self.repo.month_summary(month)
        self._set_card_value(self.card_income, cents_to_dollars_str(summary.income_cents))
        self._set_card_value(self.card_expense, cents_to_dollars_str(summary.expense_cents))
        self._set_card_value(self.card_net, cents_to_dollars_str(summary.net_cents))

        top = self.repo.top_spend_categories(month, limit=1)
        top_text = "—"
        if top:
            name, cents = top[0]
            top_text = f"{name} ({cents_to_dollars_str(cents)})"
        self._set_card_value(self.card_top, top_text)

        recent = self.repo.recent_transactions(limit=12)
        self.model.set_rows(recent)
        self.table.resizeColumnsToContents()

    @staticmethod
    def _make_card(title: str, value: str) -> QFrame:
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        box.setStyleSheet(
            "QFrame { border-radius: 10px; background: #1f1f1f; padding: 10px; }"
            "QLabel { color: #cccccc; }"
        )

        layout = QVBoxLayout(box)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 13px; color: #888888;")
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        lbl_v.setObjectName("valueLabel")

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        layout.addStretch()
        return box

    @staticmethod
    def _set_card_value(card: QFrame, value: str) -> None:
        lbl = card.findChild(QLabel, "valueLabel")
        if lbl:
            lbl.setText(value)
