# 1. Overview

*Author: La Anh Hào · code: `src/13_dedup_export.ipynb`, `src/15_run_parsing.ipynb`*

## 1.1 Goal and scope

Milestone 2 turns the LaTeX sources collected in Milestone 1 into a structured corpus. For every version of
every paper of the group (20,000 papers, 27,035 versions), the parser must find the main file among the
`.tex` files, follow its `\input` and `\include` commands, and build the **hierarchy** of the document, from
the document itself down to its sentences, formulas and figures. The text is **standardized** (layout
commands removed, macros expanded, math written one way) and **deduplicated** twice: the references of a
paper are merged into one BibTeX entry per work, and an element that is identical in several versions of a
paper is stored once.

The work was split along the four steps of the parser, one notebook each:

| Step | Notebook | Owner | Described in |
|---|---|---|---|
| root file, multi-file gathering, document tree | `src/10_parse_tree.ipynb` | Võ Nguyễn Vân Anh | [2.1](hierarchy.md) |
| macro expansion, LaTeX cleanup, math normalization, sentence splitting | `src/11_normalize.ipynb` | Phạm Tấn Nhật Thịnh | [2.2](normalization.md) |
| BibTeX extraction, reference deduplication, `\cite` renaming | `src/12_bibtex.ipynb` | Lưu Minh Quân | [2.3](references.md) |
| element IDs, full-text deduplication, the three tables; the run over all papers | `src/13_dedup_export.ipynb`, `src/15_run_parsing.ipynb` | La Anh Hào | [2.4](deduplication.ipynb), [2.5](running.md) |

Chapter [3](statistics.ipynb) reports what the parser produced, chapter [4](performance.ipynb) its running
time and memory, and chapter [5](conclusion.ipynb) the conclusions and limitations.

## 1.2 Requirements of the statement and where they are met

| Requirement of the statement | How the parser meets it | Described in |
|---|---|---|
| The root is the `.tex` file with `\documentclass`; follow `\input`/`\include` transitively; files not reached from the root are ignored | `find_root` ranks the candidates that declare a document class, `gather` expands the inclusions recursively from the root only | [2.1](hierarchy.md) |
| A commented-out inclusion is plain text | comments are removed before the inclusions are searched | [2.1](hierarchy.md) |
| Hierarchy: document, chapters/sections, subsections and deeper levels, detected automatically | a heading is attached to the nearest open heading of a higher level, so the depth comes from the document | [2.1](hierarchy.md) |
| Leaves: sentences, block formulas, figures (tables count as figures); lists branch into items | `build_tree` produces `sentence`, `formula` and `figure` leaves, `itemize` nodes with `item` children | [2.1](hierarchy.md) |
| References sections are not parsed; acknowledgements and appendices are | a References/Bibliography section and the bibliography commands are skipped; `\appendix` and acknowledgements are kept | [2.1](hierarchy.md) |
| Sentences end at a period, not inside math, commands, abbreviations, URLs or decimal numbers | `split_sentences` masks those spans before splitting | [2.2](normalization.md) |
| Remove non-semantic commands (`\centering`, `[htpb]`, `\midrule`, ...) | `clean_latex` | [2.2](normalization.md) |
| Inline math as `$...$`, block math as `\begin{equation}...\end{equation}` | `normalize_math` | [2.2](normalization.md) |
| `\bibitem` entries converted to BibTeX | `extract_bib` parses `.bib` files and converts `thebibliography` lists | [2.3](references.md) |
| Reference dedup: one key per work, `\cite` renamed, fields unioned | `dedup_bib` and `rename_cites` | [2.3](references.md) |
| Full-text dedup: identical cleaned elements across versions share one `element_id` | `parse_paper` gives IDs through content keys | [2.4](deduplication.ipynb) |
| Tables `elements`, `hierarchy`, `bibtex` with the given columns | Parquet files with exactly the statement's columns and types | [1.5](#m2-tables) |
| A version without TeX source is recorded as empty, not skipped | every version of `metadata.json` gets a status; `empty_source` versions have no rows | [3.1](statistics.ipynb) |
| Statistics: parse success rate, version coverage, counts before/after dedup | computed from the run's logs when the book is built | [3](statistics.ipynb) |
| Performance: wall time, time per paper, maximum RAM, output size, on CPU-only Colab | session records written by `15_run_parsing` | [4](performance.ipynb) |

## 1.3 Pipeline

`src/15_run_parsing.ipynb`, run on Google Colab (CPU), parses every paper. It loads `13_dedup_export`, which
loads the definitions of notebooks `10`–`12` (not their demonstration cells), each in its own namespace, and
binds them to one interface. For one paper, `parse_paper` does:

```text
for every version v1 … vN listed in metadata.json
    no vN/ folder or no .tex file  → status empty_source, no rows
    find_root (10)                 → no file with \documentclass: status no_root, no rows
    gather (10)                    → the root with its \input/\include files inlined, comments removed
    extract_bib, bib_source (12)   → the BibTeX entries of the version, read from the raw text
once for the paper
    dedup_bib (12)                 → one entry per work, and the map from old to chosen citation keys
for every parsed version
    expand_macros → clean_latex → normalize_math (11) → rename_cites (12)
    build_tree (10, with split_sentences of 11)        → the tree of the version
    element IDs and full-text deduplication (13)       → rows of elements and hierarchy
```

A failure inside one version (an exception in any step) makes that version `error` and the others go on.
The citations are renamed **before** the tree is built, so a sentence that cites `a` in v1 and the same
work as `b` in v2 is still one element after deduplication.

## 1.4 Data layout

```text
MyDrive/arxiv-project/
├── data/raw/<id>/          the corpus of Milestone 1 (only read)
├── data/parsed/<id>.json   one file per paper: status of every version, the tree of every version with its
│                           element IDs, and the rows of the three tables (enough for Milestone 3)
├── data/m2/                elements.parquet, hierarchy.parquet, bibtex.parquet
├── state/m2/done.jsonl     resume index: one summary per parsed paper and parser version
└── logs/                   m2_parse_status.csv (one row per version), m2_stats.json, m2_benchmark.json,
                            m2_benchmark_sessions.jsonl, m2_ram_timeseries.csv
```

The raw folders of Milestone 1 are never written to. No data file is committed to the code repository.

(m2-tables)=
## 1.5 Dataset tables

The three tables have exactly the columns of the statement; the element kind and the entry type are
dictionary-encoded strings in Parquet.

### Table `elements`

| Column | Type | Description |
| :--- | :--- | :--- |
| `element_id` | string, non-null | `<paper folder>#<prefix><n>`, e.g. `2609-32834#s12` (chapter [2.4](deduplication.ipynb)) |
| `arxiv_id` | string, non-null | the paper, e.g. `2609.32834` |
| `kind` | string (dictionary) | `document`, `chapter`, `section`, `subsection`, `subsubsection`, `paragraph`, `abstract`, `itemize`, `item`, `sentence`, `formula`, `figure` |
| `content` | string | the cleaned title of a heading, the cleaned text of a leaf |

One row per distinct element of a paper over all its versions.

### Table `hierarchy`

| Column | Type | Description |
| :--- | :--- | :--- |
| `arxiv_id` | string, non-null | the paper |
| `version` | int | the version |
| `element_id` | string, non-null | the child |
| `parent_id` | string, non-null | its parent in that version |

One row per node–parent edge of each version, in document order. The document node has no parent, so it has
an `elements` row and no `hierarchy` row; in every version, the only parent that is never a child is
`<paper folder>#doc`.

### Table `bibtex`

| Column | Type | Description |
| :--- | :--- | :--- |
| `arxiv_id` | string, non-null | the citing paper |
| `citation_key` | string, non-null | the key chosen for the work, the one the renamed `\cite` commands use |
| `entry_type` | string (dictionary) | `article`, `inproceedings`, `misc`, ... |
| `title` | string | |
| `authors` | list of strings | |
| `year` | int, nullable | |
| `doi` | string | without the `https://doi.org/` prefix |
| `journal` | string | `journal`, else `booktitle` |
| `url` | string | `url`, else the arXiv abstract page of the work |

One row per work cited by the paper, after deduplication over all its versions.
