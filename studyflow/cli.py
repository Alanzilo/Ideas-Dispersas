from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path

from studyflow.compiler import compile_pdf
from studyflow.config import ensure_layout, init_workspace, load_config, load_json
from studyflow.db import supports_fts5
from studyflow.doctor import run_doctor
from studyflow.indexer import index_pdfs, list_sources
from studyflow.prompts import write_prompt
from studyflow.search import search_topic
from studyflow.syllabus import resolve_topic
from studyflow.utils import sanitize_filename, setup_logger


class UserFacingError(Exception):
    pass


def _manifest(day: str, topic: str, config: dict, result: dict, source_status: list[dict]) -> dict:
    pages = {src: [h.page_num for h in hits] for src, hits in result["selected_pages"].items()}
    details = [
        {
            "source_file": hit.source_file,
            "page_num": hit.page_num,
            "score": hit.score,
            "matched_keywords": hit.matched_keywords,
            "snippet": hit.snippet,
        }
        for hits in result["selected_pages"].values()
        for hit in hits
    ]
    return {
        "date": day,
        "topic": topic,
        "config_snapshot": config,
        "applied_synonyms": result["applied_synonyms"],
        "sources_processed": source_status,
        "pages_included_by_source": pages,
        "included_page_details": details,
    }


def cmd_init(args) -> int:
    created = init_workspace(Path("."), Path(args.config), Path(args.synonyms))
    fts_ok = supports_fts5()
    write_ok = os.access(Path("."), os.W_OK)

    print("✅ Workspace inicializado")
    if created:
        for k, v in created.items():
            print(f" - {k}: creado en {v}")
    else:
        print(" - config/synonyms ya existían (no sobrescritos)")
    print(f" - Permiso de escritura en carpeta actual: {'OK' if write_ok else 'NO'}")
    print(f" - SQLite FTS5: {'OK' if fts_ok else 'NO'}")
    print("\nQuickstart:")
    print("  1) python -m studyflow doctor")
    print("  2) python -m studyflow index && python -m studyflow preview --topic \"Tu tema\"")
    return 0


def cmd_doctor(args) -> int:
    config = load_config(Path(args.config))
    ok, checks = run_doctor(config)
    print("\n=== StudyFlow Doctor ===")
    for c in checks:
        badge = "✅" if c["ok"] else "❌"
        print(f"{badge} {c['name']}")
        if not c["ok"]:
            print(f"   - Por qué importa: {c['why']}")
            print(f"   - Cómo arreglar: {c['fix']}")
    return 0 if ok else 2


def _resolve_and_search(config: dict, args):
    db_path = Path(config["index_db_path"])
    if not db_path.exists():
        raise UserFacingError("No existe el índice. Ejecuta `python -m studyflow index` primero.")
    day, topic = resolve_topic(args.topic, args.date, Path(config["syllabus_pdf_path"]), Path(config["syllabus_csv_path"]))
    result = search_topic(
        db_path=db_path,
        topic=topic,
        synonyms=load_json(Path(args.synonyms), {}),
        top_k_results=int(config["top_k_results"]),
        score_threshold=float(config["score_threshold"]),
        context_pages=int(config["context_pages"]),
        max_pages_total=int(config["max_pages_total"]),
    )
    return day, topic, result


def cmd_index(args) -> int:
    config = load_config(Path(args.config))
    ensure_layout(config)
    logger = setup_logger(Path(config["output_dir"]) / "log.txt", debug=args.debug)
    summary = index_pdfs(Path(config["sources_dir"]), Path(config["index_db_path"]), logger)
    logger.info("Resumen indexado: %s", summary)
    return 0


def cmd_preview(args) -> int:
    config = load_config(Path(args.config))
    ensure_layout(config)
    day, topic, result = _resolve_and_search(config, args)

    print(f"Tema: {topic} | Fecha: {day}")
    print(f"Keywords: {', '.join(result['keywords'])}")
    print(f"Sinónimos aplicados: {', '.join(result['applied_synonyms']) if result['applied_synonyms'] else '(ninguno)'}")

    if not result["hits"]:
        print("\n⚠️ No hubo resultados útiles.")
        for reason in result["no_result_reasons"]:
            print(f" - {reason}")
        print("Sugerencias: bajar score_threshold, agregar synonyms, o usar un tema más general.")
        return 1

    print("\nCandidatas:")
    for hit in result["hits"][: min(30, len(result["hits"]))]:
        print(f"- {Path(hit.source_file).name} p.{hit.page_num} | score={hit.score:.3f}")
        print(f"  snippet: {hit.snippet}")
    return 0


def cmd_build(args) -> int:
    config = load_config(Path(args.config))
    ensure_layout(config)
    logger = setup_logger(Path(config["output_dir"]) / "log.txt", debug=args.debug)

    day, topic, result = _resolve_and_search(config, args)
    pages_by_source = {src: [h.page_num for h in hits] for src, hits in result["selected_pages"].items()}

    if not pages_by_source:
        raise UserFacingError(
            "No se encontraron páginas para compilar. Prueba `preview`, baja `score_threshold`, o agrega sinónimos en synonyms.json."
        )

    slug = sanitize_filename(topic)
    out_dir = Path(config["output_dir"])
    pdf_path = out_dir / f"{day}_{slug}.pdf"
    prompt_path = out_dir / f"{day}_{slug}_prompt.txt"
    manifest_path = out_dir / f"{day}_{slug}_manifest.json"

    if args.dry_run:
        print("[DRY RUN] Se generaría:")
        print(f" - {pdf_path}")
        print(f" - {prompt_path}")
        print(f" - {manifest_path}")
        print(f" - Fuentes: {len(pages_by_source)}")
        return 0

    compile_pdf(pdf_path, topic, day, pages_by_source, bool(config.get("add_source_separators", False)))
    write_prompt(prompt_path, topic)
    manifest = _manifest(day, topic, config, result, list_sources(Path(config["index_db_path"])))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Build finalizado: %s", pdf_path)
    logger.info("Prompt: %s", prompt_path)
    logger.info("Manifest: %s", manifest_path)

    if args.open and platform.system().lower().startswith("win"):
        try:
            os.startfile(str(out_dir))  # type: ignore[attr-defined]
        except Exception:
            logger.warning("No se pudo abrir la carpeta de salida automáticamente.")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="StudyFlow CLI")
    p.add_argument("--config", default="config.json")
    p.add_argument("--synonyms", default="synonyms.json")
    p.add_argument("--debug", action="store_true", help="Muestra stacktrace en errores")

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("doctor")
    sub.add_parser("index")

    pv = sub.add_parser("preview")
    pv.add_argument("--date")
    pv.add_argument("--topic")

    b = sub.add_parser("build")
    b.add_argument("--date")
    b.add_argument("--topic")
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--open", action="store_true")
    return p


def main() -> None:
    p = parser()
    args = p.parse_args()
    actions = {
        "init": cmd_init,
        "doctor": cmd_doctor,
        "index": cmd_index,
        "preview": cmd_preview,
        "build": cmd_build,
    }
    try:
        code = actions[args.command](args)
        raise SystemExit(code)
    except UserFacingError as exc:
        print(f"❌ {exc}")
        raise SystemExit(2)
    except Exception as exc:  # noqa: BLE001
        if args.debug:
            raise
        print(f"❌ Error: {exc}")
        print("Tip: usa --debug para ver stacktrace completo.")
        raise SystemExit(2)
