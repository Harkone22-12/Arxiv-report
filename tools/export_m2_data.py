"""Export the results of the Milestone 2 parser into the small files in `data/` that its chapters are built from.

Usage (from the report repository):

    python tools/export_m2_data.py <project folder> [--example <folder id>] [--out <folder>]

`<project folder>` is the folder `src/15_run_parsing.ipynb` writes to (`MyDrive/arxiv-project` on Colab, or
a local copy of it). Only these files of it are read, and nothing in it is modified:

    logs/m2_stats.json, logs/m2_benchmark.json, logs/m2_benchmark_sessions.jsonl, logs/m2_parse_status.csv
    state/m2/done.jsonl            resume index: one summary per parsed paper
    data/parsed/<example>.json     the paper of the worked example (default: EXAMPLE below)

Copied: the four log files (of m2_parse_status.csv, which every session appends to, only the last row of
each version). Derived here:
    m2_papers.csv     one row per paper  <- state/m2/done.jsonl (the summaries of the final parser version)
    m2_example.json   one paper: its versions, trees with element IDs, elements and BibTeX rows
"""

import csv
import json
import shutil
import sys
from pathlib import Path

COPIED = {
    "logs/m2_stats.json": "m2_stats.json",
    "logs/m2_benchmark.json": "m2_benchmark.json",
    "logs/m2_benchmark_sessions.jsonl": "m2_benchmark_sessions.jsonl",
    "logs/m2_parse_status.csv": "m2_parse_status.csv",
}
EXAMPLE = "2603-21809"   # two versions of about 140 nodes; sections renamed between them, 21 BibTeX rows
PAPER_FIELDS = ["arxiv_id", "versions", "versions_ok", "nodes", "elements", "hierarchy", "bib_before", "bib_after",
                "seconds", "bytes", "carried"]


def read_done_index(path, version):
    """{folder_id: summary} of the papers whose last line in the index has `version` (as 15 reads it)."""
    done = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                summary = json.loads(line)
            except ValueError:
                continue
            if summary.get("parser_version") == version:
                done[summary["folder_id"]] = summary
            else:
                done.pop(summary.get("folder_id"), None)
    return done


def paper_rows(done):
    for folder_id in sorted(done):
        s = done[folder_id]
        yield [s["arxiv_id"], len(s["versions"]), sum(v["status"] == "ok" for v in s["versions"]),
               sum(s["nodes_by_kind"].values()), s["rows"]["elements"], s["rows"]["hierarchy"],
               s["bib_before"], s["rows"]["bibtex"], s["seconds"], s["bytes"], bool(s.get("carried_from"))]


def example(doc, max_chars=400):
    """The parsed.json of one paper, with element contents cut to max_chars."""
    ids, kinds, contents = (doc["elements"][c] for c in ("element_id", "kind", "content"))
    bib = doc["bibtex"]
    return {
        "arxiv_id": doc["arxiv_id"], "folder_id": doc["folder_id"], "parser_version": doc["parser_version"],
        "versions": [{k: v for k, v in r.items() if k != "seconds"} for r in doc["versions"]],
        "trees": doc["trees"],
        "elements": {i: [k, c if len(c) <= max_chars else c[:max_chars] + " …"] for i, k, c in zip(ids, kinds, contents)},
        "hierarchy_rows": len(doc["hierarchy"]["element_id"]),
        "bibtex": [dict(zip(bib, values)) for values in zip(*bib.values())],
    }


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    root = Path(args[0])
    chosen = args[args.index("--example") + 1] if "--example" in args else EXAMPLE
    out = Path(args[args.index("--out") + 1]) if "--out" in args else Path(__file__).resolve().parent.parent / "data"
    out.mkdir(parents=True, exist_ok=True)
    missing = [src for src in [*COPIED, "state/m2/done.jsonl", f"data/parsed/{chosen}.json"] if not (root / src).is_file()]
    if missing:
        raise SystemExit(f"Missing in {root}: {', '.join(missing)}")

    print(f"Export from {root} to {out}")
    for src, name in COPIED.items():
        if name == "m2_parse_status.csv":   # appended by every session: keep the last row of each version
            with open(root / src, encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fields, last = reader.fieldnames, {}
                for row in reader:
                    last[(row["arxiv_id"], row["version"])] = row
            with open(out / name, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(last.values())
            print(f"  {name}: {len(last):,} versions (last row of each)")
            continue
        shutil.copyfile(root / src, out / name)
        print(f"  {name}: copied")
    stats = json.loads((root / "logs/m2_stats.json").read_text(encoding="utf-8"))
    done = read_done_index(root / "state/m2/done.jsonl", stats["parser_version"])
    with open(out / "m2_papers.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(PAPER_FIELDS)
        writer.writerows(paper_rows(done))
    print(f"  m2_papers.csv: {len(done):,} papers of parser {stats['parser_version']}")
    doc = json.loads((root / f"data/parsed/{chosen}.json").read_text(encoding="utf-8"))
    (out / "m2_example.json").write_text(json.dumps(example(doc), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  m2_example.json: {doc['arxiv_id']}, {len(doc['versions'])} versions")


if __name__ == "__main__":
    main()
