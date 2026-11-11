# arXiv Scraping & Mining — Group 10

Report of **Group 10** for the arXiv project of **Introduction to Data Science** (Faculty of Information
Technology, University of Science, VNU-HCM).

The project follows scientific papers from **arXiv** through three milestones: crawling the LaTeX sources
and metadata of an assigned range of papers, parsing them into a structured corpus, and matching their
bibliography entries to the papers they cite. This book documents the methods, the resulting data and the
performance of each milestone; it currently covers **Milestone 1 — Data Crawling**.

- **Report (this site):** <https://harkone22-12.github.io/Arxiv-report/> · source:
  <https://github.com/Harkone22-12/Arxiv-report>
- **Code repository:** <https://github.com/thinhelzan842/intro-ds-arxiv-project> (source in `src/`, set-up
  and run instructions in `README.md`)
- **Project statement:** [Milestone 1 — Crawling](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/)

## Team

| Student ID | Name | Role in Milestone 1 | Main deliverables |
| :---: | :--- | :--- | :--- |
| `24127361` | La Anh Hào | entry discovery, coordination, pipeline | `00_config.ipynb`, `01_discovery.ipynb`, `05_run_pipeline.ipynb` |
| `24127016` | Võ Nguyễn Vân Anh | source download and extraction | `02_download.ipynb` |
| `24127223` | Lưu Minh Quân | reference metadata | `03_references.ipynb` |
| `24127244` | Phạm Tấn Nhật Thịnh | monitoring, statistics, report | `04_monitor.ipynb`, this book |

Everyone took part in the tests (`06_test_100_versions.ipynb`, `07_run_references.ipynb`) and in keeping the
Colab sessions of the crawl running.

## Objectives

1. **Find every paper and every version.** Resolve the 20,000 arXiv IDs assigned to the group and the full
   version history of each paper.
2. **Collect the sources.** Download the LaTeX source of every version and keep only the `.tex` and `.bib`
   files, with their folder structure and their content untouched.
3. **Collect the metadata.** Paper metadata for every version from arXiv, and the reference list of every
   paper from Semantic Scholar.
4. **Measure the result.** Report how complete the crawl is and how much time, memory and disk it needs on a
   CPU-only Google Colab runtime, with every table and figure generated when this book is built.

## Pipeline

```text
Milestone 1 · Data crawling                                        (this report)
  20,000 assigned arXiv IDs
    → entry discovery: which papers exist, how many versions, metadata of every version
    → source download: every version, only .tex and .bib kept
    → reference metadata from Semantic Scholar
         │
         ▼
Milestone 2 · Parsing and standardisation                          (next)
  LaTeX sources → document hierarchy, cleaned text, unified BibTeX entries
         │
         ▼
Milestone 3 · Citation matching                                    (next)
  BibTeX entries ↔ crawled references, evaluated with MRR
```

## How this report is organised

::::{grid} 1 1 2 2

:::{card} [1. Overview](milestone1/overview.md)
Goal and scope of the milestone, how each requirement of the statement is met, the pipeline and the layout
of the data.
:::

:::{card} [2. Implementation](milestone1/discovery.md)
Entry discovery, source download, extraction and figure removal, reference metadata, tools and libraries.
:::

:::{card} [3. Data statistics](milestone1/statistics.ipynb)
Success rates and failures, paper size before and after figure removal, references, versions, subjects and
dates.
:::

:::{card} [4. Scraper performance](milestone1/performance.ipynb)
Running time, memory and disk footprint, the summary table of the required metrics, and what limits the
speed.
:::

::::

The milestone ends with a short [conclusion](milestone1/conclusion.ipynb): the key results and the
limitations we know of.

:::{note}
Chapters 3, 4 and 5 are notebooks that are **executed when the book is built**. Their tables, figures and
the numbers in their text are computed from the log files of the crawl stored in `data/` of the report
repository; none of them is a screenshot or typed by hand. The code of every cell can be unfolded on the
page.
:::
