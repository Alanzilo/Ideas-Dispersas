# StudyFlow Local (Opción 1)

Sistema local en Python para automatizar el flujo:
`tema del día -> búsqueda en PDFs fuente -> PDF recortado + prompt para NotebookLM + manifest de trazabilidad`.

## Estructura esperada

```text
Temario/
  temario.pdf
  temario.csv   # fallback recomendado
Fuentes/
  *.pdf
Indice/         # se crea automáticamente
Salida/         # se crea automáticamente
config.json
synonyms.json
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso CLI

### 1) Indexar fuentes (incremental)

```bash
python -m app.main index
```

- Extrae texto por página de `Fuentes/*.pdf`.
- Guarda índice en SQLite FTS5 (`Indice/index.db`).
- Detecta PDFs sin texto y marca `requires_ocr=true` sin romper la ejecución.
- Reindexa solo archivos nuevos/cambiados (hash + mtime).

### 2) Construir salida diaria

Por fecha:

```bash
python -m app.main build --date 2026-02-19
```

Por tema directo:

```bash
python -m app.main build --topic "Shock séptico"
```

Si no se pasa `--date` ni `--topic`, intenta tomar el tema del día (fecha local) desde temario.

## Salidas generadas

En `Salida/`:
- `YYYY-MM-DD_{topic}.pdf` (portada + páginas relevantes)
- `YYYY-MM-DD_{topic}_prompt.txt` (prompt para NotebookLM)
- `YYYY-MM-DD_{topic}_manifest.json` (trazabilidad)
- `log.txt` (logs del run)

## Formato `temario.csv`

UTF-8 con columnas:

```csv
date,topic
2026-02-19,"Shock séptico: diagnóstico y manejo"
```

## Configuración (`config.json`)

Campos usados:
- `sources_dir`
- `syllabus_pdf_path`
- `syllabus_csv_path`
- `output_dir`
- `index_db_path`
- `context_pages`
- `max_pages_total`
- `top_k_results`
- `score_threshold`
- `group_by_source`
- `add_source_separators`

## Decisiones del MVP

- Sin OCR en esta versión (solo detección y reporte `requires_ocr`).
- Parser de PDF del temario es heurístico; si la confianza es baja, usa CSV.
- Scoring simple: keywords + frase completa + bonificación de proximidad simple.
- Copia páginas originales en el PDF final (no rasteriza).

## Tests

```bash
pytest -q
```

Incluye tests para:
- `sanitize_filename`
- selección de páginas con contexto
- parser de CSV
- estructura base del manifest

