from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class SyllabusEntry:
    date: str
    topic: str


def parse_csv(path: Path) -> list[SyllabusEntry]:
    if not path.exists():
        return []
    rows: list[SyllabusEntry] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            d, t = (row.get("date") or "").strip(), (row.get("topic") or "").strip()
            if d and t:
                rows.append(SyllabusEntry(d, t))
    return rows


def parse_pdf(path: Path) -> tuple[list[SyllabusEntry], float]:
    import fitz

    if not path.exists():
        return [], 0.0
    rows: list[SyllabusEntry] = []
    try:
        doc = fitz.open(path)
        for page in doc:
            for line in page.get_text("text").splitlines():
                found = DATE_RE.search(line)
                if not found:
                    continue
                d = found.group(1)
                topic = line.replace(d, "").strip(" :-\t")
                if topic:
                    rows.append(SyllabusEntry(d, topic))
        doc.close()
    except Exception:
        return [], 0.0
    confidence = min(1.0, len(rows) / 8)
    return rows, confidence


def resolve_topic(topic: str | None, day: str | None, pdf_path: Path, csv_path: Path) -> tuple[str, str]:
    selected_day = day or date.today().isoformat()
    if topic:
        return selected_day, topic

    pdf_rows, confidence = parse_pdf(pdf_path)
    entries = pdf_rows if confidence >= 0.5 else parse_csv(csv_path)
    for row in entries:
        if row.date == selected_day:
            return selected_day, row.topic
    raise ValueError(f"No se encontró tema para {selected_day}. Revisa temario.csv o usa --topic.")
