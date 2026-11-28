# 2.5 Running the pipeline, requirement checks and Hugging Face export

*Authors: La Anh Hào (`25_run_m3`, `26_export_hf`), Phạm Tấn Nhật Thịnh (`24_analysis`)*

## 2.5.1 End-to-end orchestration (`25_run_m3`)

`src/25_run_m3.ipynb` runs all six Milestone 3 stages in a fixed dependency order (`data → labels → features →
model → analysis → export`) on Google Colab CPU, writing an auditable history to `logs/m3_run.json` (code
commit, locked parser version `13.9|10:team|11:team|12:team`, `data/m3/` signature, per-step duration, key
counts, and any stale outputs).

- **Freshness and staleness protection.** `stale_steps()` compares modification timestamps of every step's
  inputs and outputs so that a change to a manual sheet or model never leaves downstream tables out of date.
- **Namespace hygiene.** Notebooks `20`, `21`, `22`, `23` and `26` share a single namespace verified by
  `name_clashes()`, while `24_analysis` is executed via `run_isolated()` in its own namespace so its helper
  definitions never shadow pipeline symbols.

The complete production run on **28 Nov 2026** (commit `8c3ee1a`) executed all data, labelling, feature,
modelling and export steps in **6,622.7 s (1 h 50 min)**, followed by two verification runs of `24_analysis`
on commit `689e914` (139.8 s and 132.8 s) with **0 stale steps**. Full step timings are shown in chapter
[4.4](results.ipynb).

## 2.5.2 Automated requirement checks (`24_analysis`)

`src/24_analysis.ipynb` is a read-only auditor that loads all 19 intermediate and final Milestone 3 artifacts
independently and tests **23 formal rules** derived from the Milestone 3 statement and the instructor's Q&A:

- manual quotas (≥ 20 papers, ≥ 5 per member, ≥ 20 matched pairs per manual paper, ≥ 400 pairs total);
- label integrity (one label per entry, every entry labelled, every target reference inside the same paper);
- automatic coverage (≥ 8 papers, 0 hand-labelled or `manual_old` papers in auto, ≥ 10% overall and ≥ 10% per
  member);
- split invariants (4 manual + 4 auto in test, 4 manual + 4 auto in valid, disjoint and consistent with
  source);
- `predictions` schema and semantics (`nil_mode_main = "skip"`, 9 statement columns, 81,329 matched-entry
  rows across 3,733 labelled papers—with the 40 labelled papers that have 0 matched pairs properly omitted—0
  ground-truth discrepancies, 0 invalid or duplicated candidates).

All **23 / 23 checks passed (`PASS`)** in `logs/m3_requirements.json` (complete table in chapter
[4.4](results.ipynb)).

## 2.5.3 Hugging Face Parquet export (`26_export_hf`)

Per Q&A M3 #2 and #5, the group shares one pipeline while **each member uploads their own 5,000-paper ID
range** as a public Hugging Face dataset using their own write `HF_TOKEN`. `src/26_export_hf.ipynb` streams
each source table once, partitions rows strictly by `member_of(arxiv_id)`, casts every batch to the explicit
Arrow schemas of `HF_SCHEMAS` (flat primitives, `list<string>` for authors and `revised_dates`, dictionary
encoding for `kind`, `entry_type` and `partition`, `int32` for `version` and nullable `year`, non-null key
constraints), and writes sharded Parquet files (`train-0000i-of-0000n.parquet`) plus a YAML dataset card
`README.md` (with one `configs` entry per table and no custom loading script):

```text
hf/<member>/
├── README.md
└── data/
    ├── papers/train-00000-of-00001.parquet
    ├── references/train-00000-of-00001.parquet
    ├── elements/train-00000-of-0000N.parquet      (2–3 shards per member)
    ├── hierarchy/train-00000-of-00001.parquet
    ├── bibtex/train-00000-of-00001.parquet
    └── predictions/train-00000-of-00001.parquet
```

Before any upload, `check_export()` verifies every shard's schema, key non-nullness, ID range membership,
and cross-table foreign keys (`predictions` keys exist in `bibtex`, every ground truth and `cand_1..5` exists
in that paper's `references`). On the 28 Nov export (`logs/hf_export.json`, **1,027.2 s**), all six tables
summed exactly to the corpus totals with **0 rows outside the four ranges** and **0 rows not exported**:

- `papers`: 20,000 (5,000 per member)
- `references`: 383,562
- `elements`: 10,042,052
- `hierarchy`: 12,902,631
- `bibtex`: 766,398
- `predictions`: 81,329

After uploading (`upload_member()`), `check_hub()` reads back one row of every table via
`datasets.load_dataset(..., streaming=True)` to confirm the Hub viewer and streaming API work cleanly.
Per-member row and shard tables are displayed in chapter [4.5](results.ipynb), and dataset links are listed
in [1.5](overview.md).
