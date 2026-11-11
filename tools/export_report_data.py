"""Export the crawl's logs and state into the small files in `data/` that the report is built from.

Usage (from the report repository):

    python tools/export_report_data.py <crawl folder>

`<crawl folder>` is the project folder the pipeline writes to (`MyDrive/arxiv-project` on Colab, or a
local copy of it) and must contain `logs/`, `state/` and `data/raw/`. Nothing in it is modified.

Copied as they are (written by `src/05_run_pipeline.ipynb`):
    benchmark.json, benchmark_sessions.jsonl, performance.json, papers.csv, run_history.jsonl

Derived here, one row per item, so that the report can break the numbers down further:
    metadata.csv         one row per assigned ID    <- state/discovery_manifest.json
    versions.csv         one row per source version <- state/download/receipts.jsonl (last receipt wins)
    download_events.csv  one row per failed or refused request <- errors.jsonl, throttles.jsonl
    references_log.csv   one row per logged reference request outcome <- logs/references.csv
    reference_fields.json  field completeness over every saved reference <- data/raw/*/references.json
    corpus_check.json    `ok` receipts whose vN/ folder is missing in this copy of data/raw
"""

import csv
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

COPIED = {
    "logs/benchmark.json": "benchmark.json",
    "logs/benchmark_sessions.jsonl": "benchmark_sessions.jsonl",
    "logs/performance.json": "performance.json",
    "logs/papers.csv": "papers.csv",
    "state/download/run_history.jsonl": "run_history.jsonl",
}
OLD_STYLE_ID = re.compile(r"^[a-z\-]+(?:\.[A-Z]{2})?/\d{7}$")


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)
    print(f"  {path.name}: {len(rows):,} rows")


def folder_id(arxiv_id):
    """2609.32834 -> 2609-32834, the paper folder name used by the crawl (00_config.to_folder_id)."""
    return arxiv_id.replace(".", "-").replace("/", "_")


def kind_of(event):
    """`error_kind` of an errors.jsonl line; lines written before the label existed only have the
    exception text, which is mapped to the label 02_download.error_kind() gives the same exception."""
    if event.get("error_kind"):
        return event["error_kind"]
    text = event.get("error", "")
    status = re.search(r"HTTP (\d{3})", text)
    if status:
        code = int(status.group(1))
        if code in (404, 410):
            return "NOT_FOUND"
        if code == 429:
            return "HTTP_429"
        return "HTTP_5XX" if code >= 500 else f"HTTP_{code}"
    if text.startswith(("ChunkedEncodingError", "ConnectionError", "ReadTimeout", "ConnectTimeout")):
        return "TRANSFER_CUT"
    if text.startswith(("BadZipFile", "ReadError", "EOFError", "BadGzipFile", "LZMAError")):
        return "CORRUPT_ARCHIVE"
    if text.startswith("ValueError"):
        return "MARKUP_RESPONSE" if "HTML/JSON" in text else "REJECTED_ARCHIVE"
    return text.split("(")[0] or "UNKNOWN"


def export_metadata(crawl, out):
    manifest = json.loads((crawl / "state/discovery_manifest.json").read_text(encoding="utf-8"))
    rows = []
    for paper in manifest["papers"]:
        info = paper.get("version_info") or [{}]
        latest = info[-1]
        categories = latest.get("categories") or []
        rows.append([
            paper["id"], paper["status"], paper["versions"],
            categories[0] if categories else "", len(categories),
            (paper.get("submitted") or "")[:10],
            (paper["revised"][-1][:10] if paper.get("revised") else ""),
            int(bool(paper.get("venue"))), int(bool(latest.get("doi"))), len(paper.get("authors") or []),
        ])
    write_csv(out / "metadata.csv",
              ["id", "status", "versions", "primary_category", "n_categories", "submitted", "last_revised",
               "has_venue", "has_doi", "n_authors"], rows)
    return manifest


def export_versions(crawl, out):
    receipts = {}
    for receipt in read_jsonl(crawl / "state/download/receipts.jsonl"):
        receipts[(receipt["arxiv_id"], receipt["version"])] = receipt
    rows = []
    for (arxiv_id, version), receipt in sorted(receipts.items()):
        names = [name.lower() for name in receipt.get("files", {})]
        rows.append([
            arxiv_id, version, receipt["status"], receipt["downloaded_bytes"], receipt["before_bytes"],
            receipt["after_bytes"], sum(n.endswith(".tex") for n in names), sum(n.endswith(".bib") for n in names),
            receipt.get("elapsed_seconds", ""), receipt["finished_at"],
        ])
    write_csv(out / "versions.csv",
              ["id", "version", "status", "downloaded_bytes", "before_bytes", "after_bytes", "n_tex", "n_bib",
               "seconds", "finished_at"], rows)
    return receipts


def export_events(crawl, out):
    rows = []
    for log in ("errors", "throttles"):
        for event in read_jsonl(crawl / f"state/download/{log}.jsonl"):
            rows.append([log, event["arxiv_id"], event["version"], kind_of(event),
                         event.get("status") or "", event["at"]])
    write_csv(out / "download_events.csv", ["log", "id", "version", "error_kind", "http_status", "at"], rows)


def export_reference_log(crawl, out):
    with open(crawl / "logs/references.csv", encoding="utf-8", newline="") as handle:
        rows = [[r["id"], r["status"], r["n_refs"], r["n_arxiv_refs"], r["n_dropped"], r["attempts"],
                 r["seconds"], r["logged_at"]] for r in csv.DictReader(handle)]
    write_csv(out / "references_log.csv",
              ["id", "status", "n_refs", "n_arxiv_refs", "n_dropped", "attempts", "seconds", "logged_at"], rows)


def export_reference_fields(crawl, out, manifest):
    fields = Counter()
    date_source = Counter()
    status = Counter()
    total = dropped = 0
    for paper in manifest["papers"]:
        path = crawl / "data/raw" / folder_id(paper["id"]) / "references.json"
        if not path.is_file():
            status["missing_file"] += 1
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        status[doc.get("status") or "unknown"] += 1
        dropped += doc.get("n_dropped") or 0
        for ref in doc.get("references") or []:
            total += 1
            fields["ref_title"] += bool(ref.get("title"))
            fields["ref_authors"] += bool(ref.get("authors"))
            fields["ref_submission_date"] += bool(ref.get("submission_date"))
            fields["ref_s2_id"] += bool(ref.get("s2_id"))
            fields["ref_arxiv_id"] += bool(ref.get("arxiv_id"))
            fields["arxiv_id_old_style"] += bool(ref.get("arxiv_id") and OLD_STYLE_ID.match(ref["arxiv_id"]))
            fields["doi"] += bool((ref.get("external_ids") or {}).get("DOI"))
            fields["venue"] += bool(ref.get("venue"))
            date_source[ref.get("date_source") or "none"] += 1
    summary = {"papers": len(manifest["papers"]), "paper_status": dict(status), "references_total": total,
               "references_dropped": dropped, "fields_present": dict(fields), "date_source": dict(date_source)}
    (out / "reference_fields.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"  reference_fields.json: {total:,} references in {sum(status.values()):,} papers")


def export_corpus_check(crawl, out, receipts):
    ok = sorted(key for key, receipt in receipts.items() if receipt["status"] == "ok")
    missing = [key for key in ok if not (crawl / "data/raw" / folder_id(key[0]) / f"v{key[1]}").is_dir()]
    check = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok_receipts": len(ok),
        "ok_receipts_without_folder": len(missing),
        "papers_affected": len({key[0] for key in missing}),
        "first_id": missing[0][0] if missing else None,
        "last_id": missing[-1][0] if missing else None,
    }
    (out / "corpus_check.json").write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
    print(f"  corpus_check.json: {len(missing):,} of {len(ok):,} ok receipts have no vN/ folder")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    crawl = Path(sys.argv[1])
    out = Path(__file__).resolve().parent.parent / "data"
    out.mkdir(exist_ok=True)
    for source, name in COPIED.items():
        shutil.copyfile(crawl / source, out / name)
        print(f"  {name}: copied")
    manifest = export_metadata(crawl, out)
    receipts = export_versions(crawl, out)
    export_events(crawl, out)
    export_reference_log(crawl, out)
    export_reference_fields(crawl, out, manifest)
    export_corpus_check(crawl, out, receipts)


if __name__ == "__main__":
    main()
