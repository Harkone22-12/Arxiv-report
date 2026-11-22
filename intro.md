# arXiv Scraping & Mining — Group 10

Report of **Group 10** for the arXiv project of **Introduction to Data Science** (Faculty of Information
Technology, University of Science, VNU-HCM).

The project follows scientific papers from **arXiv** through three milestones: crawling the LaTeX sources
and metadata of an assigned range of papers, parsing them into a structured corpus, and matching their
bibliography entries to the papers they cite. This book documents the methods, the resulting data and the
performance of each milestone; it currently covers **Milestone 1 — Data Crawling** and **Milestone 2 —
Parsing and Standardization**.

- **Report (this site):** <https://harkone22-12.github.io/Arxiv-report/> · source:
  <https://github.com/Harkone22-12/Arxiv-report>
- **Code repository:** <https://github.com/thinhelzan842/intro-ds-arxiv-project> (source in `src/`, set-up
  and run instructions in `README.md`)
- **Project statement:** [Milestone 1 — Crawling](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/),
  [Milestone 2 — Parsing](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/parsing/)

## Team

| Student ID | Name | Milestone 1 | Milestone 2 |
| :---: | :--- | :--- | :--- |
| `24127361` | La Anh Hào | entry discovery, coordination, pipeline (`00_config`, `01_discovery`, `05_run_pipeline`) | element IDs, full-text deduplication, tables, the run over all papers (`13_dedup_export`, `15_run_parsing`, `16_test_m2_1000_papers`) |
| `24127016` | Võ Nguyễn Vân Anh | source download and extraction (`02_download`) | root file, multi-file gathering, document tree (`10_parse_tree`) |
| `24127223` | Lưu Minh Quân | reference metadata (`03_references`) | BibTeX extraction, reference deduplication (`12_bibtex`) |
| `24127244` | Phạm Tấn Nhật Thịnh | monitoring, statistics, report (`04_monitor`, this book) | macros, cleanup, math, sentences (`11_normalize`) |

Everyone took part in the tests and in keeping the Colab sessions running.

## Objectives

**Milestone 1 — Data crawling.**

1. **Find every paper and every version.** Resolve the 20,000 arXiv IDs assigned to the group and the full
   version history of each paper.
2. **Collect the sources.** Download the LaTeX source of every version and keep only the `.tex` and `.bib`
   files, with their folder structure and their content untouched.
3. **Collect the metadata.** Paper metadata for every version from arXiv, and the reference list of every
   paper from Semantic Scholar.
4. **Measure the result.** Report how complete the crawl is and how much time, memory and disk it needs on a
   CPU-only Google Colab runtime, with every table and figure generated when this book is built.

**Milestone 2 — Parsing and standardization.**

1. **Read the structure.** For every version, find the main file, follow its `\input`/`\include` files and
   build the hierarchy of the document, from the document down to its sentences, formulas and figures.
2. **Standardize the content.** Remove the layout commands, expand the authors' macros, write all math one
   way, and convert the references to BibTeX.
3. **Deduplicate.** One BibTeX entry per cited work with the `\cite` keys renamed, and one element for every
   piece of text that is identical in several versions of a paper.
4. **Measure the result.** Report the parse success rate, the version coverage, the counts before and after
   deduplication, and the time, RAM and output size of the parser on a CPU-only Colab runtime.

## Pipeline

```text
Milestone 1 · Data crawling
  20,000 assigned arXiv IDs
    → entry discovery: which papers exist, how many versions, metadata of every version
    → source download: every version, only .tex and .bib kept
    → reference metadata from Semantic Scholar
         │
         ▼
Milestone 2 · Parsing and standardisation
  LaTeX sources of every version
    → root file and multi-file gathering → document tree (sections … sentences, formulas, figures)
    → macros expanded, layout removed, math normalized, BibTeX extracted and deduplicated
    → element IDs shared across versions: tables elements, hierarchy, bibtex
         │
         ▼
Milestone 3 · Citation matching                                    (next)
  BibTeX entries ↔ crawled references, evaluated with MRR
```

## How this report is organised

Each milestone has the same five chapters.

**Milestone 1 — Data Crawling**

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

**Milestone 2 — Parsing and Standardization**

::::{grid} 1 1 2 2

:::{card} [1. Overview](milestone2/overview.md)
The four steps of the parser and who wrote them, how each requirement of the statement is met, the output
layout and the three tables.
:::

:::{card} [2. Implementation](milestone2/hierarchy.md)
Root file and multi-file gathering, the document tree, macros and cleanup, math, sentences, BibTeX, element
IDs and deduplication, and the run over 20,000 papers.
:::

:::{card} [3. Parsing statistics](milestone2/statistics.ipynb)
Parse success rate, version coverage of every paper, size of the trees, elements and BibTeX entries before
and after deduplication.
:::

:::{card} [4. Parser performance](milestone2/performance.ipynb)
Running time, maximum RAM, output size and the summary table of the required metrics.
:::

::::

Each milestone ends with a short conclusion ([Milestone 1](milestone1/conclusion.ipynb),
[Milestone 2](milestone2/conclusion.ipynb)): the key results and the limitations we know of.

:::{note}
Chapters 3, 4 and 5 of each milestone, and chapter 2.4 of Milestone 2, are notebooks that are **executed
when the book is built**. Their tables, figures and the numbers in their text are computed from the log
files stored in `data/` of the report repository; none of them is a screenshot or typed by hand. The code of
every cell can be unfolded on the page.
:::
