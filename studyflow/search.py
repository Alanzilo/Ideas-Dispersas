from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from studyflow.db import connect
from studyflow.utils import normalize_text, tokenize


@dataclass
class Hit:
    source_file: str
    page_num: int
    score: float
    snippet: str
    matched_keywords: list[str]


def expand_keywords(topic: str, synonyms: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    topic_norm = normalize_text(topic)
    kws = set(tokenize(topic))
    applied: list[str] = []
    for key, vals in synonyms.items():
        key_norm = normalize_text(key)
        if key_norm in topic_norm or key_norm in kws:
            applied.append(key)
            kws.update(tokenize(key))
            for v in vals:
                kws.update(tokenize(v))
    return sorted(kws), applied


def _snippet(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def _heuristic_score(text: str, topic: str, keywords: list[str]) -> tuple[float, list[str]]:
    nt = normalize_text(text)
    matched = [kw for kw in keywords if kw in nt]
    score = len(matched) * 0.35
    if normalize_text(topic) in nt:
        score += 0.9
    return score, matched


def _select_with_context(hits: list[Hit], context_pages: int, max_pages_total: int) -> dict[str, list[Hit]]:
    grouped: dict[str, dict[int, Hit]] = defaultdict(dict)
    for hit in sorted(hits, key=lambda h: h.score, reverse=True):
        grouped[hit.source_file][hit.page_num] = hit
        for p in range(max(1, hit.page_num - context_pages), hit.page_num + context_pages + 1):
            grouped[hit.source_file].setdefault(p, Hit(hit.source_file, p, max(0.05, hit.score * 0.2), "[contexto]", ["context"]))

    flat: list[Hit] = [h for per_source in grouped.values() for h in per_source.values()]
    flat.sort(key=lambda h: h.score, reverse=True)
    flat = flat[:max_pages_total]

    out: dict[str, list[Hit]] = defaultdict(list)
    for h in flat:
        out[h.source_file].append(h)
    for source in out:
        out[source].sort(key=lambda x: x.page_num)
    return dict(out)


def search_topic(
    db_path: Path,
    topic: str,
    synonyms: dict[str, list[str]],
    top_k_results: int,
    score_threshold: float,
    context_pages: int,
    max_pages_total: int,
) -> dict:
    conn = connect(db_path)
    keywords, applied_synonyms = expand_keywords(topic, synonyms)
    terms = [f'"{kw}"' for kw in keywords if kw]
    query = " OR ".join(terms) if terms else f'"{normalize_text(topic)}"'

    sql = (
        "SELECT source_file,page_num,text,bm25(pages_fts) as bm25_score "
        "FROM pages_fts WHERE pages_fts MATCH ? ORDER BY bm25_score LIMIT ?"
    )
    try:
        rows = conn.execute(sql, (query, top_k_results * 5)).fetchall()
    except Exception as exc:  # noqa: BLE001
        conn.close()
        raise ValueError("Índice no inicializado. Ejecuta `python -m studyflow index`.") from exc
    conn.close()

    hits: list[Hit] = []
    for row in rows:
        base = 1.0 / (1.0 + max(0.0, float(row["bm25_score"])))
        extra, matched = _heuristic_score(row["text"] or "", topic, keywords)
        final_score = base + extra
        if final_score >= score_threshold:
            hits.append(Hit(row["source_file"], int(row["page_num"]), final_score, _snippet(row["text"] or ""), matched))

    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:top_k_results]
    selected = _select_with_context(hits, context_pages=context_pages, max_pages_total=max_pages_total)
    reasons = []
    if not rows:
        reasons.append("No hubo coincidencias FTS para ese tema.")
    elif not hits:
        reasons.append("Hubo coincidencias, pero todas quedaron por debajo del score_threshold.")

    return {
        "topic": topic,
        "keywords": keywords,
        "applied_synonyms": applied_synonyms,
        "hits": hits,
        "selected_pages": selected,
        "no_result_reasons": reasons,
    }
