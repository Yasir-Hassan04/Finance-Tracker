# core/db.py

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .schema import CREATE_TABLES_SQL, SCHEMA_VERSION


def _project_root() -> Path:
    """
    Assumes this file lives at: <root>/<your_package>/core/db.py
    Adjust parents[n] if your structure differs.
    """
    return Path(__file__).resolve().parents[1]


def get_data_dir() -> Path:
    return _project_root() / "data"


def get_db_path() -> Path:
    return get_data_dir() / "finance.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@dataclass
class Database:
    _conn: sqlite3.Connection

    @classmethod
    def open(cls) -> "Database":
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        conn = _connect(get_db_path())
        return cls(conn)

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self._conn.execute(sql, tuple(params))
        self._conn.commit()
        return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
        cur = self._conn.executemany(sql, [tuple(p) for p in seq_of_params])
        self._conn.commit()
        return cur

    def query_all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        cur = self._conn.execute(sql, tuple(params))
        return cur.fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(sql, tuple(params))
        return cur.fetchone()


def init_db(db: Database) -> None:
    # Create tables
    with db.transaction():
        for stmt in CREATE_TABLES_SQL:
            db._conn.execute(stmt)

    # Store schema version
    existing = db.query_one("SELECT value FROM schema_meta WHERE key = 'schema_version';")
    if existing is None:
        db.execute(
            "INSERT INTO schema_meta(key, value) VALUES(?, ?);",
            ("schema_version", str(SCHEMA_VERSION)),
        )

    # Seed default categories (safe to re-run)
    seed_default_categories(db)


def seed_default_categories(db: Database) -> None:
    defaults = [
        ("Salary", "income"),
        ("Other Income", "income"),
        ("Groceries", "expense"),
        ("Rent", "expense"),
        ("Utilities", "expense"),
        ("Transport", "expense"),
        ("Eating Out", "expense"),
        ("Subscriptions", "expense"),
        ("Shopping", "expense"),
        ("Health", "expense"),
        ("Entertainment", "expense"),
        ("Other Expense", "expense"),
    ]

    # Insert only missing ones
    existing_names = {row["name"] for row in db.query_all("SELECT name FROM categories;")}
    to_add = [(name, kind) for (name, kind) in defaults if name not in existing_names]

    if to_add:
        db.executemany("INSERT INTO categories(name, kind) VALUES(?, ?);", to_add)
