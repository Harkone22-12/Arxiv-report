# arXiv Project Report — Group 10

Source of the report of Group 10 for the arXiv project of *Introduction to Data Science* (HCMUS).

- **Published report:** <https://harkone22-12.github.io/Arxiv-report/>
- **Code repository:** <https://github.com/thinhelzan842/intro-ds-arxiv-project>
- **Project statement:** <https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/>

The report is a Jupyter Book 2 (MyST) site. Chapters 3–5 are notebooks that are **executed when the book is
built**: every table, figure and number in them is computed from the files in `data/`; nothing is a pasted
screenshot.

## Layout

```text
├── myst.yml                     book configuration and table of contents
├── intro.md                     landing page
├── milestone1/
│   ├── overview.md              1. Overview
│   ├── discovery.md             2.1 Entry discovery
│   ├── download.md              2.2 Source download
│   ├── extraction.md            2.3 Extraction and figure removal
│   ├── references.md            2.4 Reference metadata
│   ├── tools.md                 2.5 Tools and libraries
│   ├── statistics.ipynb         3. Data statistics            (executed at build time)
│   ├── performance.ipynb        4. Scraper performance        (executed at build time)
│   ├── conclusion.ipynb         5. Conclusion                 (executed at build time)
│   └── report_data.py           loaders and table/chart helpers shared by the notebooks
├── data/                        log files of the crawl that the notebooks read
├── tools/export_report_data.py  builds data/ from the crawl folder
└── .github/workflows/deploy.yml builds the book and deploys it to GitHub Pages on every push to main
```

## Updating the data

`data/` is produced from the crawl folder (`MyDrive/arxiv-project` on Colab, or a local copy of it), which
must contain `logs/`, `state/` and `data/raw/`:

```bash
python tools/export_report_data.py <crawl folder>
```

The script copies the pipeline's own logs and derives a few small per-item files; the crawl folder is not
modified.

| File in `data/` | Source in the crawl folder | Content |
|---|---|---|
| `benchmark.json` | `logs/benchmark.json` | the Milestone 1 metrics over all Colab sessions |
| `benchmark_sessions.jsonl` | `logs/benchmark_sessions.jsonl` | one record per session: wall time, stages, RAM, disk |
| `performance.json` | `logs/performance.json` | RAM time series |
| `papers.csv` | `logs/papers.csv` | one row per assigned ID: versions, sizes, references, time |
| `run_history.jsonl` | `state/download/run_history.jsonl` | one record per run of the downloader |
| `metadata.csv` | `state/discovery_manifest.json` | versions, primary category and dates of every paper |
| `versions.csv` | `state/download/receipts.jsonl` | one row per processed source version |
| `download_events.csv` | `state/download/errors.jsonl`, `throttles.jsonl` | failed and refused requests |
| `references_log.csv` | `logs/references.csv` | one row per logged reference request |
| `reference_fields.json` | `data/raw/*/references.json` | field completeness over all saved references |
| `corpus_check.json` | receipts against `data/raw/` | `ok` receipts whose version folder is missing |

If a file is missing, the notebooks stop with a message naming it and the build fails instead of publishing
a broken page.

## Building locally

```bash
pip install -r requirements.txt
jupyter book build --html --execute
```

The site is written to `_build/html`. `jupyter book start --execute` serves it with live reload. To build
from another folder of data files, set `REPORT_DATA_DIR=/path/to/data`.

## Publishing

Pushing to `main` runs `.github/workflows/deploy.yml`, which installs `requirements.txt`, executes the
notebooks, builds the HTML and deploys it to GitHub Pages (**Settings → Pages → Source: GitHub Actions**).
