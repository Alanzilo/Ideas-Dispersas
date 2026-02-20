from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_files (
            source_file TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL,
            mtime REAL NOT NULL,
            size INTEGER NOT NULL,
            pages INTEGER NOT NULL,
            requires_ocr INTEGER NOT NULL,
            last_indexed TEXT NOT NULL,
            last_error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
            source_file UNINDEXED,
            page_num UNINDEXED,
            text,
            page_hash UNINDEXED,
            indexed_at UNINDEXED,
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )
    conn.commit()


def supports_fts5() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE x USING fts5(content)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
