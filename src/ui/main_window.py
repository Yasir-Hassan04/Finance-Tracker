from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
)
from PySide6.QtCore import Qt

from src.ui.pages import PlaceholderPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        #name of the app and its size
        self.setWindowTitle("Finance Assistant")
        self.setMinimumSize(1000, 650)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(8)

        # Main content stack
        self.stack = QStackedWidget()

        # Pages
        self.pages = {
            "Dashboard": PlaceholderPage(
                "Dashboard",
                "Overview of spending and alerts."
            ),
            "Import": PlaceholderPage(
                "Import",
                "Import bank transactions (CSV)."
            ),
            "Transactions": PlaceholderPage(
                "Transactions",
                "Search and review transactions."
            ),
            "Budgets": PlaceholderPage(
                "Budgets",
                "Set monthly budgets."
            ),
            "Reports": PlaceholderPage(
                "Reports",
                "Monthly and yearly summaries."
            ),
            "Settings": PlaceholderPage(
                "Settings",
                "Preferences and privacy."
            ),
            "Feedback": PlaceholderPage(
                "Feedback",
                "Send suggestions or issues."
            ),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        # Sidebar buttons
        self.buttons = {}


        for name in self.pages.keys():
            button = QPushButton(name)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(self._button_style(False))
            button.clicked.connect(
                lambda checked=False, n=name: self.show_page(n)
            )

            sidebar_layout.addWidget(button)
            self.buttons[name] = button

        sidebar_layout.addStretch()

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack, 1)

        # Default page
        self.show_page("Dashboard")

    def show_page(self, name: str) -> None:
        self.stack.setCurrentWidget(self.pages[name])

        for btn_name, btn in self.buttons.items():
            btn.setStyleSheet(
                self._button_style(btn_name == name)
            )

    @staticmethod
    def _button_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    padding: 10px;
                    text-align: left;
                    border-radius: 8px;
                    background-color: #2d2d2d;
                    color: white;
                    font-size: 14px;
                }
            """
        return """
            QPushButton {
                padding: 10px;
                text-align: left;
                border-radius: 8px;
                background-color: transparent;
                color: #cccccc;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1f1f1f;
            }
        """
