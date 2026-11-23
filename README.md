# Travel Itinerary Organizer

StudentLife Hack — Project #52 | Domain: Travel & Transport

A zero-dependency Python application for organizing destinations, dates, notes and estimated costs, with strict input validation, local JSON/CSV persistence, search, analytics and threshold warnings. It includes both a console interface and a Tkinter desktop GUI over a shared service layer.

- **Repository:** https://github.com/pottollaramcharangoud-maker/TravelItineraryOrganizer
- **Website:** https://travel-itinerary-organizer.vercel.app

## Features

- Interactive terminal menu and full Tkinter GUI
- Defensive input validation with looping input wrappers
- CRUD operations for itinerary records
- Keyword, category and status search/filtering
- JSON/CSV persistence with corrupted-file recovery and format toggling
- Summary metrics with distribution bar charts and top-cost ranking
- Overdue, invalid-duration and cost-limit warnings
- Markdown, CSV, JSON and plain-text audit-log exports
- Bulk CSV import with row-by-row error logging
- 40 deterministic sample records

## Requirements

Python 3.10+ (standard library only; Tkinter required for the GUI).

## Run

```bash
git clone https://github.com/pottollaramcharangoud-maker/TravelItineraryOrganizer.git
cd TravelItineraryOrganizer
python main.py       # console application
python run_gui.py    # desktop GUI
```

## Console menu

| Option | Action |
|---|---|
| 1 | Add trip |
| 2 | View all trips (paginated table) |
| 3 | Search / filter trips |
| 4 | Update trip |
| 5 | Delete trip |
| 6 | Summary & analytics |
| 7 | Threshold warnings |
| 8 | Export reports (Markdown / CSV / Audit log / JSON) |
| 9 | Bulk import CSV |
| 10 | Seed 40 sample records |
| 11 | Toggle storage format (JSON/CSV) |
| 12 | Launch graphical interface |
| 0 | Exit |

## Project structure

| Path | Purpose |
|---|---|
| `main.py` | Console dispatch loop, configuration and handlers |
| `models.py` | `Trip` dataclass with derived timing/duration |
| `validation.py` | Input wrappers and domain validation |
| `storage.py` | JSON/CSV adapter with corruption recovery |
| `service.py` | CRUD, search, analytics and warnings |
| `reports.py` | Exports and bar charts |
| `ui.py` | ANSI console UI, tables and pagination |
| `gui.py` | Tkinter desktop interface |
| `seed.py` | Sample dataset generator |
| `data/` | Active store, config and sample datasets |
| `exports/` | Generated reports |

## Data model

| Field | Type | Rule |
|---|---|---|
| `id` | int | Auto-incrementing unique identifier |
| `destination` | str | Required, 1–200 characters |
| `start_date` / `end_date` | ISO date | `YYYY-MM-DD`; end must not precede start |
| `category` | enum | Leisure, Business, Adventure, Family, Cultural, Solo |
| `notes` | str | Optional, max 300 characters |
| `estimated_cost` | float | Numeric, non-negative |
| `status` | enum | Planned, Booked, In Progress, Completed, Cancelled |
| `created_at` | timestamp | ISO creation timestamp |

## Demo flow

1. Launch the app and show the welcome screen.
2. Add a trip, intentionally entering invalid input to demonstrate validation.
3. Run analytics to show totals, averages and distribution charts.
4. Display threshold warnings for overdue trips and high costs.
5. Restart the app to prove persistence.
6. Export a report.
7. Launch the Tkinter GUI to demonstrate the desktop experience.

## Testing

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The suite covers 50 cases across models, validation, storage (including corrupted-file recovery and atomic writes), service logic, fuzzy search, warnings, summaries and report exports.

## Reliability features

- Structured file logging to `logs/app.log` with timestamps and severity levels.
- Cross-platform advisory file locking and atomic file replacement for safe concurrent access.
- Automatic `.bak` snapshots on every write with a `Storage.restore_backup()` recovery path.
- Optional fuzzy search in the console app (and typo-tolerant search in the web app).

## Advanced capabilities

- **Natural-language queries:** console option 3 accepts phrases such as `trips to Paris under 3000 booked`; the web search box parses the same intent on Enter.
- **Predictive analytics:** `InsightsEngine.linear_forecast()` extrapolates next-month spend using least-squares regression.
- **Offline PWA:** the web app is installable and caches its shell with a service worker.
- **Undo/redo:** the GUI supports toolbar buttons and `Ctrl+Z` / `Ctrl+Y`.

## Database backends

Switch between local file storage (JSON/CSV) and an SQLite database without losing data:

- Console: option **14** (Toggle database backend).
- GUI: **DB backend** button in the toolbar.
- Configuration is persisted in `data/config.json` under `backend` (`file` or `sqlite`).

## Smart insights

The `InsightsEngine` produces monthly spend trends, the busiest month, anomaly detection using
z-scores, trips in the next 30 days and a forecast spend estimate. Available through console
option **13**, the GUI Summary tab and the web app.

## Documentation

Detailed documentation is available in `TravelItineraryOrganizer_Documentation.docx`, and the slide deck in `TravelItineraryOrganizer_Presentation.pptx`.
