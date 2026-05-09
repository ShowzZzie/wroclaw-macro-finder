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

The API also exposes `GET /restaurants` (returns `[{id, name}]`) which the frontend uses to populate the restaurant filter, and is CORS-enabled for `http://localhost:5173` (the Vite dev origin).

## Run the frontend

A modern Vite + React + TypeScript SPA lives in `frontend/`. It talks to the FastAPI backend running on `127.0.0.1:8000` via a Vite dev proxy, so no CORS dance is needed in dev.

Requirements: **Node.js 20+** and **npm**.

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173). Make sure the FastAPI server (above) is running in another terminal.

Production build:

```bash
cd frontend
npm run build      # outputs static files to frontend/dist/
npm run preview    # preview the built bundle locally
```

For a single-deployable setup, you can later mount the build directly inside FastAPI with `app.mount("/", StaticFiles(directory="frontend/dist", html=True))`.

## Extract macros (deterministic by default)

Reads `data/sources.csv` and updates **`data/macros.csv`**. By default this uses **HTTP + HTML parsing** (no billable API) for chains like HulThai, MAX Burgers, LUCA, Pan Precel, Shrimp House, Pizzatopia; **merges** into the existing CSV so other restaurants are left untouched.

```bash
cd src
python -m app.extract_macros --only "HulThai" "MAX Burgers"
```

- **`--no-merge`**: write only rows produced in this run (overwrites unrelated restaurants’ rows in the output file).
- **`--use-openai`** or **`MACRO_USE_OPENAI=1`**: run the OpenAI Responses flow for supported PDFs (requires **`OPENAI_SECRET_KEY`**). Without this, PDF rows are skipped unless you extend `app.macro_extract.pdf_local`.

Legacy PDF-only OpenAI run (full rewrite, no merge):

```bash
cd src
python -m app.api_pdfs
```

## Development

Optional quality checks (install tools in your venv if missing):

```bash
ruff check .
ruff format --check .
mypy src/
```

Install **`pytest`** to run tests (e.g. under `tests/`) once you add or expand cases.


## MVP Data Policy (SQLite in Git)

For MVP deployment, `data/main_database.db` is **intentionally tracked in Git** so the static site can ship with pre-seeded data.

### Why this is intentional
- The current hosting setup needs a ready-to-use local SQLite file.
- Keeping the DB in the repo makes MVP deployment simple and repeatable.

### Temporary tradeoff
This is an MVP-only decision. Before production hardening, we should move data storage out of Git (e.g. managed DB or external storage), then re-enable ignoring `data/main_database.db` in `.gitignore`.

### Contributor note
If you update `data/main_database.db`, make sure changes are expected for MVP data refreshes and do not include sensitive information.


## License / status

Early-stage personal project; behavior and data coverage may change.
