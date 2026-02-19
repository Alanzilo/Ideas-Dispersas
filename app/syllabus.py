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


def parse_syllabus_csv(csv_path: Path) -> list[SyllabusEntry]:
    if not csv_path.exists():
        return []
    entries: list[SyllabusEntry] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            d = (row.get("date") or "").strip()
            t = (row.get("topic") or "").strip()
            if d and t:
                entries.append(SyllabusEntry(date=d, topic=t))
    return entries


def parse_syllabus_pdf(pdf_path: Path) -> tuple[list[SyllabusEntry], float]:
    import fitz
    if not pdf_path.exists():
        return [], 0.0
    entries: list[SyllabusEntry] = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            for line in page.get_text("text").splitlines():
                line = line.strip()
                match = DATE_RE.search(line)
                if not match:
                    continue
                d = match.group(1)
                topic = line.replace(d, "").strip(" :-\t")
                if topic:
                    entries.append(SyllabusEntry(date=d, topic=topic))
        doc.close()
    except Exception:
        return [], 0.0
    confidence = min(1.0, len(entries) / 10) if entries else 0.0
    return entries, confidence


def get_topic_for_date(target_date: str, syllabus_pdf: Path, syllabus_csv: Path) -> str:
    pdf_entries, confidence = parse_syllabus_pdf(syllabus_pdf)
    entries = pdf_entries if confidence >= 0.6 else parse_syllabus_csv(syllabus_csv)
    for entry in entries:
        if entry.date == target_date:
            return entry.topic
    raise ValueError(f"No se encontró tema para la fecha {target_date}")


def resolve_topic(topic: str | None, date_arg: str | None, syllabus_pdf: Path, syllabus_csv: Path) -> tuple[str, str]:
    if topic:
        day = date_arg or date.today().isoformat()
        return day, topic
    day = date_arg or date.today().isoformat()
    return day, get_topic_for_date(day, syllabus_pdf, syllabus_csv)
