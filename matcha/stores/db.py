"""SQLite connection + schema bootstrap."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from matcha.config import DB_PATH

_SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with sensible defaults."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables if they don't exist. Idempotent."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = _SCHEMA_FILE.read_text(encoding="utf-8")
    conn = get_connection(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
