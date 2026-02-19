from __future__ import annotations

from pathlib import Path



def _format_ranges(pages: list[int]) -> str:
    if not pages:
        return ""
    pages = sorted(set(pages))
    ranges = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = p
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(ranges)


def compile_pdf(
    output_pdf_path: Path,
    topic: str,
    date_str: str,
    selected_pages: dict[str, list[int]],
    add_source_separators: bool,
) -> None:
    import fitz

    out = fitz.open()

    cover = out.new_page()
    lines = [
        "Compilado de estudio",
        f"Fecha: {date_str}",
        f"Tema: {topic}",
        "",
        "Fuentes y páginas:",
    ]
    for source, pages in selected_pages.items():
        lines.append(f"- {Path(source).name}: {_format_ranges(pages)}")
    cover.insert_textbox(fitz.Rect(50, 50, 545, 800), "\n".join(lines), fontsize=12)

    for source, pages in selected_pages.items():
        src_doc = fitz.open(source)
        if add_source_separators:
            sep = out.new_page()
            sep.insert_textbox(
                fitz.Rect(50, 300, 545, 500),
                f"Fuente: {Path(source).name}",
                fontsize=18,
                align=1,
            )
        for page in sorted(set(pages)):
            if 1 <= page <= src_doc.page_count:
                out.insert_pdf(src_doc, from_page=page - 1, to_page=page - 1)
        src_doc.close()

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_pdf_path)
    out.close()
