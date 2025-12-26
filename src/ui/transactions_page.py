from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QDialog,
)

from core.db import Database
from core.repos.transactions_repo import TransactionsRepo, cents_to_dollars_str
from src.ui.add_transaction_dialog import AddTransactionDialog


class TransactionsTableModel(QAbstractTableModel):
    HEADERS = ["Date", "Description", "Account", "Category", "Amount"]

    def __init__(self) -> None:
        super().__init__()
        self._rows = []

    def set_rows(self, rows) -> None:
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

        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return row.occurred_on
            if col == 1:
                return row.description
            if col == 2:
                return row.account_name
            if col == 3:
                return row.category_name
            if col == 4:
                return cents_to_dollars_str(row.amount_cents)

        if role == Qt.TextAlignmentRole and col == 4:
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    def row_at(self, row_index: int):
        return self._rows[row_index] if 0 <= row_index < len(self._rows) else None


class TransactionsPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.repo = TransactionsRepo(db)

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_refresh = QPushButton("Refresh")
        self.btn_delete = QPushButton("Delete Selected")
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_delete)
        top.addStretch()
        root.addLayout(top)

        self.table = QTableView()
        self.model = TransactionsTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_delete.clicked.connect(self.delete_selected)

        self.refresh()

    def open_add_dialog(self) -> None:
        dlg = AddTransactionDialog(self.db, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def refresh(self) -> None:
        rows = self.repo.list_transactions(limit=500)
        self.model.set_rows(rows)
        self.table.resizeColumnsToContents()

    def delete_selected(self) -> None:
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return

        row_idx = idxs[0].row()
        row = self.model.row_at(row_idx)
        if row is None:
            return

        self.repo.delete_transaction(row.id)
        self.refresh()
