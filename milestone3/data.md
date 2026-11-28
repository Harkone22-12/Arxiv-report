# 2.1 Inputs of Milestone 3

*Author: La Anh Hào · code: `src/20_m3_data.ipynb`*

Milestone 3 joins two upstream sources—the standardized bibliography and document trees of Milestone 2
(`data/parsed/<fid>.json`) and the Semantic Scholar reference lists of Milestone 1
(`data/raw/<fid>/references.json`)—into three clean Parquet tables under `data/m3/` so that labelling,
feature engineering and modelling never re-read 40,000 raw JSON files from Google Drive.

## 2.1.1 Parser lock and reproducibility

Manual labels are keyed by `(arxiv_id, citation_key)`. Re-parsing a paper with a different parser version
could alter normalized citation keys and invalidate manual sheets. `20_m3_data` therefore enforces a strict
**parser lock** by reading each paper's `parser_version` from `state/m2/done.jsonl` and stopping before
writing anything if any paper disagrees with `M3_PARSER_VERSION = "13.9|10:team|11:team|12:team"`.

The final `data/m3/` snapshot (`data_version = "20.3"`, signature `da32f6a848f6`) was built on
**27 Nov 2026** in **1,733.1 s** (28.9 min) across all 20,000 papers, with **0** integrity problems reported
by `check_m3_tables`. Subsequent pipeline runs in `25_run_m3` verify the signature in 3.8 s and reuse the
frozen tables directly.

## 2.1.2 The three input tables

| Table | One row per | Rows (27 Nov build) | Columns |
|---|---|---:|---|
| `entries.parquet` | Deduplicated BibTeX entry of a publication | **766,398** | The 9 M2 `bibtex` columns + `bib_source`, `position`, `n_cites`, `context`, `sections` |
| `refs.parquet` | arXiv-keyed Semantic Scholar reference of a publication | **383,562** | The 6 M1 `references` columns + `ref_year`, `ref_doi`, `ref_venue`, `ref_position` |
| `pubs.parquet` | Publication in the four assigned ranges | **20,000** | `arxiv_id`, `member`, `n_entries`, `n_refs`, `eligible`, `parser_version`, `bib_source`, `n_cited_entries`, `n_refs_all`, `s2_status`, `m2_status` |

Key construction rules:

- **Citation contexts from Milestone 2 (`entries`).** For each paper, `citation_contexts()` walks every
  version's tree in document order (starting from `v1`), tracking the nearest enclosing `section`, `chapter`,
  or `abstract` title. Each leaf (`sentence`, `formula`, `figure`) containing a `\cite`-family command is
  counted **once per distinct M2 element** (`n_cites`) and contributes up to `CONTEXT_MAX = 10` citing
  sentences (`context`) plus their distinct enclosing heading titles (`sections`). Across the corpus, 98.51%
  of entries are cited in the text, while 93,225 cited keys have no matching entry in `bibtex` (mostly from
  `missing_bbl` versions or typos in author `\cite` keys).
- **arXiv reference deduplication (`refs`).** Only references carrying a valid arXiv ID (new- or old-style,
  normalized via `normalize_ref_arxiv_id` from `03_references`) enter `refs.parquet` (383,562 of 724,139
  total S2 references = 52.97%). Duplicate `(arxiv_id, ref_arxiv_id)` rows within a paper are dropped
  (0 duplicates found) so each paper's candidate matrix has one column per arXiv reference.
- **Resumable batched I/O.** Files are read with multi-threaded Drive I/O and written per batch through
  atomic temporary parts under `data/m3/_parts/<signature>/`, merged and verified at the end.

## 2.1.3 Eligibility and sampling pools

A publication is **eligible** for reference matching when it has at least one extracted BibTeX entry and at
least one arXiv-keyed S2 reference (`n_entries >= 1` and `n_refs >= 1`):

- **15,040 of 20,000 papers (75.20%)** are eligible, holding 643,139 entries and **19,790,582** total
  within-paper `(entry, reference)` pairs (median **38** entries and **18** arXiv references per eligible
  paper).
- Papers are ineligible primarily because Milestone 2 had no BibTeX entries (`empty_source`: 955 papers,
  `no_root`: 7 papers, `missing_bbl` / `none` bibliographies leaving 2,897 papers with 0 entries) or because
  Semantic Scholar returned 0 arXiv-keyed references (2,636 papers, including 11 `not_found` papers).
- **`MANUAL_POOL`** (`min_entries = 20`, `max_entries = 60`, `min_refs = 30` with M2 and S2 both `ok`):
  **8,007 papers** across the four members (1,762–2,230 per member), ensuring every manually labelled paper
  is large enough to yield ≥ 20 matched pairs while remaining tractable for careful human verification.
- **`SPLIT_POOL`** (`min_entries = 20`, `min_refs = 10`): **10,389 papers**, from which test and validation
  publications are drawn (for manual and automatic papers, `21_labeling` checks ≥ 20 matched pairs).

Per-member breakdowns of eligibility, entries, references and pools are plotted in chapter
[3.1](statistics.ipynb).
