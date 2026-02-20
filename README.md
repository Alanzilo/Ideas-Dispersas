# StudyFlow (local, offline)

StudyFlow automatiza tu flujo diario de estudio: indexa PDFs locales, encuentra páginas relevantes por tema, permite **previsualizar** resultados y compila un PDF final + prompt para NotebookLM + manifest de trazabilidad.

> No automatiza NotebookLM. El flujo termina en `PDF + prompt` listos para subir/pegar manualmente.

## Requisitos

- Python 3.11+
- SQLite con FTS5 (se valida con `doctor`)
- PyMuPDF

## Instalación

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### macOS/Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quickstart real (diario)

```bash
python -m studyflow init
python -m studyflow doctor
python -m studyflow index
python -m studyflow preview --topic "Shock séptico"
python -m studyflow build --topic "Shock séptico"
```

## Comandos CLI

- `python -m studyflow init`
  - Crea `Temario/`, `Fuentes/`, `Indice/`, `Salida/`.
  - Crea `config.json` y `synonyms.json` si no existen.
  - Verifica escritura y FTS5.

- `python -m studyflow doctor`
  - Verifica Python, PyMuPDF, FTS5, rutas y PDFs.
  - Intenta extracción de texto de un PDF de muestra.
  - Si falla, explica por qué y cómo arreglar.

- `python -m studyflow index`
  - Indexa incrementalmente `Fuentes/*.pdf` en `Indice/index.db`.
  - Guarda metadata: hash, mtime, size, pages, `requires_ocr`, `last_indexed`.
  - Si un PDF falla/corrupto: lo reporta y sigue.

- `python -m studyflow preview --topic "..."` o `--date YYYY-MM-DD`
  - No genera archivos.
  - Muestra páginas candidatas con score y snippet.
  - Muestra sinónimos aplicados.

- `python -m studyflow build --topic "..." [--dry-run] [--open]`
  - Genera:
    - `Salida/YYYY-MM-DD_tema.pdf`
    - `Salida/YYYY-MM-DD_tema_prompt.txt`
    - `Salida/YYYY-MM-DD_tema_manifest.json`
  - `--dry-run` muestra qué haría sin escribir.
  - `--open` intenta abrir carpeta de salida en Windows.

## Estructura de carpetas

```text
Temario/
  temario.pdf
  temario.csv
Fuentes/
  *.pdf
Indice/
  index.db
Salida/
  *.pdf
  *_prompt.txt
  *_manifest.json
  log.txt
config.json
synonyms.json
demo/temario.csv
```

## Config (`config.json`)

Campos:
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

## Synonyms (`synonyms.json`)

```json
{
  "shock septico": ["sepsis", "septic shock"]
}
```

## Troubleshooting

### “SQLite FTS5: NO”
- Tu runtime de SQLite no trae FTS5.
- Solución: usar otra instalación de Python (normalmente oficial 3.11+).

### “PyMuPDF no instalado”
- Ejecuta `pip install pymupdf`.

### “PDF escaneado / requires_ocr”
- StudyFlow no hace OCR en este MVP.
- Usa una versión OCR del PDF o conviértelo externamente.

### “No hubo hits”
- Baja `score_threshold` en `config.json`.
- Añade sinónimos en `synonyms.json`.
- Prueba un tema más general en `preview`.

### Errores detallados
- Usa `--debug` para stacktrace completo.

## Demo mínima

1. Copia un PDF con texto a `Fuentes/`.
2. Copia `demo/temario.csv` a `Temario/temario.csv`.
3. Corre `index`, luego `preview --date 2026-02-19`, y luego `build`.

## Tests

```bash
pytest
```

Cobertura mínima:
- normalización de acentos
- sanitize filename
- selección con contexto
- parsing de temario CSV
- schema básico de manifest
