from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "sources_dir": "Fuentes",
    "syllabus_pdf_path": "Temario/temario.pdf",
    "syllabus_csv_path": "Temario/temario.csv",
    "output_dir": "Salida",
    "index_db_path": "Indice/index.db",
    "context_pages": 1,
    "max_pages_total": 60,
    "top_k_results": 40,
    "score_threshold": 0.0,
    "group_by_source": True,
    "add_source_separators": False,
}


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_config(config_path: Path = Path("config.json")) -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    loaded = load_json(config_path, {})
    if loaded:
        config.update(loaded)
    return config


def ensure_directories(config: dict[str, Any]) -> None:
    Path(config["sources_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["output_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["index_db_path"]).parent.mkdir(parents=True, exist_ok=True)
    Path(config["syllabus_csv_path"]).parent.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE).strip().replace(" ", "_")
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized[:120] or "topic"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def today_iso() -> str:
    return datetime.now().date().isoformat()


def setup_logger(output_dir: Path) -> logging.Logger:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("studyflow")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(output_dir / "log.txt", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
