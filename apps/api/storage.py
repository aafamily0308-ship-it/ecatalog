import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "ecatalog.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_offer_status_column(cur: sqlite3.Cursor) -> None:
    columns = [row["name"] for row in cur.execute("PRAGMA table_info(offers)").fetchall()]
    if "status" not in columns:
        cur.execute("ALTER TABLE offers ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            brand TEXT,
            category TEXT,
            condition TEXT NOT NULL CHECK (condition IN ('new', 'used', 'refurbished')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT,
            rating REAL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            seller_id INTEGER NOT NULL,
            price_azn REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'AZN',
            url TEXT,
            is_available INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (seller_id) REFERENCES sellers(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            old_price_azn REAL,
            new_price_azn REAL NOT NULL,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES offers(id)
        )
        """
    )

    _ensure_offer_status_column(cur)

    conn.commit()
    conn.close()
