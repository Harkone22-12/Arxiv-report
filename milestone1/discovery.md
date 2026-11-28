# 2.1 Entry discovery

*Author: La Anh Hào · code: `src/00_config.ipynb`, `src/01_discovery.ipynb`*

Discovery answers two questions for each of the 20,000 assigned IDs: **does the paper exist**, and **how
many versions does it have**. It also collects the metadata of every version. The functions are
`fetch_metadata`, `resolve_discovery_batches` and `discover_all` in `src/01_discovery.ipynb`; the assigned
ranges are expanded by `all_assigned_ids()` in `src/00_config.ipynb`.

## 2.1.1 Choice of the method

The statement offers three ways to resolve entries: the arXiv API, OAI-PMH and the Kaggle metadata
snapshot. We use the **arXiv API** through the `arxiv` library 4.x
(`Client.results(Search(id_list=...))`), for three reasons:

- it is addressed **by ID**, which is exactly what we are given, and accepts many IDs per call;
- asked for a *versioned* ID it returns the metadata of that version, so the whole version history can be
  rebuilt from the same service;
- it is live, whereas a snapshot would miss the newest range, which was submitted only weeks before the
  crawl.

OAI-PMH is designed for harvesting whole sets by date and the Kaggle file is a bulk snapshot; both are tools
for repository-scale work, which is outside this milestone.

## 2.1.2 Two passes over the arXiv API

1. **Latest versions.** The API is queried with up to **100 plain IDs per call** (`id_list`). For a plain
   ID arXiv returns the *latest* version, e.g. `2609.32867v2`, so the suffix gives the number of versions.
   IDs that do not exist are simply missing from the answer.
2. **Older versions.** The versioned IDs `v1 … v(n-1)` are queried, again 100 per call. For a versioned ID
   the API returns that version's own title, authors, abstract and date, which gives the revision dates and
   the per-version metadata.

```text
pass 1   id_list = [2609.32834, 2609.32835, …, 2609.32933]           100 plain IDs per call
           → 2609.32834v1, 2609.32835v1, …, 2609.32867v2, …           latest version of each paper
pass 2   id_list = [2609.32867v1, …]                                  100 versioned IDs per call
           → title, authors, abstract, date of each older version
```

With the mandatory 3 s between calls, batching is what keeps discovery short: the 20,000 IDs need about 200
calls in the first pass instead of 20,000. The measured discovery time is reported in
[4.2 Running time](performance.ipynb).

## 2.1.3 What is saved

Each paper is saved as `data/raw/<id>/metadata.json`:

| Field | Content |
|---|---|
| `id`, `versions` | base identifier and number of versions |
| `title`, `authors`, `venue` | from the latest version; `venue` is the journal reference or `null` |
| `submitted`, `revised` | date of version 1 and dates of the later versions |
| `version_info` | one record per version: title, authors, abstract, date, `journal_ref`, DOI, comment, categories |
| `status` | `ok` (all versions found), `partial` (an older version could not be fetched), `not_found` (the ID does not exist on arXiv) or `error` (the request kept failing) |

Keeping the metadata **per version** matters for the next milestones: titles, author lists and abstracts
change between versions, and the parser will work on each version separately. `papers_rows()` turns these
files into the `papers` table of the statement ([1.5](overview.md#tables)).

## 2.1.4 Errors and rate limiting

- One connection and at least **3 s** between calls (`ARXIV_DELAY`), with a descriptive `User-Agent`.
- **HTTP 429** (too many requests): wait `ARXIV_BACKOFF` = 30 s, doubling each time, up to `ARXIV_RETRIES`
  = 3 times, then mark the batch as failed. Splitting the batch would only send more requests to a service
  that is asking for fewer.
- **Other failures** (e.g. HTTP 500): split the batch in half and retry each half, down to single IDs, so
  one bad ID cannot block the other 99; an ID that still fails gets status `error`.
- Old-style IDs (`hep-th/9711200`) are supported by the ID helpers and tested, although all assigned ranges
  are new-style.

## 2.1.5 Checkpoints, crawl dates and resume

`resolve_discovery_batches` saves every finished batch of 100 IDs to `state/discovery_batches/` **before**
the next API call, and `discover_all` merges them into `state/discovery_manifest.json`. A batch that still
fails after the retries stops the run *before* any download starts; running the pipeline again reuses the
saved batches and only queries the IDs that are missing or ended in `error`. The API time of every run is
added up in the manifest (`discovery_seconds`), which is the **entry discovery time** of the benchmark.
In the later sessions of the crawl, discovery only checks that the manifest is complete, which takes a few
seconds.

**Crawl dates and version snapshot.** Because arXiv continuously receives new revisions (`v2`, `v3`, …), the
corpus reflects the version list captured by the discovery manifest:

- The latest revision date recorded across all 20,000 papers in `metadata.csv` is **2026-10-30** (all 20,000
  assigned IDs existed on arXiv, totalling 27,035 versions).
- The main Colab crawl ran from **2026-11-02 to 2026-11-06**, followed by a final retry session on
  **2026-11-09** and a corpus integrity check on **2026-11-11** (followed by the repair run of
  `src/09_repair_missing_sources.ipynb` before Milestone 2).
- Any new arXiv version uploaded after the discovery snapshot is intentionally excluded so that all three
  milestones operate on a fixed, reproducible set of 27,035 versions.
- *Team progress checkpoints (working notes):* during development, the group saved intermediate snapshots on
  **20 Oct**, **26 Oct**, **2 Nov** and **6 Nov 2026**; a spot check on **9 Nov 2026** against an earlier
  25 Oct snapshot of one member's 5,000-ID range observed 24 newly uploaded revisions, illustrating why the
  discovery timestamp must be frozen and documented in the report.
