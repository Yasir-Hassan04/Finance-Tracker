from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from typing import Optional

from core.db import Database


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str, db: Optional[Database] = None) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        # sets the name for the big title on each section (page)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setStyleSheet("font-size: 22px; font-weight: 600;")

        # for our smaller descriptive title
        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignLeft)
        subtitle_label.setStyleSheet("font-size: 14px; color: #888888;")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # optional DB proof (so you know db is wired correctly)
        if db is not None:
            row = db.query_one("SELECT COUNT(*) AS n FROM categories;")
            count = row["n"] if row else 0
            db_label = QLabel(f"DB OK • Categories: {count}")
            db_label.setAlignment(Qt.AlignLeft)
            db_label.setStyleSheet("font-size: 12px; color: #44aa44;")
            layout.addWidget(db_label)

        layout.addStretch()
