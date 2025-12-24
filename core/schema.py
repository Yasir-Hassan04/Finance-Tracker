# core/schema.py

SCHEMA_VERSION = 1

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,              -- e.g., chequing, savings, credit, cash
        currency TEXT NOT NULL DEFAULT 'CAD',
        opening_balance_cents INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL,              -- 'income' or 'expense'
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        category_id INTEGER,
        amount_cents INTEGER NOT NULL,   -- positive = income, negative = expense
        description TEXT,
        occurred_on TEXT NOT NULL,       -- ISO date string: YYYY-MM-DD
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_account_date
    ON transactions(account_id, occurred_on);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_category
    ON transactions(category_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        month TEXT NOT NULL,             -- YYYY-MM
        limit_cents INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(category_id, month),
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    );
    """,
]
