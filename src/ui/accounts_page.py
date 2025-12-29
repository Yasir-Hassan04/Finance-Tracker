from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QDialog,
    QMessageBox, QLineEdit, QComboBox, QLabel
)

from core.db import Database
from core.repos.accounts_repo import AccountsRepo, Account


class AccountsTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Type", "Currency", "Opening Balance (cents)"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[Account] = []

    def set_rows(self, rows: list[Account]) -> None:
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
        a = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return a.name
            if col == 1:
                return a.type
            if col == 2:
                return a.currency
            if col == 3:
                return str(a.opening_balance_cents)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    def row_at(self, row_index: int) -> Account | None:
        return self._rows[row_index] if 0 <= row_index < len(self._rows) else None


class AccountDialog(QDialog):
    def __init__(self, parent=None, *, title: str, initial: Account | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["chequing", "savings", "credit", "cash", "other"])
        self.currency_edit = QLineEdit()
        self.currency_edit.setPlaceholderText("CAD")
        self.opening_edit = QLineEdit()
        self.opening_edit.setPlaceholderText("0")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Type"))
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Currency"))
        layout.addWidget(self.currency_edit)

        layout.addWidget(QLabel("Opening Balance (cents)"))
        layout.addWidget(self.opening_edit)

        btns = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)

        if initial is not None:
            self.name_edit.setText(initial.name)
            idx = self.type_combo.findText(initial.type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.currency_edit.setText(initial.currency)
            self.opening_edit.setText(str(initial.opening_balance_cents))

    def get_values(self) -> tuple[str, str, str, int] | None:
        name = self.name_edit.text().strip()
        if not name:
            return None

        type_ = self.type_combo.currentText().strip()
        currency = self.currency_edit.text().strip() or "CAD"

        opening_text = self.opening_edit.text().strip() or "0"
        try:
            opening_cents = int(opening_text)
        except ValueError:
            return None

        return name, type_, currency, opening_cents


class AccountsPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.repo = AccountsRepo(db)

        root = QVBoxLayout(self)

        top = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_edit = QPushButton("Edit Selected")
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_refresh = QPushButton("Refresh")

        top.addWidget(self.btn_add)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_delete)
        top.addWidget(self.btn_refresh)
        top.addStretch()
        root.addLayout(top)

        self.table = QTableView()
        self.model = AccountsTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_add.clicked.connect(self.add_account)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_refresh.clicked.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        self.model.set_rows(self.repo.list_accounts())
        self.table.resizeColumnsToContents()

    def _selected_account(self) -> Account | None:
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return None
        return self.model.row_at(idxs[0].row())

    def add_account(self) -> None:
        dlg = AccountDialog(self, title="Add Account")
        if dlg.exec() != QDialog.Accepted:
            return

        vals = dlg.get_values()
        if vals is None:
            QMessageBox.warning(self, "Invalid input", "Please fill fields correctly.")
            return

        name, type_, currency, opening_cents = vals
        try:
            self.repo.create_account(name, type_, currency, opening_cents)
        except Exception:
            QMessageBox.warning(self, "Create failed", "Account name must be unique.")
            return

        self.refresh()

    def edit_selected(self) -> None:
        acc = self._selected_account()
        if acc is None:
            return

        dlg = AccountDialog(self, title="Edit Account", initial=acc)
        if dlg.exec() != QDialog.Accepted:
            return

        vals = dlg.get_values()
        if vals is None:
            QMessageBox.warning(self, "Invalid input", "Please fill fields correctly.")
            return

        name, type_, currency, opening_cents = vals
        try:
            self.repo.update_account(acc.id, name, type_, currency, opening_cents)
        except Exception:
            QMessageBox.warning(self, "Update failed", "Account name must be unique.")
            return

        self.refresh()

    def delete_selected(self) -> None:
        acc = self._selected_account()
        if acc is None:
            return

        if QMessageBox.question(self, "Delete account", f"Delete '{acc.name}'?") != QMessageBox.Yes:
            return

        self.repo.delete_account(acc.id)
        self.refresh()
