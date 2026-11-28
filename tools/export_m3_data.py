"""Export the Milestone 3 logs and label summaries into the small files in `data/` that its chapters read.

Usage (from the report repository):

    python tools/export_m3_data.py <project folder> [--out <folder>]

`<project folder>` is the folder the Milestone 3 notebooks write to (`MyDrive/arxiv-project` on Colab, or a
local copy such as `report_inputs/`). Only these files are read, and nothing in `<project folder>` is modified:

    logs/m3_data_summary.json       dataset sizes, eligible counts, pools, per-member breakdown (20_m3_data)
    logs/m3_labels.json             manual and automatic label counts, tuning, auto vs manual (21_labeling)
    logs/m3_feature_report.csv      per-feature coverage, means, AUC and single-feature MRR@5 (22_features)
    logs/m3_cleaning_report.csv     field completeness after cleaning, by bib_source (22_features)
    logs/m3_metrics.json            chosen model, MRR@5, NIL curve, ablation, LOPO (23_model)
    logs/m3_model_selection.csv     5-fold grouped CV and valid MRR@5 of all 14 configs (23_model)
    logs/m3_run.json                pipeline run history and per-step timings (25_run_m3)
    logs/m3_requirements.json       23 statement and Q&A checks (24_analysis)
    logs/hf_export.json             exported Parquet rows and shards per member and table (26_export_hf)
    labels/split.json               train / valid / test publication IDs (21_labeling)
    labels/selection.csv            the 20 manually labelled publications with bib_source (21_labeling)
"""

import shutil
import sys
from pathlib import Path

COPIED = {
    "logs/m3_data_summary.json": "m3_data_summary.json",
    "logs/m3_labels.json": "m3_labels.json",
    "logs/m3_feature_report.csv": "m3_feature_report.csv",
    "logs/m3_cleaning_report.csv": "m3_cleaning_report.csv",
    "logs/m3_metrics.json": "m3_metrics.json",
    "logs/m3_model_selection.csv": "m3_model_selection.csv",
    "logs/m3_run.json": "m3_run.json",
    "logs/m3_requirements.json": "m3_requirements.json",
    "logs/hf_export.json": "m3_hf_export.json",
    "labels/split.json": "m3_split.json",
    "labels/selection.csv": "m3_selection.csv",
}


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    root = Path(args[0])
    out = Path(args[args.index("--out") + 1]) if "--out" in args else Path(__file__).resolve().parent.parent / "data"
    out.mkdir(parents=True, exist_ok=True)
    missing = [src for src in COPIED if not (root / src).is_file()]
    if missing:
        raise SystemExit(f"Missing in {root}: {', '.join(missing)}")

    print(f"Export Milestone 3 data from {root} to {out}")
    for src, name in COPIED.items():
        shutil.copyfile(root / src, out / name)
        print(f"  {name}: copied")


if __name__ == "__main__":
    main()
