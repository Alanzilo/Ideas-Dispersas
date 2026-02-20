from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.indexer import get_connection


@dataclass
class PageHit:
    source_file: str
    page_num: int
    score: float
    matched_keywords: list[str]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


def tokenize_topic(topic: str) -> list[str]:
    return [tok for tok in re.split(r"[^\w]+", normalize(topic)) if len(tok) > 2]


def expand_keywords(topic: str, synonyms: dict[str, list[str]]) -> list[str]:
    kws = set(tokenize_topic(topic))
    normalized_topic = normalize(topic)
    for key, values in synonyms.items():
        if normalize(key) in normalized_topic or normalize(key) in kws:
            kws.add(normalize(key))
            for v in values:
                kws.update(tokenize_topic(v))
                kws.add(normalize(v))
    return sorted(kws)


def _score_text(text: str, topic: str, keywords: list[str]) -> tuple[float, list[str]]:
    ntext = normalize(text)
    score = 0.0
    matched: list[str] = []
    for kw in keywords:
        if kw and kw in ntext:
            hits = ntext.count(kw)
            score += hits * 1.0
            matched.append(kw)
    phrase = normalize(topic)
    if phrase and phrase in ntext:
        score += 4.0
    token_hits = sum(1 for kw in keywords if kw in ntext)
    if token_hits >= 2:
        score += 1.5
    return score, sorted(set(matched))


def select_pages_with_context(
    page_hits: list[PageHit],
    context_pages: int,
    max_pages_total: int,
) -> dict[str, list[PageHit]]:
    grouped: dict[str, dict[int, PageHit]] = defaultdict(dict)
    for hit in sorted(page_hits, key=lambda h: h.score, reverse=True):
        source_map = grouped[hit.source_file]
        if hit.page_num not in source_map:
            source_map[hit.page_num] = hit
        for page in range(max(1, hit.page_num - context_pages), hit.page_num + context_pages + 1):
            if page not in source_map:
                source_map[page] = PageHit(hit.source_file, page, max(0.1, hit.score * 0.25), ["context"])

    flat = []
    for source, pages in grouped.items():
        for hit in pages.values():
            flat.append((source, hit))

    flat.sort(key=lambda it: (it[1].score), reverse=True)
    flat = flat[:max_pages_total]

    limited: dict[str, list[PageHit]] = defaultdict(list)
    for source, hit in flat:
        limited[source].append(hit)

    for source in limited:
        limited[source].sort(key=lambda h: h.page_num)
    return dict(limited)


def search_topic(
    db_path: Path,
    topic: str,
    synonyms: dict[str, list[str]],
    top_k_results: int,
    score_threshold: float,
    context_pages: int,
    max_pages_total: int,
) -> dict:
    conn = get_connection(db_path)
    keywords = expand_keywords(topic, synonyms)
    fts_query = " OR ".join(f'"{kw}"' for kw in keywords if " " not in kw)
    if not fts_query:
        fts_query = '"' + normalize(topic) + '"'

    rows = conn.execute(
        """
        SELECT source_file, page_num, text
        FROM pages_fts
        WHERE pages_fts MATCH ?
        LIMIT ?
        """,
        (fts_query, top_k_results * 5),
    ).fetchall()
    conn.close()

    hits: list[PageHit] = []
    for row in rows:
        score, matched = _score_text(row["text"] or "", topic, keywords)
        if score >= score_threshold:
            hits.append(PageHit(row["source_file"], int(row["page_num"]), score, matched))

    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:top_k_results]
    selected = select_pages_with_context(hits, context_pages=context_pages, max_pages_total=max_pages_total)

    return {
        "topic": topic,
        "keywords": keywords,
        "hits": hits,
        "selected_pages": selected,
    }


def build_pages_summary(selected_pages: dict[str, list[PageHit]]) -> dict[str, list[int]]:
    return {source: [hit.page_num for hit in hits] for source, hits in selected_pages.items()}
