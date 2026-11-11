# 2.4 Reference metadata

*Author: Lưu Minh Quân · code: `src/03_references.ipynb`*

For every assigned paper we collect the list of works it cites from the
[Semantic Scholar Graph API](https://api.semanticscholar.org/api-docs/graph). These references are the
matching pool of Milestone 3: each BibTeX entry parsed in Milestone 2 will be matched against the
arXiv-keyed references collected here.

## 2.4.1 One request per 100 papers

The client uses the batch endpoint `POST /graph/v1/paper/batch`. It takes a list of IDs written as
`arXiv:{id}` and returns the papers in the same order, with `null` for a paper Semantic Scholar does not
index. For each paper we ask for its `paperId`, `title`, `externalIds` and the flat reference fields
`references.title`, `references.authors`, `references.year`, `references.publicationDate`,
`references.venue` and `references.externalIds`. Nested names such as `references.authors.name` are rejected
by the API, so the fields are requested flat. Every reference also comes with its `paperId`, the Semantic
Scholar ID. Semantic Scholar does not tell arXiv versions apart, so the list is saved once per paper and
applies to all its versions.

**Why batches.** Our first version sent one request per paper (`GET /graph/v1/paper/arXiv:{id}`). On a test
run of 90 papers it took 12.5 s per paper: Semantic Scholar refused about half of the requests with HTTP 429
even with an API key, each paper waited out its own retries (2 s, 4 s, 8 s, …), and the 5 slowest papers
took half of the total time. At that speed the 20,000 papers would need about 60 hours, longer than the
source downloads. The batch endpoint returns the same reference lists (checked on `1706.03762`,
`hep-th/9711200` and `2303.18223`, a survey with 462 references), and a 429 now delays 100 papers by a few
seconds instead of one paper.

| | One request per paper | Batch of 100 papers |
|---|---:|---:|
| Requests for 20,000 papers | 20,000 | about 200 |
| Measured time per paper (test runs, 2 Nov 2026) | 12.5 s (90 papers) | 0.11 s (1,000 papers) |
| Effect of one HTTP 429 | one paper waits | 100 papers wait a few seconds |

## 2.4.2 Two traps of the batch endpoint

Both were found by testing the endpoint, and both fail silently:

- **Versioned IDs.** An ID with a version suffix (`2609.32867v1`) comes back as `null`, as if the paper did
  not exist. Versions are always stripped before the request.
- **A cap of 9,999 references per answer.** A test batch of 500 papers of our range returned exactly 9,999
  references, and 197 of the papers came back with an empty list but no error; the same papers asked 100 at
  a time had 16,974 references. We therefore send 100 papers per request, and if an answer still reaches
  9,999 references (`S2_BATCH_MAX_REFS`), the batch is split in two and asked again.

## 2.4.3 What is kept

**Every reference is kept, and the arXiv ones are flagged.** As the statement asks, all references are
stored locally, not only those with an arXiv ID. A reference whose `externalIds` has an `ArXiv` key gets:

- `arxiv_id`: the ID as given, without any version suffix. Old-style IDs such as `hep-th/9901001` are kept
  in their original form, because that is their real identifier.
- `arxiv_folder_id`: the folder name used across our corpus (`2310.12345` → `2310-12345`,
  `hep-th/9901001` → `hep-th_9901001`), so a reference can be joined directly with a paper folder.

An `ArXiv` value that is not a valid new- or old-style ID is not counted as an arXiv reference. It is still
visible in `external_ids`, which also keeps `DOI`, `CorpusId`, `DBLP`, etc. for Milestone 3.

**Dates.** `submission_date` is the `publicationDate` of the reference; if that is missing, its `year` is
used. The `date_source` field records which one was used, and the completeness of each field is measured in
[3.3](statistics.ipynb).

**Output.** Each paper folder gets a `references.json`:

```json
{
  "id": "2609.32834", "status": "ok", "s2_id": "7a1dd005...", "s2_title": "...",
  "n_refs": 28, "n_arxiv_refs": 9, "n_dropped": 0, "error": null,
  "references": [
    {"s2_id": "50098b03...", "title": "On the CGGRT Criterion ...",
     "authors": ["Swastik Kopparty", "Shubhangi Saraf"],
     "submission_date": "2026-07-17", "date_source": "publicationDate", "year": 2026,
     "venue": "arXiv.org", "arxiv_id": "2607.15554", "arxiv_folder_id": "2607-15554",
     "external_ids": {"ArXiv": "2607.15554", "DBLP": "..."}}
  ],
  "fetched_at": "2026-10-28T14:22:08+00:00"
}
```

The file is written even when Semantic Scholar does not know the paper (empty list, `status: "not_found"`),
so every paper folder is complete. A failed request never overwrites a file that an earlier run saved
successfully. Entries with neither a Semantic Scholar ID nor a title carry no information; they are dropped
and counted in `n_dropped`.

`references_rows()` turns the saved files into the `references` table of the statement
(`arxiv_id, ref_arxiv_id, ref_title, ref_authors, ref_submission_date, ref_s2_id`), keeping only the
arXiv-keyed references.

## 2.4.4 Rate limits and error handling

| Situation | Handling |
|---|---|
| Rate limit | one shared limiter for all threads: one request every `S2_DELAY` seconds with an API key, and never faster than one every 3 s without one (to stay under 100 requests per 5 minutes) |
| HTTP 429, 5xx, timeout | retry up to 8 times (`S2_RETRIES`), waiting 2 s, 4 s, 8 s, … up to 60 s (or the server's `Retry-After`), plus up to 1 s of random jitter |
| Paper not indexed | `null` in the batch answer, `status: "not_found"`; common for very recent papers, which Semantic Scholar indexes with some days of delay |
| Batch answer reaches 9,999 references | split the batch in two and ask again, until every answer is below the cap |
| HTTP 400 / 401 / 403 | not retried; the error is logged, and 401/403 adds a hint to check `S2_API_KEY` |
| Batch still failing after 8 attempts | its papers get `status: "error"`; the next run asks for them again |

The API key is read from the `S2_API_KEY` environment variable or from Colab Secrets (set up in
`00_config.ipynb`). It is never written in a notebook.

Even with the key, a large share of requests is refused with HTTP 429. A separate check sent 10 requests at
each spacing of 1 s, 1.5 s and 2 s, plus 8 requests at 3 s: between 40 % and 80 % of them were refused at
every spacing, so slowing down does not remove the refusals. Fewer, larger requests are what reduces the
waiting time, which is the reason for the batches.

## 2.4.5 Log and resume

Every paper appends a row to `logs/references.csv` with `id, status, s2_id, n_refs, n_arxiv_refs,
n_dropped, attempts, seconds, error`. For a batch, `attempts` counts the requests of the whole batch and
`seconds` is its time divided evenly among its papers. `pending_references()` reads this log once to skip
the papers that are already `ok` or `not_found`, so after an interruption only the missing and failed papers
are fetched again, without one Drive read per paper.

## 2.4.6 Running alongside the downloads

The arXiv limit and the Semantic Scholar limit are separate, so `crawl_references(ids)` runs on one
background thread while the main thread downloads the sources from arXiv. Each service still sees one
connection at its own rate. With batches the references finish long before the downloads, so they do not
add to the total running time. `src/07_run_references.ipynb` can also run the reference stage alone on a
second Colab runtime and export the result as one archive.

## 2.4.7 Limitations

- References are per paper, not per version (Semantic Scholar does not distinguish versions).
- Semantic Scholar indexes new uploads with some delay, so the newest papers may be `not_found` or have an
  empty list at first; running the reference stage again later fills them in.
- Some publishers hide reference lists from Semantic Scholar; those papers are `ok` with few or no
  references.
- A part of the references is returned without a Semantic Scholar ID and without authors, as an unlinked
  citation string; these are kept for their title but cannot be matched by identifier.
