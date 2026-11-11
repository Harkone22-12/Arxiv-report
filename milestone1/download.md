# 2.2 Source download

*Author: Võ Nguyễn Vân Anh · code: `src/02_download.ipynb`*

Every version of every discovered paper is downloaded from the arXiv source mirror. This section covers the
network side: the requests, what happens when arXiv refuses or cuts one, how the work is organised around
the request interval, and how the crawl resumes. What is done with a downloaded archive is the subject of
[2.3](extraction.md). The code is `SourceClient` and `download_sources` in `src/02_download.ipynb`, covered
by 46 offline tests in the same notebook.

## 2.2.1 Requests

- **One request per version:** `https://export.arxiv.org/src/{arxiv_id}v{N}`, for `N` from 1 to the number
  of versions found by discovery. Automated downloads never go to `arxiv.org`.
- **One connection, at least 3 s between request starts** (`ARXIV_DELAY`). Retries go through the same gate,
  so they never break the pacing. The `User-Agent` names the project.
- The archive is **streamed in 1 MB blocks to the runtime's local disk** (`/tmp`), not to Google Drive and
  not into memory, so a large archive costs neither RAM nor slow Drive writes.

## 2.2.2 When a request does not succeed

The downloader separates failures of the *version* from refusals by the *server*, because they call for
different reactions:

| What happens | Meaning | Reaction |
|---|---|---|
| HTTP 404 / 410, another 4xx | arXiv has no source for this version | not retried in this run; marked failed and asked again in the next run |
| HTTP 429, 5xx, timeout, connection lost before any byte arrived | the server refused or was busy; nothing is wrong with the version | **not retried at once**: the crawl moves on and puts the version back at the end of the same run (up to 3 times, then the next run) |
| transfer cut midway (`IncompleteRead`) | part of the archive has arrived | retried in place, asking **only for the missing bytes** |
| empty body, or an HTML/JSON error page served with HTTP 200 | not a source | rejected; asked again in the next run |

**Refusals.** HTTP 429 is arXiv's rate limit (`Rate exceeded.`), counted per IP over a short window, and
Colab IPs are shared with other users. Waiting on the refused version would stall the whole crawl, while the
next request often succeeds, so the refused version simply goes to the back of the queue and the spacing
stays at 3 s. Only a `Retry-After` header sent by arXiv is honoured as an extra wait. If 50 requests in a
row are refused, the run stops with a message to switch runtime: that IP is rate-limited and continuing
would only send requests that will be refused.

**Cut transfers.** arXiv often cuts long transfers. When part of the file has arrived and the server sent an
`ETag`, the retry uses an HTTP `Range` request for the missing bytes, guarded by `If-Range` on the `ETag`,
so a file that changed in the meantime starts over instead of being stitched together from two versions.
Moving on would throw the received bytes away, which for a large archive is most of the cost. If the
transfer still fails after its last attempt (4), the next request waits a cooldown of 10 s, doubled after
each such failure up to 60 s and reset by the next successful download: a period of throttling then costs a
few pauses instead of dozens of failed versions to redo.

**Failures that would hit every version.** The run stops early, with the reason, instead of failing and
requesting every remaining version: at once on a storage error (Google Drive or the local disk full, Drive
unmounted), and after 20 failed versions in a row. An HTTP 404/410 does not count towards that limit,
because the versions without a source are retried one after another at the end of a run.

## 2.2.3 Pipelined downloads

The 3 s interval is the floor for any compliant scraper, so the download is organised to add nothing to it:

```text
main thread     fetch v1 ─3 s─ fetch v2 ─3 s─ fetch v3 ─3 s─ ...      (only network)
worker 1               └ unpack, copy .tex/.bib to Drive, receipt
worker 2                              └ unpack, copy .tex/.bib to Drive, receipt
```

Unpacking and the slow writes to Google Drive run in two worker threads (`DOWNLOAD_WORKERS`) while the main
thread waits for the next request slot. At most `2 × DOWNLOAD_WORKERS` fetched archives wait for a worker,
which bounds the space used in `/tmp`. Each version therefore costs about `max(3 s, transfer time)` instead
of transfer + unpacking + Drive writes. [4.5](performance.ipynb) checks this against the measured times.

## 2.2.4 Resuming after a disconnect

A free Colab session lasts at most about 12 hours and can end at any moment, and the full crawl needs many
sessions. The downloader is built so that stopping it, at any point, loses at most the version in progress.

- **Receipts.** Every finished version gets a receipt (sizes and SHA-256 of the kept files, bytes
  downloaded, time) in `state/download/receipts/<id>/vN.json`, also appended to the index
  `state/download/receipts.jsonl`.
- **Atomic versions.** A version is written to a staging folder and renamed into place only when complete,
  so an interrupted version is never mistaken for a finished one. Staging folders left by a killed run are
  removed at start-up.
- **Fast start-up.** The index is read once and trusted (`DOWNLOAD_VERIFY = "receipt"`), which takes
  seconds. Checking the saved files themselves costs about 17 Drive calls per version, hours for the whole
  corpus, so the modes `"size"` and `"sha256"` are meant for an occasional full check.
- **Ordering.** Every request is logged in `attempts.jsonl` before it is sent, so each run starts with the
  versions never requested; versions requested before but not finished come after them, the least-tried
  first. A new session therefore does not open with the same failures as the last one.
- **One runtime at a time.** A lock file with a heartbeat (`pipeline.lock`, `download.lock`) refuses a
  second runtime working on the same Drive folder and is taken over once the other runtime has been gone
  for 3 minutes.
- **Before and after.** Before the first request the run checks that Drive and `/tmp` have room for the
  rest of the crawl and tests the runtime's IP with a few requests; at the end of a session the pipeline
  flushes Google Drive, whose writes are asynchronous.

:::{warning}
Trusting the receipts has a cost that we met in practice. Google Drive syncs in the background, and a
session that Colab kills can leave receipts that are synced while the files they describe are not. A check
after the crawl found such versions; they are reported in [3.1](statistics.ipynb) and
`src/09_repair_missing_sources.ipynb` downloads them again. The `"size"` verification mode would have caught
them at the next start-up, at the price of a much slower start.
:::

## 2.2.5 Progress and logs

Two progress bars show the papers done out of every discovered paper (with versions, MB downloaded and the
remaining time) and the file being downloaded. The downloader writes `progress.json`, `run_summary.json`,
`run_history.jsonl` and `papers.csv` (one row per paper: versions, sizes before and after, status, time) to
`state/download/`.

Two more files record what went wrong, one JSON line per event: `errors.jsonl` for a version that
**failed**, and `throttles.jsonl` for a request arXiv **refused** or did not answer. Every line carries the
`arxiv_id`, the `version`, the HTTP `status`, the time and an `error_kind` label set by `error_kind()`:

| `error_kind` | Meaning | File |
|---|---|---|
| `HTTP_429`, `HTTP_5XX` | arXiv rate-limited the IP or was busy | `throttles.jsonl` |
| `TIMEOUT`, `NO_CONNECTION` | no answer, or the connection was lost before any byte arrived | `throttles.jsonl` |
| `NOT_FOUND` | HTTP 404/410: arXiv has no source for this version | `errors.jsonl` |
| `HTTP_<code>` | another HTTP 4xx (e.g. `HTTP_403`) | `errors.jsonl` |
| `TRANSFER_CUT` | a transfer cut midway that still failed after its `Range` retries | `errors.jsonl` |
| `EMPTY_RESPONSE`, `MARKUP_RESPONSE` | an empty body, or an HTML/JSON error page served with HTTP 200 | `errors.jsonl` |
| `CORRUPT_ARCHIVE` | an archive that cannot be unpacked (broken TAR, ZIP, gzip or xz data) | `errors.jsonl` |
| `REJECTED_ARCHIVE` | an unsafe path, a link or special file, or a text file over 128 MB | `errors.jsonl` |
| `STORAGE`, `IO_ERROR` | Google Drive or the local disk full or unmounted, another file-system error | `errors.jsonl` |

The handling of refusals changed during the crawl, and lines written before the label existed have only the
exception text; the failure breakdown in [3.1](statistics.ipynb) labels those from that text.
