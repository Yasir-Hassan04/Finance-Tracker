from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.db import Database


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    kind: str  # 'income' or 'expense'


@dataclass
class CategoriesRepo:
    db: Database

    def list_categories(self, kind: Optional[str] = None) -> list[Category]:
        if kind is None:
            rows = self.db.query_all(
                "SELECT id, name, kind FROM categories ORDER BY kind ASC, name ASC;"
            )
        else:
            rows = self.db.query_all(
                "SELECT id, name, kind FROM categories WHERE kind = ? ORDER BY name ASC;",
                (kind,),
            )
        return [Category(id=int(r["id"]), name=str(r["name"]), kind=str(r["kind"])) for r in rows]

    def create_category(self, name: str, kind: str) -> int:
        cur = self.db.execute(
            "INSERT INTO categories(name, kind) VALUES(?, ?);",
            (name, kind),
        )
        return int(cur.lastrowid)

    def update_category(self, category_id: int, name: str, kind: str) -> None:
        self.db.execute(
            "UPDATE categories SET name = ?, kind = ? WHERE id = ?;",
            (name, kind, category_id),
        )

    def delete_category(self, category_id: int) -> None:
        self.db.execute("DELETE FROM categories WHERE id = ?;", (category_id,))
