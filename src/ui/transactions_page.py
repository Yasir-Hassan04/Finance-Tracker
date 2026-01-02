from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
)
import csv
from pathlib import Path
from PySide6.QtWidgets import QFileDialog
from core.db import Database
import shutil
from core.db import get_db_path
from src.ui.edit_transaction_dialog import EditTransactionDialog
from core.repos.transactions_repo import TransactionsRepo, cents_to_dollars_str, dollars_to_cents
from core.repos.accounts_repo import AccountsRepo
from core.repos.categories_repo import CategoriesRepo
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

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "transactions.csv", "CSV Files (*.csv)")
        if not path:
            return

        # export exactly what is currently shown in the table
        rows = self.model._rows

        with Path(path).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Description", "Account", "Category", "Amount"])
            for r in rows:
                w.writerow([
                    r.occurred_on,
                    r.description,
                    r.account_name,
                    r.category_name,
                    cents_to_dollars_str(r.amount_cents),
                ])

    def backup_db(self) -> None:
        dst, _ = QFileDialog.getSaveFileName(self, "Save Backup", "finance_backup.db", "DB Files (*.db)")
        if not dst:
            return

        src = get_db_path()
        try:
            shutil.copy2(src, dst)
            QMessageBox.information(self, "Backup saved", f"Saved backup to:\n{dst}")
        except Exception as e:
            QMessageBox.warning(self, "Backup failed", str(e))

    def open_edit_dialog(self, index) -> None:
        row = self.model.row_at(index.row())
        if row is None:
            return
        dlg = EditTransactionDialog(self.db, transaction_id=row.id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.repo = TransactionsRepo(db)

        self.accounts_repo = AccountsRepo(db)
        self.categories_repo = CategoriesRepo(db)

        root = QVBoxLayout(self)

        # --- Buttons row ---
        top = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_apply = QPushButton("Apply")
        self.btn_clear = QPushButton("Clear")
        self.btn_export = QPushButton("Export CSV")
        top.addWidget(self.btn_export)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_backup = QPushButton("Backup DB")
        top.addWidget(self.btn_backup)
        self.btn_backup.clicked.connect(self.backup_db)

        top.addWidget(self.btn_add)
        top.addWidget(self.btn_apply)
        top.addWidget(self.btn_clear)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_delete)
        top.addStretch()
        root.addLayout(top)

        # --- Filters row ---
        filters = QHBoxLayout()

        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("From YYYY-MM-DD")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("To YYYY-MM-DD")

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Search description")

        self.min_amt = QLineEdit()
        self.min_amt.setPlaceholderText("Min $")
        self.max_amt = QLineEdit()
        self.max_amt.setPlaceholderText("Max $")

        self.account_combo = QComboBox()
        self.category_combo = QComboBox()

        filters.addWidget(QLabel("From"))
        filters.addWidget(self.date_from)
        filters.addWidget(QLabel("To"))
        filters.addWidget(self.date_to)
        filters.addWidget(QLabel("Text"))
        filters.addWidget(self.text_edit, 1)
        filters.addWidget(QLabel("Min"))
        filters.addWidget(self.min_amt)
        filters.addWidget(QLabel("Max"))
        filters.addWidget(self.max_amt)
        filters.addWidget(QLabel("Account"))
        filters.addWidget(self.account_combo)
        filters.addWidget(QLabel("Category"))
        filters.addWidget(self.category_combo)

        root.addLayout(filters)

        # --- Table ---
        self.table = QTableView()
        self.model = TransactionsTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)
        self.table.doubleClicked.connect(self.open_edit_dialog)

        # wiring
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_apply.clicked.connect(self.apply_filters)
        self.btn_clear.clicked.connect(self.clear_filters)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_delete.clicked.connect(self.delete_selected)

        self._load_filter_dropdowns()
        self.refresh()

    def _load_filter_dropdowns(self) -> None:
        # Accounts
        self.accounts_repo.ensure_default_cash_account()
        accounts = self.accounts_repo.list_accounts()
        self.account_combo.clear()
        self.account_combo.addItem("All", None)
        for a in accounts:
            self.account_combo.addItem(a.name, a.id)

        # Categories
        cats = self.categories_repo.list_categories()
        self.category_combo.clear()
        self.category_combo.addItem("All", None)
        for c in cats:
            self.category_combo.addItem(f"{c.name} ({c.kind})", c.id)

    def open_add_dialog(self) -> None:
        dlg = AddTransactionDialog(self.db, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def clear_filters(self) -> None:
        self.date_from.setText("")
        self.date_to.setText("")
        self.text_edit.setText("")
        self.min_amt.setText("")
        self.max_amt.setText("")
        self.account_combo.setCurrentIndex(0)   # All
        self.category_combo.setCurrentIndex(0)  # All
        self.refresh()

    def apply_filters(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        # collect filters
        d_from = self.date_from.text().strip() or None
        d_to = self.date_to.text().strip() or None
        text = self.text_edit.text().strip() or None

        account_id = self.account_combo.currentData()
        category_id = self.category_combo.currentData()

        min_cents = None
        max_cents = None

        try:
            if self.min_amt.text().strip():
                min_cents = dollars_to_cents(float(self.min_amt.text().strip()))
            if self.max_amt.text().strip():
                max_cents = dollars_to_cents(float(self.max_amt.text().strip()))
        except ValueError:
            QMessageBox.warning(self, "Invalid amount", "Min/Max must be numbers like 10.00")
            return

        rows = self.repo.search_transactions(
            limit=500,
            date_from=d_from,
            date_to=d_to,
            account_id=account_id,
            category_id=category_id,
            text=text,
            min_cents=min_cents,
            max_cents=max_cents,
        )
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
