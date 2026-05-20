# Competitor Tracker MVP

Local Python MVP for tracking competitor hiring changes from ATS job boards.

## Features

- Scrape jobs from Greenhouse and Lever APIs
- Normalize all jobs into one schema
- Persist current postings and historical snapshots in SQLite
- Detect new, removed, and updated job descriptions
- Print a simple markdown-like diff report in CLI

## Project Structure

```
competitor_tracker/
├── app/
│   ├── analysis/diff.py
│   ├── config.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   ├── schemas/job.py
│   ├── scrapers/
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── greenhouse.py
│   │   └── lever.py
│   └── services/
│       ├── generate_diff_report.py
│       └── scrape_company.py
├── competitors.yaml
├── main.py
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py scrape
python main.py report
```

## Notes

- SQLite DB file is created as `competitor_tracker.db` in project root.
- To add more companies, edit `competitors.yaml`.
- To add more ATS providers, implement a new scraper in `app/scrapers/` and register it in `factory.py`.
