from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QPushButton,
    QMessageBox,
)

from core.db import Database
from core.repos.accounts_repo import AccountsRepo
from core.repos.categories_repo import CategoriesRepo
from core.repos.transactions_repo import TransactionsRepo, dollars_to_cents


class AddTransactionDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Add Transaction")
        self.setMinimumWidth(420)

        self.accounts_repo = AccountsRepo(db)
        self.categories_repo = CategoriesRepo(db)
        self.tx_repo = TransactionsRepo(db)

        root = QVBoxLayout(self)

        root.addWidget(QLabel("Date"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        root.addWidget(self.date_edit)

        root.addWidget(QLabel("Amount (use - for expense, + for income)"))
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("-5.99")
        root.addWidget(self.amount_edit)

        root.addWidget(QLabel("Account"))
        self.account_combo = QComboBox()
        root.addWidget(self.account_combo)

        root.addWidget(QLabel("Category (optional)"))
        self.category_combo = QComboBox()
        root.addWidget(self.category_combo)

        root.addWidget(QLabel("Description (optional)"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("e.g., Coffee")
        root.addWidget(self.desc_edit)

        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

        self.created_tx_id: Optional[int] = None
        self._load_dropdowns()

    def _load_dropdowns(self) -> None:
        default_id = self.accounts_repo.ensure_default_cash_account()

        accounts = self.accounts_repo.list_accounts()
        self.account_combo.clear()
        for a in accounts:
            self.account_combo.addItem(a.name, a.id)

        idx = self.account_combo.findData(default_id)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)

        categories = self.categories_repo.list_categories()
        self.category_combo.clear()
        self.category_combo.addItem("Uncategorized", None)
        for c in categories:
            self.category_combo.addItem(f"{c.name} ({c.kind})", c.id)

    def _on_save(self) -> None:
        amt_text = self.amount_edit.text().strip()
        if not amt_text:
            QMessageBox.warning(self, "Missing amount", "Please enter an amount (e.g., -5.99).")
            return

        try:
            amount = float(amt_text)
        except ValueError:
            QMessageBox.warning(self, "Invalid amount", "Amount must be a number (e.g., -5.99).")
            return

        if self.account_combo.currentData() is None:
            QMessageBox.warning(self, "Missing account", "Please choose an account.")
            return

        amount_cents = dollars_to_cents(amount)
        account_id = int(self.account_combo.currentData())
        category_id = self.category_combo.currentData()
        description = self.desc_edit.text().strip()
        occurred_on = self.date_edit.date().toString("yyyy-MM-dd")

        self.created_tx_id = self.tx_repo.add_transaction(
            account_id=account_id,
            category_id=category_id,
            amount_cents=amount_cents,
            occurred_on=occurred_on,
            description=description,
        )
        self.accept()
