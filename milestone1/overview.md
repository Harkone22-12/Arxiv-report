# 1. Overview

*Author: La Anh Hào · code: `src/05_run_pipeline.ipynb`*

## 1.1 Goal and scope

Milestone 1 builds the raw corpus that the next two milestones work on. For the **20,000 arXiv IDs**
assigned to the group, the scraper must find every paper and all of its versions, download the LaTeX source
of each version, keep only the text files, and collect the metadata of the papers and of the works they
cite.

The four assigned ranges hold 5,000 IDs each (both ends inclusive) and are listed in `ID_RANGES` in
`src/00_config.ipynb`. The report refers to them as R1–R4:

| | Range | IDs | ID prefix |
|---|---|---:|---|
| R1 | `2609.32834` – `2609.37833` | 5,000 | September 2026 |
| R2 | `2605.17338` – `2605.22337` | 5,000 | May 2026 |
| R3 | `2605.07338` – `2605.12337` | 5,000 | May 2026 |
| R4 | `2603.20580` – `2603.25579` | 5,000 | March 2026 |

The work has four parts, each described in its own section of chapter 2:

1. **Entry discovery** ([2.1](discovery.md)). Resolve each assigned ID with the arXiv API: does the paper
   exist, how many versions does it have, and what are the title, authors, dates and venue of every version.
   Harvesting the whole repository (OAI-PMH, the Kaggle snapshot) is outside the scope of the milestone and
   was not needed.
2. **Source download** ([2.2](download.md)). Request every version, `v1` to the latest, from the source
   mirror `export.arxiv.org`, one connection at a time and at least 3 s apart.
3. **Extraction and figure removal** ([2.3](extraction.md)). Unpack whatever arXiv returns and keep only the
   `.tex` and `.bib` files, byte for byte and with their folder structure. A version without LaTeX source
   keeps an empty record.
4. **Reference metadata** ([2.4](references.md)). Fetch the reference list of every paper from the Semantic
   Scholar API and keep all references locally, flagging the ones that have an arXiv ID.

Chapter [3](statistics.ipynb) reports what was collected, chapter [4](performance.ipynb) how fast and with
how much memory and disk, and chapter [5](conclusion.ipynb) the conclusions and limitations.

## 1.2 Requirements of the statement and where they are met

| Requirement of the statement | How the scraper meets it | Described in |
|---|---|---|
| Crawl **every version** of each paper; a single-submission paper uses `v1` | discovery reads the number of versions from the versioned ID of the latest version; the downloader requests `/src/{id}v{N}` for every `N` | [2.1](discovery.md), [2.2](download.md) |
| Use the `export.arxiv.org` mirror, a descriptive User-Agent, one connection, 3 s between requests | one `requests` session with a single-connection gate (`ARXIV_DELAY = 3.0` s) plus adaptive retry/cooldown; threads are used only for local extraction/Drive I/O and the separate Semantic Scholar API | [2.2](download.md) |
| Keep **only `.tex` and `.bib`** files, by extraction; no figure binaries | the extractor writes only members with these two extensions; the archive is deleted after unpacking (`.bbl` handling is documented in [2.3](extraction.md)) | [2.3](extraction.md) |
| Leave `figure` environments and `\includegraphics` untouched | the kept files are copied byte for byte; nothing in the TeX is edited | [2.3](extraction.md) |
| A version with no LaTeX source (or HTTP 404 at `/src/`) keeps an empty record | PDF-only versions get an empty `vN/` folder and `empty_source` receipt; persistent HTTP 404 versions are marked failed (`NOT_FOUND`) and carried into Milestone 2 as empty records (`empty_source`, reason `not_found`) | [2.2](download.md), [2.3](extraction.md), [3.1](statistics.ipynb) |
| Paper metadata for each version (title, authors, dates, venue) | `metadata.json` with one `version_info` record per version; crawl snapshot dates documented | [2.1](discovery.md) |
| Reference metadata from Semantic Scholar; keep all references, only arXiv-keyed ones become `references` rows | batch endpoint with flat fields; one `references.json` per publication (Semantic Scholar does not separate versions), `references_rows()` filters on the arXiv ID; 404s logged and kept as empty records | [2.4](references.md), [3.3](statistics.ipynb) |
| Tables `papers` and `references` with the given columns | `papers_rows()` and `references_rows()` build them from the saved files | [1.5](#tables) |
| Report statistics: papers scraped, success rate, size before/after, references per paper, reference success rate | computed from the crawl's logs when the book is built, across all 20,000 assigned IDs | [3](statistics.ipynb) |
| Report performance: time per paper, average, discovery time, peak and average RAM, maximum disk, output size, measured on CPU-only Colab | 30 Colab session records (retries and waits included), receipts and a `psutil` monitor thread, summed over the full 20,000-ID corpus | [4](performance.ipynb) |
| Figures and tables generated at compilation, no screenshots | chapters 3–5 are notebooks executed by the build | [3](statistics.ipynb), [4](performance.ipynb) |

## 1.3 Pipeline

The crawl is one notebook, `src/05_run_pipeline.ipynb`, run on Google Colab (CPU). It loads the notebooks of
the four members with `%run -i` and runs three stages:

```text
[setup]      clone/update the repository, install src/requirements.txt, mount Google Drive,
             read S2_API_KEY (Colab Secrets or .env), start the RAM monitor
   │
[1] discovery (01_discovery)              arXiv API, 100 IDs per request, one request every 3 s
   │   20,000 assigned IDs → which papers exist, how many versions, metadata of every version
   │   checkpoint after every batch → state/discovery_batches/, state/discovery_manifest.json
   ▼
[2] sources (02_download)  ─────────────  main thread, arXiv /src, one request every 3 s
   │   every version vN of every paper → raw archive on the local disk (/tmp)
   │     → 2 worker threads: unpack, keep only .tex/.bib, copy to Drive, write a receipt
   │
   └── references (03_references) ──────  background thread, Semantic Scholar batch API
           100 papers per request → references.json in the paper folder
   ▼
[3] report (04_monitor + 05)
       logs/papers.csv, logs/benchmark.json (all sessions), logs/performance.json, logs/figures/
```

Three design decisions shape everything else:

- **Batch whatever the service lets us batch.** The 3 s interval of arXiv is per request, not per paper, so
  discovery asks for 100 IDs per call and the references for 100 papers per call. Only the sources need one
  request per version.
- **Never let our own work add to the request interval.** Unpacking and the slow writes to Google Drive run
  in worker threads while the main thread waits for its next request slot, and the references run on a
  separate thread against a different service with its own rate limit.
- **Every stage resumes from what is on Drive.** A free Colab session ends after some hours and the crawl
  needs many of them, so each finished batch and each finished version leaves a checkpoint, and running the
  notebook again continues where the last session stopped.

`src/06_test_100_versions.ipynb` runs the same pipeline on the first 100 source versions only, in a separate
folder, and checks the result; every change was tested with it before the full crawl.

## 1.4 Data layout and organization decisions

The statement's working folder layout is a suggestion, and our group adapted it deliberately: one folder per
paper, named after its ID with the dot replaced by a hyphen, containing the `.tex` and `.bib` files of every
version, one `metadata.json` holding per-version metadata, and one `references.json` for the publication.

- **Why one `references.json` per publication instead of per version.** The Semantic Scholar Graph API
  returns one reference list per arXiv publication and does not distinguish individual arXiv revisions (a
  versioned ID such as `2609.32867v1` returns `null`). Duplicating the same list inside every `vN/` folder
  would waste storage without adding version granularity. Instead, we store `references.json` once at the
  paper level and preserve every version's submission and revision dates in `metadata.json` (`submitted`,
  `revised`, `version_info`), which populates `revised_dates` in the `papers` table.
- **Why multi-session checkpoints on Google Drive.** The final benchmark ran on all 20,000 assigned IDs on a
  CPU-only Google Colab runtime. Because 27,035 versions at ≥ 3 s per request exceed Colab's ~12-hour session
  limit, we split execution across 30 resumable sessions, kept every per-session log in
  `benchmark_sessions.jsonl`, and summed them in `benchmark.json` (chapter [4](performance.ipynb)).

```text
MyDrive/arxiv-project/
├── data/raw/
│   └── 2609-32834/
│       ├── metadata.json        paper metadata, one record per version (title, authors, dates, venue, ...)
│       ├── references.json      every reference found by Semantic Scholar (not only arXiv ones)
│       ├── v1/                  .tex and .bib files of version 1, original folder structure kept
│       └── v2/                  ... one folder per version; empty if the version has no LaTeX source
├── state/                       resume state: discovery manifest and batches, download receipts, errors
└── logs/                        papers.csv, references.csv, benchmark.json, performance.json, figures/
```

No data file is committed to the code repository; the corpus lives on Google Drive, and only the small log
files that this report is built from are copied to the report repository.

(tables)=
## 1.5 Dataset tables

### Table `papers`

| Column | Type | Description |
| :--- | :--- | :--- |
| `arxiv_id` | string (PK) | base arXiv identifier (e.g. `2310.12345`) |
| `title` | string | paper title |
| `authors` | list of strings | author names |
| `submission_date` | string (ISO) | date of the first version (v1) |
| `revised_dates` | list of strings | dates of the later versions |
| `venue` | string (nullable) | journal reference, if any |

`metadata.json` keeps its own field names (`id`, `submitted`, `revised`) and adds `status`, `versions` and
`version_info` (title, authors, abstract, date, `journal_ref`, DOI, comment and categories of every version).
`papers_rows()` in `01_discovery.ipynb` turns the saved files into the rows of this table.

### Table `references`

| Column | Type | Description |
| :--- | :--- | :--- |
| `arxiv_id` | string (FK) | citing paper |
| `ref_arxiv_id` | string | arXiv identifier of the cited paper |
| `ref_title` | string | title of the cited work |
| `ref_authors` | list of strings | authors of the cited work |
| `ref_submission_date` | string | submission date of the cited work |
| `ref_s2_id` | string | Semantic Scholar paper ID |

Only references that carry an arXiv ID become rows of `references` (`references_rows()` in
`03_references.ipynb`); all of them stay in `references.json`.
