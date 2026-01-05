from __future__ import annotations

from core.db import Database, init_db
from app import main


if __name__ == "__main__":

    db = Database.open()
    init_db(db)
    db.close()

    main()
