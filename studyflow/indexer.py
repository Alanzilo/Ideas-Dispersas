from __future__ import annotations

from pathlib import Path

from studyflow.db import connect, ensure_schema
from studyflow.utils import now_ts, sha256_file


def _changed(conn, path: Path, digest: str, mtime: float, size: int) -> bool:
    row = conn.execute(
        "SELECT file_hash, mtime, size FROM source_files WHERE source_file=?",
        (str(path),),
    ).fetchone()
    if row is None:
        return True
    return row["file_hash"] != digest or abs(row["mtime"] - mtime) > 1e-6 or row["size"] != size


def index_pdfs(sources_dir: Path, db_path: Path, logger) -> dict:
    import fitz

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    ensure_schema(conn)

    pdfs = sorted(sources_dir.glob("*.pdf"))
    summary = {"total": len(pdfs), "indexed": 0, "skipped": 0, "requires_ocr": 0, "errors": []}

    for idx, pdf_path in enumerate(pdfs, start=1):
        try:
            logger.info("Indexando %s/%s: %s", idx, len(pdfs), pdf_path.name)
            stat = pdf_path.stat()
            digest = sha256_file(pdf_path)
            if not _changed(conn, pdf_path, digest, stat.st_mtime, stat.st_size):
                summary["skipped"] += 1
                continue

            conn.execute("DELETE FROM pages_fts WHERE source_file=?", (str(pdf_path),))
            doc = fitz.open(pdf_path)
            has_text = False
            indexed_at = now_ts()
            page_count = doc.page_count

            for page_num, page in enumerate(doc, start=1):
                text = (page.get_text("text") or "").strip()
                if text:
                    has_text = True
                conn.execute(
                    "INSERT INTO pages_fts(source_file,page_num,text,page_hash,indexed_at) VALUES(?,?,?,?,?)",
                    (str(pdf_path), page_num, text, str(hash(text)), indexed_at),
                )

            requires_ocr = 0 if has_text else 1
            if requires_ocr:
                summary["requires_ocr"] += 1
                logger.warning("PDF sin texto (requires_ocr): %s", pdf_path.name)

            conn.execute(
                """
                INSERT INTO source_files(source_file,file_hash,mtime,size,pages,requires_ocr,last_indexed,last_error)
                VALUES(?,?,?,?,?,?,?,NULL)
                ON CONFLICT(source_file) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    mtime=excluded.mtime,
                    size=excluded.size,
                    pages=excluded.pages,
                    requires_ocr=excluded.requires_ocr,
                    last_indexed=excluded.last_indexed,
                    last_error=NULL
                """,
                (str(pdf_path), digest, stat.st_mtime, stat.st_size, page_count, requires_ocr, indexed_at),
            )
            doc.close()
            conn.commit()
            summary["indexed"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("No se pudo indexar %s: %s", pdf_path.name, exc)
            conn.execute(
                """
                INSERT INTO source_files(source_file,file_hash,mtime,size,pages,requires_ocr,last_indexed,last_error)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(source_file) DO UPDATE SET
                    last_error=excluded.last_error,
                    last_indexed=excluded.last_indexed
                """,
                (str(pdf_path), "error", 0.0, 0, 0, 0, now_ts(), str(exc)),
            )
            conn.commit()
            summary["errors"].append({"file": str(pdf_path), "error": str(exc)})

    conn.close()
    return summary


def list_sources(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT source_file,pages,requires_ocr,last_indexed,last_error FROM source_files ORDER BY source_file"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
