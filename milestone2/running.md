# 2.5 Running the parser on 20,000 papers

*Author: La Anh Hào · code: `src/15_run_parsing.ipynb`, `src/16_test_m2_1000_papers.ipynb`*

`parse_paper` handles one paper. `src/15_run_parsing.ipynb` runs it over the whole corpus on Google Colab,
where a session can end at any time and the files are on Google Drive. It was written for three goals: use
the time of a session well, never lose finished work, and never let one paper stop or block the run.

## 2.5.1 Parallel parsing

Reading thousands of small files from Drive, not the CPU, limits the speed. `15` therefore parses in a pool of
worker processes (six on the 2-core Colab runtime), started with `fork` so that the functions loaded from the
notebooks exist in the workers. Each task is one paper; the worker writes `data/parsed/<id>.json` and returns a
short summary (statuses, node and row counts, seconds), so the main process never holds the rows of the
corpus. Within a paper, each file is read once and each text scanned once (the root search and the gathering
share a per-paper cache, emptied after the paper).

The parser itself was profiled on 900 papers before the run: replacing character-by-character loops by
regular-expression jumps, and repeated searches by one pass over the text, cut the time on that sample from
52.9 s to about 30 s with byte-identical output (checked with a SHA-256 fingerprint of every paper's output).

## 2.5.2 Never blocked by one paper

Some sources are pathological: unclosed braces or math, recursive macros, a 50 MB `.bib`. Each case met in
the corpus became a regression test, and the parsing functions were made to fall back to a linear pass when
the input is malformed: each of 20 malformed stress inputs is parsed in less than 15 s. On top of that, `15`
bounds the time of every paper:

- a worker stops a paper after `PAPER_TIMEOUT` (600 s, with `SIGALRM`, which also interrupts a regular
  expression stuck in C code), records its versions as `error` with the reason `timeout`, and goes on;
- the main process supervises the workers: if a worker dies or stops answering, it gives the paper up after
  the time limit plus a grace period, replaces the pool and submits the other papers again;
- the papers given up are listed in `state/m2/failed.jsonl` and skipped by later sessions unless
  `RETRY_FAILED = True`.

These mechanisms were tested on Colab with a deliberately endless loop, a catastrophic regular expression and
a killed worker (`src/16_test_m2_1000_papers.ipynb`). In the full run with parser 13.7, no paper reached the
limit.

## 2.5.3 Resume and versioning

Every parsed paper appends one line to the resume index `state/m2/done.jsonl`, with its summary and the
**parser version**. The version is `13.<n>|10:…|11:…|12:…`: the base number changes whenever the output of
`parse_paper` changes, and the other parts say which notebooks provided each step. A new session skips the
papers already parsed with the current version, so after a disconnection the notebook is simply run again; a
paper parsed by an older version is parsed again.

**From 13.7 to 13.8.** The full run was made with parser 13.7. Its results showed two problems (chapter
[2.1](hierarchy.md): files with carriage-return line ends; chapter [2.2](normalization.md): nested macro
definitions), fixed in 13.8. Rather than parsing all 20,000 papers again, the papers that 13.8 can change were
listed from their files alone: a `.tex` file with a carriage return, or with a macro definition that holds
another definition, is not closed in its file or holds an `\input` (1,775 papers). On a local copy of the
corpus, the outputs of 13.7 and 13.8 differ for 436 papers, all in that list. The 13.8 session parsed the
list again, plus a random sample of 300 other papers, whose new files had to be identical to their 13.7 files
to confirm that the other papers could be kept; the 13.7 results of the remaining papers were kept under the
new version.

The 13.8 session parsed 2,075 papers (the 1,775 of the list and the sample) in 47 min, against 2 h 47 min for
a full pass (chapter [4](performance.ipynb)). The 300 papers of the sample gave the same files as with 13.7
(compared by a hash of each file without the parser version and the times; any difference would have failed
the checks of section 2.5.4, which reported no problem), and over the corpus the run changed exactly what the
local comparison had predicted: two more versions `ok` (the two `no_root` versions of chapter [2.1](hierarchy.md)), 589 fewer tree
nodes, 806 fewer elements, and 54 and 52 more BibTeX entries before and after deduplication.

**From 13.8 to 13.9 (27 Nov 2026).** Manual inspection during Milestone 3 uncovered the REVTeX `\bibitem`
problem described in chapter [2.3](references.md). Because `revtex_to_fields` can only affect papers whose
`.tex` or `.bbl` files contain `\BibitemOpen`, `REPARSE_13_9` targeted only those **190 papers** while
`CARRY_OVER` kept the 13.8 outputs of the rest. A verification check re-parsed a non-REVTeX sample (128/128
identical) together with all 20 Milestone 3 manually labelled papers (20/20 identical), confirming that none
of the carried-over papers or manual-label keys changed. Across the full corpus, BibTeX entries after
deduplication moved from 766,356 to **766,398** (out of 1,023,822 before deduplication) and deduplicated
elements from 10,042,014 to **10,042,052** (out of 12,928,391 tree nodes). The parser is locked at
`13.9|10:team|11:team|12:team` for all Milestone 3 tables.

| Parser | Date | Change | Papers re-parsed | Carry-over verification |
|---|---|---|---|---|
| `13.7` | 21 Nov 2026 | First full run on all 20,000 papers | 20,000 (2 h 47 min) | — |
| `13.8` | 22 Nov 2026 | CR-only line endings (`10`) and nested macro definitions (`11`) | 1,775 flagged + 300 random (47 min) | 300/300 random unchanged; 436 flagged changed |
| `13.9` | 27 Nov 2026 | REVTeX `\bibinfo` extraction (`12`, 41 tests) | 190 with `\BibitemOpen` (`REPARSE_13_9`) + verification sample (31 min main session) | Non-REVTeX sample (128/128) and all 20 manual-label papers unchanged |

## 2.5.4 Output and checks

At the end of each session, the three tables are rebuilt from `data/parsed/`: the files are read 500 at a
time, checked, and written to Parquet (zstd compression) through a local temporary file, then copied to
Drive. Before it finishes, `15` checks

- the invariants of every paper (chapter [2.4](deduplication.ipynb)), and the same invariants over the
  tables: unique `element_id`, every `hierarchy` edge inside `elements`, one root per version;
- that the tables have as many rows as the papers' summaries announce;
- that every version of every paper has a row in `m2_parse_status.csv`;

and stops with an error if one of them fails. It then writes the statistics (`m2_stats.json`) and the
benchmark (`m2_benchmark.json`) used in chapters [3](statistics.ipynb) and [4](performance.ipynb), and flushes
and unmounts Google Drive so that every file of the session is saved. The last session of the full run
reported `0 papers with broken invariants, 0 table problems, 0 versions missing from m2_parse_status.csv,
0 papers not parsed`.

`src/16_test_m2_1000_papers.ipynb` runs the same notebook on 1,000 papers in a separate folder, checks the
tables against the statement (columns, types, nulls, the single root of each version), tests resume and the
time limits, and was run on Colab before the full run.
