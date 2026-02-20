from __future__ import annotations

import sqlite3
import time
from pathlib import Path


from app.utils import file_hash


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_files (
            source_file TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL,
            mtime REAL NOT NULL,
            indexed_at TEXT NOT NULL,
            requires_ocr INTEGER NOT NULL DEFAULT 0
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


def _needs_reindex(conn: sqlite3.Connection, pdf_path: Path, mtime: float, digest: str) -> bool:
    row = conn.execute(
        "SELECT file_hash, mtime FROM source_files WHERE source_file = ?",
        (str(pdf_path),),
    ).fetchone()
    if row is None:
        return True
    return row["file_hash"] != digest or abs(row["mtime"] - mtime) > 1e-6


def index_sources(sources_dir: Path, db_path: Path, logger) -> dict:
    import fitz
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    init_db(conn)

    indexed, skipped, ocr_marked, errors = 0, 0, 0, []

    for pdf_path in sorted(sources_dir.glob("*.pdf")):
        try:
            mtime = pdf_path.stat().st_mtime
            digest = file_hash(pdf_path)
            if not _needs_reindex(conn, pdf_path, mtime, digest):
                skipped += 1
                continue

            logger.info("Indexando %s", pdf_path.name)
            conn.execute("DELETE FROM pages_fts WHERE source_file = ?", (str(pdf_path),))
            doc = fitz.open(pdf_path)
            has_text = False
            now = time.strftime("%Y-%m-%dT%H:%M:%S")

            for page_num, page in enumerate(doc, start=1):
                text = (page.get_text("text") or "").strip()
                if text:
                    has_text = True
                page_digest = str(hash(text))
                conn.execute(
                    "INSERT INTO pages_fts(source_file, page_num, text, page_hash, indexed_at) VALUES (?, ?, ?, ?, ?)",
                    (str(pdf_path), page_num, text, page_digest, now),
                )

            requires_ocr = 0 if has_text else 1
            if requires_ocr:
                ocr_marked += 1
                logger.warning("PDF sin texto detectado (requires_ocr=true): %s", pdf_path.name)

            conn.execute(
                """
                INSERT INTO source_files(source_file, file_hash, mtime, indexed_at, requires_ocr)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(source_file) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    mtime=excluded.mtime,
                    indexed_at=excluded.indexed_at,
                    requires_ocr=excluded.requires_ocr
                """,
                (str(pdf_path), digest, mtime, now, requires_ocr),
            )
            conn.commit()
            indexed += 1
            doc.close()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error indexando %s: %s", pdf_path, exc)
            errors.append({"file": str(pdf_path), "error": str(exc)})

    conn.close()
    return {
        "indexed": indexed,
        "skipped": skipped,
        "ocr_marked": ocr_marked,
        "errors": errors,
    }


def list_sources_status(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT source_file, indexed_at, requires_ocr FROM source_files ORDER BY source_file"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
