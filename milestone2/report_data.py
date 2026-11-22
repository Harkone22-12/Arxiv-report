"""Load the parsing results that the Milestone 2 chapters are built from, plus the shared table and chart helpers.

The files in `data/` are written by `tools/export_m2_data.py` from the logs and the resume index of
`src/15_run_parsing.ipynb` (see the README). Every table and figure of the Milestone 2 chapters is computed
from them when the book is built. Set REPORT_DATA_DIR to read them from another folder.
"""

import json
import os
from pathlib import Path

import pandas as pd
from IPython.display import Markdown, display

DATA_DIR = Path(os.environ.get("REPORT_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
REQUIRED = ("m2_stats.json", "m2_benchmark.json", "m2_benchmark_sessions.jsonl", "m2_parse_status.csv",
            "m2_papers.csv", "m2_example.json")
MB = 1024 * 1024
GB = 1024 * MB
STATUSES = ("ok", "empty_source", "no_root", "error")

# The kinds of tree node (13_dedup_export), from the root to the leaves.
KINDS = ("document", "chapter", "section", "subsection", "subsubsection", "paragraph", "abstract", "itemize",
         "item", "sentence", "formula", "figure")
LEAVES = ("sentence", "formula", "figure")

# The four ID ranges assigned to the group (00_config.ID_RANGES), 5,000 IDs each, both ends inclusive.
RANGES = {
    "R1": ("2609.32834", "2609.37833"),
    "R2": ("2605.17338", "2605.22337"),
    "R3": ("2605.07338", "2605.12337"),
    "R4": ("2603.20580", "2603.25579"),
}

# Chart colours: the palette of the Milestone 1 chapters, one fixed categorical order, never cycled.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA]
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def check():
    """Stop the build with a clear message instead of publishing figures of missing data."""
    missing = [name for name in REQUIRED if not (DATA_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing in {DATA_DIR}: {', '.join(missing)}. Run tools/export_m2_data.py on the parsing logs "
            "(see README.md).")


def style():
    """Matplotlib defaults shared by every figure: light surface, hairline grid, no top/right spines."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 160, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.labelcolor": "#52514e", "axes.titlecolor": INK,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelsize": 9.5,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": "#52514e", "ytick.labelcolor": "#52514e",
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.frameon": False, "legend.fontsize": 9,
        "font.size": 9.5, "lines.linewidth": 2,
    })


def md(text):
    """Show generated text as Markdown (numbers are filled in at build time)."""
    display(Markdown(text))


def table(frame, caption, formats=None, index=False):
    """Show a DataFrame as a numbered table: caption above, thousands separators, optional formats."""
    md(f"*{caption}*")
    styler = frame.style.format(formats or {}, thousands=",", na_rep="–")
    display(styler if index else styler.hide(axis="index"))


def figure_caption(caption):
    md(f"*{caption}*")


def hm(seconds):
    """A duration as '2 h 47 min'."""
    return f"{int(seconds // 3600)} h {int(seconds % 3600 // 60):02d} min"


def pct(part, whole, digits=2):
    return f"{100 * part / whole:.{digits}f}%" if whole else "–"


def range_of(arxiv_id):
    """R1..R4 for an assigned ID."""
    for name, (first, last) in RANGES.items():
        if first <= arxiv_id <= last:
            return name
    return "other"


def _json(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _jsonl(name):
    return [json.loads(line) for line in (DATA_DIR / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def stats():
    """logs/m2_stats.json: status of every version, coverage, elements and entries before/after dedup."""
    return _json("m2_stats.json")


def benchmark():
    """logs/m2_benchmark.json: time, RAM (with its time series) and output size over every session."""
    return _json("m2_benchmark.json")


def sessions():
    """logs/m2_benchmark_sessions.jsonl: one row per Colab session of 15_run_parsing."""
    frame = pd.DataFrame(_jsonl("m2_benchmark_sessions.jsonl"))
    for column in ("start", "end"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame.sort_values("start").reset_index(drop=True)


def versions():
    """logs/m2_parse_status.csv: one row per version (status, source of the references, nodes, seconds).

    15 appends a row each time it parses a paper, so a paper parsed again by a newer parser has several rows
    per version: the last one is the current one, as in 15 itself."""
    frame = pd.read_csv(DATA_DIR / "m2_parse_status.csv", dtype={"arxiv_id": str, "error": str},
                        keep_default_na=False)
    frame = frame.drop_duplicates(["arxiv_id", "version"], keep="last").reset_index(drop=True)
    for column in ("version", "n_nodes"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
    frame["seconds"] = pd.to_numeric(frame["seconds"], errors="coerce")
    frame["range"] = frame["arxiv_id"].map(range_of)
    return frame


def papers():
    """One row per paper, from the resume index of 15 (state/m2/done.jsonl): versions, nodes before and rows
    after dedup, BibTeX entries before and after, seconds in the worker."""
    frame = pd.read_csv(DATA_DIR / "m2_papers.csv", dtype={"arxiv_id": str})
    frame["range"] = frame["arxiv_id"].map(range_of)
    return frame


def example():
    """One parsed paper (data/parsed/<id>.json, shortened by the export script) for the worked example."""
    return _json("m2_example.json")
