from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _ranges(values: list[int]) -> str:
    if not values:
        return ""
    items = sorted(set(values))
    out = []
    s = e = items[0]
    for cur in items[1:]:
        if cur == e + 1:
            e = cur
        else:
            out.append(f"{s}-{e}" if s != e else str(s))
            s = e = cur
    out.append(f"{s}-{e}" if s != e else str(s))
    return ", ".join(out)


def compile_pdf(output_path: Path, topic: str, day: str, pages_by_source: dict[str, list[int]], add_source_separators: bool) -> None:
    import fitz

    out = fitz.open()
    cover = out.new_page()
    lines = [
        "StudyFlow - Compilado de estudio",
        f"Tema: {topic}",
        f"Fecha objetivo: {day}",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Fuentes usadas:",
    ]
    for source, pages in pages_by_source.items():
        lines.append(f"- {Path(source).name}: {_ranges(pages)}")
    lines.append("")
    lines.append("Nota: Generado por StudyFlow")
    cover.insert_textbox(fitz.Rect(50, 50, 545, 800), "\n".join(lines), fontsize=12)

    for source, pages in pages_by_source.items():
        src = fitz.open(source)
        if add_source_separators:
            sep = out.new_page()
            sep.insert_textbox(fitz.Rect(50, 250, 545, 500), f"Fuente: {Path(source).name}", fontsize=18, align=1)
        for page in sorted(set(pages)):
            if 1 <= page <= src.page_count:
                out.insert_pdf(src, from_page=page - 1, to_page=page - 1)
        src.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    out.close()
