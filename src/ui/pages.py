from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt



class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        #sets the name for the big title on each section (page)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        # for our smaller descriptive title
        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignLeft)
        subtitle_label.setStyleSheet("font-size: 14px; color: #888888;")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch()
