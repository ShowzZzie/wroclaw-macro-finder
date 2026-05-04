# Wrocław Macro Finder

Search and filter restaurant nutrition data around Wrocław: interactive CLI queries and a small **FastAPI** service over **SQLite** (via **SQLModel**). Source CSVs live under `data/`; macro tables for many chains are scraped or extracted separately.

## Requirements

- **Python 3.11+**
- Optional: **[OpenAI API key]** only if you run the PDF extraction script (`OPENAI_SECRET_KEY` in `.env`)

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Create a `.env` file when using OpenAI-backed tooling:

```env
OPENAI_SECRET_KEY=sk-...
```

The app loads it with `python-dotenv` where needed (e.g. `app/api_pdfs.py`). `.env` is gitignored.

## Data layout

| Path | Role |
|------|------|
| `data/sources.csv` | Restaurants, links to macro sources, formats, notes |
| `data/macros.csv` | Per-item nutrition (typically produced before or alongside DB ingest) |
| `data/main_database.db` | SQLite database (paths are resolved relative to project root inside `app/db.py`) |

Some extraction flows reference extra assets (for example PDFs under `data/`).

## Run the interactive CLI

Commands assume the **`src`** directory is on `PYTHONPATH` (simplest: run from `src`).

```bash
cd src
python main.py
```

Re-import both CSVs into the database (sources first, then foods):

```bash
cd src
python main.py --reingest-database
```

The CLI prompts for max kcal, min protein, optional restaurant id, inclusion of low-kcal add-ons, result limit, and sort mode.

## Run the HTTP API

```bash
cd src
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

Example:

```http
GET /foods/search?max_kcal=800&min_protein=40&limit=10&sort_by=protein_ratio_desc
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Extract macros from PDFs (OpenAI)

Reads `data/sources.csv`, calls the OpenAI Responses API where configured, and writes **`data/macros.csv`**. Requires a valid **`OPENAI_SECRET_KEY`**.

```bash
cd src
python -m app.api_pdfs
```

Rows that are skipped or fail are printed; not every source format may be automated yet.

## Development

Optional quality checks (install tools in your venv if missing):

```bash
ruff check .
ruff format --check .
mypy src/
```

Install **`pytest`** to run tests (e.g. under `tests/`) once you add or expand cases.

## License / status

Early-stage personal project; behavior and data coverage may change.
