from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from studyflow.db import supports_fts5


def run_doctor(config: dict) -> tuple[bool, list[dict]]:
    checks: list[dict] = []

    checks.append(
        {
            "name": "Python >= 3.11",
            "ok": sys.version_info >= (3, 11),
            "why": "StudyFlow está validado para Python 3.11+.",
            "fix": "Instala Python 3.11 o 3.12 y recrea tu entorno virtual.",
        }
    )

    try:
        import fitz  # noqa: F401

        pymupdf_ok = True
    except Exception:
        pymupdf_ok = False
    checks.append(
        {
            "name": "PyMuPDF instalado",
            "ok": pymupdf_ok,
            "why": "Se usa para leer y compilar PDFs.",
            "fix": "pip install pymupdf",
        }
    )

    checks.append(
        {
            "name": "SQLite FTS5",
            "ok": supports_fts5(),
            "why": "FTS5 acelera búsqueda por texto.",
            "fix": "Usa una build de Python/SQLite con soporte FTS5.",
        }
    )

    for key in ["sources_dir", "output_dir", "syllabus_csv_path", "index_db_path"]:
        p = Path(config[key]) if key.endswith("_dir") else Path(config[key]).parent
        checks.append(
            {
                "name": f"Ruta accesible: {key}",
                "ok": p.exists(),
                "why": "Sin rutas válidas no se puede correr el flujo.",
                "fix": f"Crea la ruta {p} o ejecuta `python -m studyflow init`.",
            }
        )

    source_dir = Path(config["sources_dir"])
    pdfs = list(source_dir.glob("*.pdf")) if source_dir.exists() else []
    checks.append(
        {
            "name": "Hay PDFs en Fuentes/",
            "ok": len(pdfs) > 0,
            "why": "Sin fuentes no hay páginas para compilar.",
            "fix": "Copia uno o más PDFs de texto a la carpeta Fuentes/.",
        }
    )

    if pdfs and pymupdf_ok:
        import fitz

        sample = pdfs[0]
        try:
            doc = fitz.open(sample)
            text = (doc[0].get_text("text") if doc.page_count else "") or ""
            scanned = len(text.strip()) == 0
            doc.close()
            checks.append(
                {
                    "name": f"Extracción de texto de muestra ({sample.name})",
                    "ok": not scanned,
                    "why": "PDFs escaneados no se indexan por texto en este MVP.",
                    "fix": "Usa una versión OCR del PDF o convierte con OCR externo.",
                }
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                {
                    "name": f"Lectura PDF de muestra ({sample.name})",
                    "ok": False,
                    "why": "Si no se puede leer, ese archivo no entra en la búsqueda.",
                    "fix": f"Revisa permisos/corrupción del PDF. Error: {exc}",
                }
            )

    ok = all(c["ok"] for c in checks)
    return ok, checks
