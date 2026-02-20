from __future__ import annotations

from pathlib import Path


def build_prompt(topic: str) -> str:
    return f"""Genera una infografía vertical de alta calidad sobre: {topic}.

Estructura:
1) Definición
2) Fisiopatología (diagrama)
3) Clínica
4) Diagnóstico (algoritmo)
5) Tratamiento (primera línea y alternativas)
6) Red flags
7) Errores comunes

Regla: usa solo estas fuentes; si falta algo, dilo explícitamente.
"""


def write_prompt(path: Path, topic: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_prompt(topic), encoding="utf-8")
