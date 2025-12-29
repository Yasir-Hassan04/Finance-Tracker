from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QDialog,
    QMessageBox, QLineEdit, QComboBox, QLabel
)

from core.db import Database
from core.repos.categories_repo import CategoriesRepo, Category


class CategoriesTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Kind"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[Category] = []

    def set_rows(self, rows: list[Category]) -> None:
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
        c = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return c.name
            if col == 1:
                return c.kind

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return str(section + 1)

    def row_at(self, row_index: int) -> Category | None:
        return self._rows[row_index] if 0 <= row_index < len(self._rows) else None


class CategoryDialog(QDialog):
    def __init__(self, parent=None, *, title: str, initial: Category | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        self.name_edit = QLineEdit()
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["expense", "income"])

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Kind"))
        layout.addWidget(self.kind_combo)

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
            idx = self.kind_combo.findText(initial.kind)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)

    def get_values(self) -> tuple[str, str] | None:
        name = self.name_edit.text().strip()
        if not name:
            return None
        kind = self.kind_combo.currentText().strip()
        return name, kind


class CategoriesPage(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.repo = CategoriesRepo(db)

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
        self.model = CategoriesTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        self.btn_add.clicked.connect(self.add_category)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_refresh.clicked.connect(self.refresh)

        self.refresh()

    def refresh(self) -> None:
        self.model.set_rows(self.repo.list_categories())
        self.table.resizeColumnsToContents()

    def _selected_category(self) -> Category | None:
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return None
        return self.model.row_at(idxs[0].row())

    def add_category(self) -> None:
        dlg = CategoryDialog(self, title="Add Category")
        if dlg.exec() != QDialog.Accepted:
            return

        vals = dlg.get_values()
        if vals is None:
            QMessageBox.warning(self, "Invalid input", "Please fill fields correctly.")
            return

        name, kind = vals
        try:
            self.repo.create_category(name, kind)
        except Exception:
            QMessageBox.warning(self, "Create failed", "Category name must be unique.")
            return

        self.refresh()

    def edit_selected(self) -> None:
        cat = self._selected_category()
        if cat is None:
            return

        dlg = CategoryDialog(self, title="Edit Category", initial=cat)
        if dlg.exec() != QDialog.Accepted:
            return

        vals = dlg.get_values()
        if vals is None:
            QMessageBox.warning(self, "Invalid input", "Please fill fields correctly.")
            return

        name, kind = vals
        try:
            self.repo.update_category(cat.id, name, kind)
        except Exception:
            QMessageBox.warning(self, "Update failed", "Category name must be unique.")
            return

        self.refresh()

    def delete_selected(self) -> None:
        cat = self._selected_category()
        if cat is None:
            return

        if QMessageBox.question(self, "Delete category", f"Delete '{cat.name}'?") != QMessageBox.Yes:
            return

        self.repo.delete_category(cat.id)
        self.refresh()
