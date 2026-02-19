from __future__ import annotations

from pathlib import Path


def build_notebooklm_prompt(topic: str) -> str:
    return f"""Genera una infografía vertical de alta calidad sobre: {topic}.

Estructura obligatoria:
1) Definición clara y breve.
2) Fisiopatología (incluye diagrama conceptual).
3) Clínica (signos, síntomas, hallazgos clave).
4) Diagnóstico (algoritmo paso a paso).
5) Tratamiento (primera línea y alternativas).
6) Red flags / criterios de gravedad.
7) Errores comunes a evitar.

Reglas:
- Usa solo estas fuentes proporcionadas.
- Si falta información en las fuentes, dilo explícitamente.
- Prioriza claridad visual, bullets cortos y jerarquía de color.
"""


def write_prompt_file(path: Path, topic: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_notebooklm_prompt(topic), encoding="utf-8")
