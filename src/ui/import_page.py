from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableView,
    QFileDialog,
    QComboBox,
    QMessageBox,
)

from core.db import Database
from core.repos.accounts_repo import AccountsRepo
from core.repos.transactions_repo import TransactionsRepo


class CsvPreviewModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.headers: list[str] = []
        self.rows: list[list[str]] = []

    def set_data(self, headers: list[str], rows: list[list[str]]) -> None:
        self.beginResetModel()
        self.headers = headers
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            r = index.row()
            c = index.column()
            if r < len(self.rows) and c < len(self.rows[r]):
                return self.rows[r][c]
            return ""
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headers[section] if section < len(self.headers) else ""
        return str(section + 1)


class ImportPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db

        self.csv_path: Path | None = None
        self._headers: list[str] = []
        self._rows: list[list[str]] = []
        self.tx_repo = TransactionsRepo(self.db)

        root = QVBoxLayout(self)

        top = QHBoxLayout()

        self.btn_choose = QPushButton("Choose CSV")
        self.path_label = QLabel("No file selected")
        self.path_label.setStyleSheet("color: #888888;")

        self.btn_preview = QPushButton("Preview Import")
        self.btn_preview.setEnabled(False)

        self.btn_import = QPushButton("Import")
        self.btn_import.setEnabled(False)

        top.addWidget(self.btn_choose)
        top.addWidget(self.path_label, 1)
        top.addWidget(self.btn_preview)
        top.addWidget(self.btn_import)
        root.addLayout(top)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888888;")
        root.addWidget(self.status_label)

        map_row = QHBoxLayout()

        self.date_col = QComboBox()
        self.desc_col = QComboBox()

        self.amount_col = QComboBox()
        self.debit_col = QComboBox()
        self.credit_col = QComboBox()

        self.account_combo = QComboBox()

        map_row.addWidget(QLabel("Date"))
        map_row.addWidget(self.date_col)
        map_row.addWidget(QLabel("Desc"))
        map_row.addWidget(self.desc_col)

        map_row.addWidget(QLabel("Amount"))
        map_row.addWidget(self.amount_col)
        map_row.addWidget(QLabel("Debit"))
        map_row.addWidget(self.debit_col)
        map_row.addWidget(QLabel("Credit"))
        map_row.addWidget(self.credit_col)

        map_row.addWidget(QLabel("Account"))
        map_row.addWidget(self.account_combo)

        root.addLayout(map_row)

        # load accounts
        self.accounts_repo = AccountsRepo(self.db)
        default_id = self.accounts_repo.ensure_default_cash_account()
        accounts = self.accounts_repo.list_accounts()
        for a in accounts:
            self.account_combo.addItem(a.name, a.id)
        idx = self.account_combo.findData(default_id)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)

        self.table = QTableView()
        self.model = CsvPreviewModel()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_choose.clicked.connect(self.choose_csv)
        self.btn_preview.clicked.connect(self.preview_import)
        self.btn_import.clicked.connect(self.import_csv)

    # ---------------- UI actions ----------------
    def choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        self.csv_path = Path(path)
        self.path_label.setText(path)
        self.status_label.setText("")
        self.btn_preview.setEnabled(False)
        self.btn_import.setEnabled(False)

        headers, rows = self._read_csv_preview(self.csv_path, limit=200)

        self._headers = headers
        self._rows = rows

        self._set_mapping_options(headers)
        self.model.set_data(headers, rows)
        self.table.resizeColumnsToContents()

        if headers:
            self.btn_preview.setEnabled(True)
            self.btn_import.setEnabled(True)

    def preview_import(self) -> None:
        if self.csv_path is None:
            return

        ok, msg = self._validate_mapping()
        if not ok:
            QMessageBox.warning(self, "Missing mapping", msg)
            return

        valid, dup, failed, errors = self._scan_full_file(self.csv_path, dry_run=True)

        text = f"Preview: Valid {valid} • Duplicates {dup} • Failed {failed}."
        if errors:
            text += "  First errors: " + " | ".join(errors)
        self.status_label.setText(text)

    def import_csv(self) -> None:
        if self.csv_path is None:
            return

        ok, msg = self._validate_mapping()
        if not ok:
            QMessageBox.warning(self, "Missing mapping", msg)
            return

        valid, dup, failed, _ = self._scan_full_file(self.csv_path, dry_run=True)

        confirm = QMessageBox.question(
            self,
            "Confirm Import",
            f"This will import {valid} rows.\n"
            f"Duplicates skipped: {dup}\n"
            f"Failed rows: {failed}\n\n"
            f"Continue?",
        )
        if confirm != QMessageBox.Yes:
            return

        imported, skipped, failed2, errors2 = self._scan_full_file(self.csv_path, dry_run=False)

        msg2 = f"Imported {imported} • Skipped {skipped} duplicates • Failed {failed2}."
        if errors2:
            msg2 += "  First errors: " + " | ".join(errors2)
        self.status_label.setText(msg2)

    # ---------------- Core logic ----------------
    def _validate_mapping(self) -> tuple[bool, str]:
        d_i = int(self.date_col.currentData())
        s_i = int(self.desc_col.currentData())
        amt_i = int(self.amount_col.currentData())
        debit_i = int(self.debit_col.currentData())
        credit_i = int(self.credit_col.currentData())
        account_id = self.account_combo.currentData()

        if d_i == -1 or s_i == -1 or account_id is None:
            return False, "Please choose Date, Desc, and an Account."

        if amt_i == -1 and (debit_i == -1 and credit_i == -1):
            return False, "Choose Amount, or Debit/Credit columns."

        return True, ""

    def _scan_full_file(self, path: Path, dry_run: bool) -> tuple[int, int, int, list[str]]:
        d_i = int(self.date_col.currentData())
        s_i = int(self.desc_col.currentData())
        amt_i = int(self.amount_col.currentData())
        debit_i = int(self.debit_col.currentData())
        credit_i = int(self.credit_col.currentData())
        account_id = int(self.account_combo.currentData())

        imported = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            _ = next(reader, None)  # headers
            for row in reader:
                try:
                    date_raw = row[d_i].strip() if d_i < len(row) else ""
                    desc = row[s_i].strip() if s_i < len(row) else ""

                    occurred_on = self._parse_date(date_raw)
                    amount_cents = self._amount_from_row(row, amt_i, debit_i, credit_i)

                    if self._transaction_exists(account_id, occurred_on, amount_cents, desc):
                        skipped += 1
                        continue

                    if not dry_run:
                        self.tx_repo.add_transaction(
                            account_id=account_id,
                            category_id=None,
                            amount_cents=amount_cents,
                            occurred_on=occurred_on,
                            description=desc,
                        )

                    imported += 1
                except Exception as e:
                    failed += 1
                    if len(errors) < 5:
                        errors.append(str(e))

        return imported, skipped, failed, errors

    def _transaction_exists(self, account_id: int, occurred_on: str, amount_cents: int, description: str) -> bool:
        row = self.db.query_one(
            """
            SELECT 1
            FROM transactions
            WHERE account_id = ?
              AND occurred_on = ?
              AND amount_cents = ?
              AND COALESCE(description, '') = ?
            LIMIT 1;
            """,
            (account_id, occurred_on, amount_cents, description),
        )
        return row is not None

    def _amount_from_row(self, row: list[str], amt_i: int, debit_i: int, credit_i: int) -> int:
        # Single Amount column
        if amt_i != -1 and amt_i < len(row):
            return self._parse_amount_to_cents(row[amt_i].strip())

        # Debit/Credit columns
        debit_text = row[debit_i].strip() if debit_i != -1 and debit_i < len(row) else ""
        credit_text = row[credit_i].strip() if credit_i != -1 and credit_i < len(row) else ""

        if debit_text:
            return -abs(self._parse_amount_to_cents(debit_text))
        if credit_text:
            return abs(self._parse_amount_to_cents(credit_text))

        raise ValueError("Missing amount (no debit/credit)")

    def _set_mapping_options(self, headers: list[str]) -> None:
        combos = [self.date_col, self.desc_col, self.amount_col, self.debit_col, self.credit_col]
        for cb in combos:
            cb.clear()
            cb.addItem("(choose)", -1)
            for i, h in enumerate(headers):
                cb.addItem(h, i)

        def pick(cb: QComboBox, keywords: list[str]) -> None:
            for i, h in enumerate(headers):
                h2 = h.lower()
                if any(k in h2 for k in keywords):
                    idx = cb.findData(i)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
                    return

        pick(self.date_col, ["date", "posted", "posting", "transaction date", "trans date"])
        pick(self.desc_col, ["description", "details", "merchant", "name", "memo", "payee"])
        pick(self.amount_col, ["amount", "amt", "value", "transaction amount", "total"])
        pick(self.debit_col, ["debit", "withdrawal", "money out", "spent"])
        pick(self.credit_col, ["credit", "deposit", "money in", "received"])

    def _read_csv_preview(self, path: Path, limit: int = 200) -> tuple[list[str], list[list[str]]]:
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            rows: list[list[str]] = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i + 1 >= limit:
                    break
        return headers, rows

    def _parse_date(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            raise ValueError("Missing date")

        s2 = s.replace(".", "/").strip()

        fmts = (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%d-%b-%Y",  # 02-Jan-2026
            "%d-%B-%Y",  # 02-January-2026
            "%b %d %Y",
            "%B %d %Y",
        )

        for fmt in fmts:
            try:
                return datetime.strptime(s2, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

        if len(s) >= 10 and s[4] in "-/" and s[7] in "-/":
            return s[:10].replace("/", "-")

        raise ValueError(f"Unrecognized date: {s}")

    def _parse_amount_to_cents(self, s: str) -> int:
        raw = (s or "").strip()
        if not raw:
            raise ValueError("Missing amount")

        t = raw.strip()
        sign = 1

        # Parentheses = negative
        if t.startswith("(") and t.endswith(")"):
            sign = -1
            t = t[1:-1].strip()

        low = t.lower()

        # DR/DEBIT negative, CR/CREDIT positive
        if any(x in low for x in [" dr", "dr ", "debit", "withdrawal"]):
            sign = -1
        if any(x in low for x in [" cr", "cr ", "credit", "deposit"]):
            sign = 1

        # Remove all but digits, dot, minus, plus
        cleaned = re.sub(r"[^0-9\.\-\+]", "", t)

        if not cleaned or cleaned in ["-", "+", ".", "-.", "+."]:
            raise ValueError(f"Invalid amount: {raw}")

        # Leading '-' overrides sign
        if cleaned.startswith("-"):
            sign = -1

        val = float(cleaned)
        cents = int(round(abs(val) * 100))
        return sign * cents
