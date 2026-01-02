from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QMessageBox
)

from core.db import Database
from core.repos.accounts_repo import AccountsRepo
from core.repos.categories_repo import CategoriesRepo
from core.repos.transactions_repo import TransactionsRepo


class EditTransactionDialog(QDialog):
    def __init__(self, db: Database, transaction_id: int, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.transaction_id = transaction_id

        self.setWindowTitle("Edit Transaction")
        self.setMinimumWidth(420)

        self.accounts_repo = AccountsRepo(db)
        self.categories_repo = CategoriesRepo(db)
        self.tx_repo = TransactionsRepo(db)

        tx = self.tx_repo.get_transaction(transaction_id)
        if tx is None:
            QMessageBox.warning(self, "Not found", "Transaction no longer exists.")
            self.reject()
            return

        root = QVBoxLayout(self)

        # Date
        root.addWidget(QLabel("Date"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        y, m, d = [int(x) for x in tx["occurred_on"].split("-")]
        self.date_edit.setDate(QDate(y, m, d))
        root.addWidget(self.date_edit)

        # Amount
        root.addWidget(QLabel("Amount (use - for expense, + for income)"))
        self.amount_edit = QLineEdit()
        self.amount_edit.setText(f"{tx['amount_cents'] / 100:.2f}")
        root.addWidget(self.amount_edit)

        # Account
        root.addWidget(QLabel("Account"))
        self.account_combo = QComboBox()
        root.addWidget(self.account_combo)

        # Category
        root.addWidget(QLabel("Category (optional)"))
        self.category_combo = QComboBox()
        root.addWidget(self.category_combo)

        # Description
        root.addWidget(QLabel("Description (optional)"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setText(tx["description"])
        root.addWidget(self.desc_edit)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

        self._load_dropdowns(
            selected_account_id=tx["account_id"],
            selected_category_id=tx["category_id"],
        )

    def _load_dropdowns(self, selected_account_id: int, selected_category_id: Optional[int]) -> None:
        accounts = self.accounts_repo.list_accounts()
        self.account_combo.clear()
        for a in accounts:
            self.account_combo.addItem(a.name, a.id)
        idx = self.account_combo.findData(selected_account_id)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)

        cats = self.categories_repo.list_categories()
        self.category_combo.clear()
        self.category_combo.addItem("Uncategorized", None)
        for c in cats:
            self.category_combo.addItem(f"{c.name} ({c.kind})", c.id)

        if selected_category_id is None:
            self.category_combo.setCurrentIndex(0)
        else:
            idx2 = self.category_combo.findData(selected_category_id)
            if idx2 >= 0:
                self.category_combo.setCurrentIndex(idx2)

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

        amount_cents = int(round(amount * 100))
        account_id = int(self.account_combo.currentData())
        category_id = self.category_combo.currentData()
        description = self.desc_edit.text().strip()
        occurred_on = self.date_edit.date().toString("yyyy-MM-dd")

        self.tx_repo.update_transaction(
            transaction_id=self.transaction_id,
            account_id=account_id,
            category_id=category_id,
            amount_cents=amount_cents,
            occurred_on=occurred_on,
            description=description,
        )
        self.accept()
