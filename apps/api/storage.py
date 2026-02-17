import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "ecatalog.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    return [row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_offer_status_column(cur: sqlite3.Cursor) -> None:
    columns = _table_columns(cur, "offers")
    if "status" not in columns:
        cur.execute("ALTER TABLE offers ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")


def _ensure_seller_phase2_columns(cur: sqlite3.Cursor) -> None:
    columns = _table_columns(cur, "sellers")
    if "verification_level" not in columns:
        cur.execute("ALTER TABLE sellers ADD COLUMN verification_level TEXT NOT NULL DEFAULT 'unverified'")
    if "review_count" not in columns:
        cur.execute("ALTER TABLE sellers ADD COLUMN review_count INTEGER NOT NULL DEFAULT 0")


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
            rating REAL DEFAULT 0,
            verification_level TEXT NOT NULL DEFAULT 'unverified' CHECK (verification_level IN ('unverified', 'basic', 'verified')),
            review_count INTEGER NOT NULL DEFAULT 0
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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seller_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES sellers(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            target_price_azn REAL NOT NULL,
            contact_email TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fraud_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER,
            seller_id INTEGER,
            signal_type TEXT NOT NULL,
            risk_score REAL NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES offers(id),
            FOREIGN KEY (seller_id) REFERENCES sellers(id)
        )
        """
    )

    _ensure_offer_status_column(cur)
    _ensure_seller_phase2_columns(cur)

    conn.commit()
    conn.close()
