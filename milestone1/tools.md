# 2.5 Tools and libraries

*Code: `src/requirements.txt`, `src/00_config.ipynb`*

## 2.5.1 External services

| Service | Endpoint | Used for | Limit we apply |
|---|---|---|---|
| arXiv API | Atom API through the `arxiv` library, `id_list` of up to 100 IDs | entry discovery, metadata of every version | one connection, 3 s between calls |
| arXiv source mirror | `https://export.arxiv.org/src/{id}v{N}` | LaTeX source of every version | one connection, 3 s between request starts |
| Semantic Scholar Graph API | `POST /graph/v1/paper/batch`, 100 papers per request | reference metadata | one connection, one request every `S2_DELAY` seconds, API key |

## 2.5.2 Libraries

| Purpose | Tool | Where |
|---|---|---|
| entry discovery, paper metadata | `arxiv` 4.x (`Client.results(Search(id_list=...))`) | `01_discovery.ipynb` |
| HTTP for sources and references | `requests` (one `Session` per service, streaming, `Range` requests) | `02_download.ipynb`, `03_references.ipynb` |
| unpacking | Python standard library: `tarfile`, `zipfile`, `gzip`, `bz2`, `lzma` | `02_download.ipynb` |
| integrity | `hashlib` (SHA-256 of every kept file in the receipt) | `02_download.ipynb` |
| concurrency | `concurrent.futures.ThreadPoolExecutor`, `threading` (extraction workers, reference thread, monitor thread, locks) | `02`, `03`, `04`, `05` |
| monitoring | `psutil` (resident memory), `time.perf_counter` (wall clock), receipts or a `du`-style walk for disk (`MEASURE_DISK`) | `04_monitor.ipynb`, `05_run_pipeline.ipynb` |
| progress | `tqdm` bars (discovery, papers, current file and MB left) | `01`, `02` |
| analysis and figures | `pandas`, `matplotlib` | `04_monitor.ipynb`, this report |
| notebooks as modules | `%run -i` to load notebooks 00–04 into the pipeline | `05_run_pipeline.ipynb` |

The pinned ranges are in `src/requirements.txt`: `arxiv>=4.0,<5`, `requests>=2.31`, `psutil>=5.9`,
`pandas>=2.0`, `matplotlib>=3.7`, `nbformat>=5.9`, `tqdm>=4.66`, `ipywidgets>=7.7`.

## 2.5.3 Environment

| | |
|---|---|
| **Runtime** | Google Colab, CPU-only (the benchmark environment required by the statement) |
| **Persistent storage** | Google Drive, mounted by `00_config.ipynb` at `MyDrive/arxiv-project` (corpus, state, logs) |
| **Scratch storage** | the runtime's local disk (`/tmp`) for the downloaded archives |
| **Secrets** | `S2_API_KEY` from Colab Secrets or a local `.env` file; never stored in a notebook |
| **Version control** | Git and GitHub; the pipeline notebook clones or updates the repository at the start of every session |
| **Report** | Jupyter Book 2 (MyST), built and deployed to GitHub Pages by a GitHub Actions workflow |

## 2.5.4 Code organisation

The pipeline is a set of notebooks in `src/`, one per responsibility, loaded into a single run:

| Notebook | Content |
|---|---|
| `00_config.ipynb` | assigned ranges, paths, rate limits, ID helpers, logging |
| `01_discovery.ipynb` | entry discovery and paper metadata (arXiv API) |
| `02_download.ipynb` | source download, extraction of `.tex`/`.bib`, resume; 46 offline tests |
| `03_references.ipynb` | reference metadata (Semantic Scholar batch API) |
| `04_monitor.ipynb` | RAM monitor, statistics and chart helpers |
| `05_run_pipeline.ipynb` | the end-to-end run: discovery, then sources and references in parallel, then the benchmark |
| `06_test_100_versions.ipynb` | the real pipeline on the first 100 source versions, with checks |
| `07_run_references.ipynb` | the reference stage alone, on a second runtime |
| `09_repair_missing_sources.ipynb` | downloads again the versions whose files did not reach Drive |

Notebooks 01–04 only define functions and their tests (`RUN_TEST = True` when opened on their own); none of
them starts the crawl. How to set up the environment and run the code is in the `README.md` of the
[code repository](https://github.com/thinhelzan842/intro-ds-arxiv-project).
