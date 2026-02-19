from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.compiler import compile_pdf
from app.indexer import index_sources, list_sources_status
from app.prompts import write_prompt_file
from app.searcher import build_pages_summary, search_topic
from app.syllabus import resolve_topic
from app.utils import ensure_directories, load_config, load_json, sanitize_filename, setup_logger


def cmd_index(config: dict) -> None:
    logger = setup_logger(Path(config["output_dir"]))
    summary = index_sources(Path(config["sources_dir"]), Path(config["index_db_path"]), logger)
    logger.info("Indexación completada: %s", summary)


def _build_manifest(
    date_str: str,
    topic: str,
    config: dict,
    search_result: dict,
    sources_status: list[dict],
) -> dict:
    selected_pages = build_pages_summary(search_result["selected_pages"])
    details = []
    for source, hits in search_result["selected_pages"].items():
        for hit in hits:
            details.append(
                {
                    "source_file": source,
                    "page_num": hit.page_num,
                    "score": hit.score,
                    "matched_keywords": hit.matched_keywords,
                }
            )

    return {
        "date": date_str,
        "topic": topic,
        "config_snapshot": config,
        "sources_processed": sources_status,
        "pages_included_by_source": selected_pages,
        "included_page_details": details,
        "keywords": search_result["keywords"],
    }


def cmd_build(config: dict, date_arg: str | None, topic_arg: str | None) -> None:
    ensure_directories(config)
    logger = setup_logger(Path(config["output_dir"]))

    date_str, topic = resolve_topic(
        topic_arg,
        date_arg,
        Path(config["syllabus_pdf_path"]),
        Path(config["syllabus_csv_path"]),
    )
    logger.info("Tema resuelto para build: %s (%s)", topic, date_str)

    synonyms = load_json(Path("synonyms.json"), {}) or {}
    search_result = search_topic(
        db_path=Path(config["index_db_path"]),
        topic=topic,
        synonyms=synonyms,
        top_k_results=int(config["top_k_results"]),
        score_threshold=float(config["score_threshold"]),
        context_pages=int(config["context_pages"]),
        max_pages_total=int(config["max_pages_total"]),
    )

    selected_pages = build_pages_summary(search_result["selected_pages"])
    if not selected_pages:
        logger.warning("No se encontraron páginas relevantes para el tema: %s", topic)

    slug = sanitize_filename(topic)
    out_dir = Path(config["output_dir"])
    pdf_path = out_dir / f"{date_str}_{slug}.pdf"
    prompt_path = out_dir / f"{date_str}_{slug}_prompt.txt"
    manifest_path = out_dir / f"{date_str}_{slug}_manifest.json"

    compile_pdf(
        output_pdf_path=pdf_path,
        topic=topic,
        date_str=date_str,
        selected_pages=selected_pages,
        add_source_separators=bool(config.get("add_source_separators", False)),
    )
    write_prompt_file(prompt_path, topic)

    manifest = _build_manifest(date_str, topic, config, search_result, list_sources_status(Path(config["index_db_path"])))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Generado PDF: %s", pdf_path)
    logger.info("Generado prompt: %s", prompt_path)
    logger.info("Generado manifest: %s", manifest_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automatización local de estudio (Opción 1)")
    parser.add_argument("--config", default="config.json", help="Ruta al config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="Indexa PDFs en Fuentes/")
    b = sub.add_parser("build", help="Genera PDF recortado + prompt + manifest")
    b.add_argument("--date", help="Fecha YYYY-MM-DD")
    b.add_argument("--topic", help="Tema explícito")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(Path(args.config))
    ensure_directories(config)

    if args.command == "index":
        cmd_index(config)
    elif args.command == "build":
        cmd_build(config, args.date, args.topic)


if __name__ == "__main__":
    main()
