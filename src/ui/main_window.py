from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
)
from src.ui.dashboard_page import DashboardPage
from src.ui.import_page import ImportPage
from src.ui.reports_page import ReportsPage
from src.ui.budgets_page import BudgetsPage
from PySide6.QtCore import Qt
from src.ui.accounts_page import AccountsPage
from core.db import Database
from src.ui.pages import PlaceholderPage
from src.ui.categories_page import CategoriesPage
from src.ui.transactions_page import TransactionsPage

class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db

        # name of the app and its size
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

        # Pages (pass db so pages can query later)
        self.pages = {
            "Dashboard": DashboardPage(db=self.db),
            "Import": ImportPage(db=self.db),
            "Transactions": TransactionsPage(db=self.db),
            "Budgets": BudgetsPage(db=self.db),
            "Reports": ReportsPage(db=self.db),
            "Accounts": AccountsPage(db=self.db),
            "Categories": CategoriesPage(db=self.db),

        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        # Sidebar buttons
        self.buttons = {}

        for name in self.pages.keys():
            button = QPushButton(name)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(self._button_style(False))
            button.clicked.connect(lambda checked=False, n=name: self.show_page(n))

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
            btn.setStyleSheet(self._button_style(btn_name == name))

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
