from __future__ import annotations

import hashlib
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


def setup_logger(log_path: Path, debug: bool = False) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("studyflow")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG if debug else logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE).strip().replace(" ", "_")
    return re.sub(r"_+", "_", cleaned)[:120] or "topic"


def normalize_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.lower())
    no_accents = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^\w\s]", " ", no_accents)


def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"\s+", normalize_text(text)) if len(t) > 2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
