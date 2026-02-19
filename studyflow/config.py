from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "sources_dir": "Fuentes",
    "syllabus_pdf_path": "Temario/temario.pdf",
    "syllabus_csv_path": "Temario/temario.csv",
    "output_dir": "Salida",
    "index_db_path": "Indice/index.db",
    "context_pages": 1,
    "max_pages_total": 60,
    "top_k_results": 40,
    "score_threshold": 0.15,
    "group_by_source": True,
    "add_source_separators": False,
}

DEFAULT_SYNONYMS = {
    "sca": ["síndrome coronario agudo", "acute coronary syndrome"],
    "shock septico": ["sepsis", "septic shock"],
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config(config_path: Path) -> dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(load_json(config_path, {}))
    return cfg


def ensure_layout(config: dict[str, Any]) -> None:
    Path(config["sources_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["output_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["index_db_path"]).parent.mkdir(parents=True, exist_ok=True)
    Path(config["syllabus_pdf_path"]).parent.mkdir(parents=True, exist_ok=True)


def init_workspace(base_dir: Path, config_path: Path, synonyms_path: Path) -> dict[str, str]:
    base_dir.mkdir(parents=True, exist_ok=True)
    for folder in ["Temario", "Fuentes", "Indice", "Salida"]:
        (base_dir / folder).mkdir(parents=True, exist_ok=True)

    created: dict[str, str] = {}
    if not config_path.exists():
        save_json(config_path, DEFAULT_CONFIG)
        created["config"] = str(config_path)
    if not synonyms_path.exists():
        save_json(synonyms_path, DEFAULT_SYNONYMS)
        created["synonyms"] = str(synonyms_path)
    return created
