import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from core.db import Database, init_db

def main() -> None:
    app = QApplication(sys.argv)

    db = Database.open()
    init_db(db)

    window = MainWindow(db=db)
    window.show()

    app.aboutToQuit.connect(db.close)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
