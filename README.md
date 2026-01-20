# Studio Ingest Tool (UI Skeleton)

## Run
1. Install deps:
   - `pip install PySide6`

2. Run:
   - `python app.py`

## Existing Project dropdown (UI-only)
- Edit `projects_index.json` (next to `app.py`) to add recent projects.

Example:
[
  {"client": "Iriya", "project": "Yom_HaAtsmaut", "last_updated": "2026-01-10"},
  {"client": "Mayor", "project": "Weekly_Update", "last_updated": "2026-01-11"}
]


## Ledger
- A row is appended to `ingest_ledger.csv` (next to `app.py`) for each ingest session.
