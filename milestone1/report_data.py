"""Load the crawl results that the report pages are built from, plus the shared table and chart helpers.

The files in `data/` are written by `tools/export_report_data.py` from the crawl's `logs/` and `state/`
folders (see the README). Every table and figure of the report is computed from them when the book is
built. Set REPORT_DATA_DIR to read them from another folder.
"""

import json
import os
from pathlib import Path

import pandas as pd
from IPython.display import HTML, Markdown, display

DATA_DIR = Path(os.environ.get("REPORT_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
REQUIRED = ("benchmark.json", "benchmark_sessions.jsonl", "performance.json", "papers.csv", "run_history.jsonl",
            "metadata.csv", "versions.csv", "download_events.csv", "references_log.csv",
            "reference_fields.json", "corpus_check.json")
MB = 1024 * 1024
GB = 1024 * MB
ARXIV_DELAY = 3.0   # seconds between arXiv requests during the crawl (00_config.ARXIV_DELAY)

# The four ID ranges assigned to the group (00_config.ID_RANGES), 5,000 IDs each, both ends inclusive.
RANGES = {
    "R1": ("2609.32834", "2609.37833"),
    "R2": ("2605.17338", "2605.22337"),
    "R3": ("2605.07338", "2605.12337"),
    "R4": ("2603.20580", "2603.25579"),
}

# Chart colours: one fixed categorical order, never cycled; ink and grid stay neutral.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA]
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def check():
    """Stop the build with a clear message instead of publishing figures of missing data."""
    missing = [name for name in REQUIRED if not (DATA_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing in {DATA_DIR}: {', '.join(missing)}. Run tools/export_report_data.py on the crawl "
            "folder (see README.md).")


def show(fig, height=380, margin=None):
    """Display an interactive Plotly figure using the native Jupyter Book 2 (MyST) Plotly mimebundle.

    MyST book-theme bundles `@jupyterlab/plotly-extension` and renders `application/vnd.plotly.v1+json`
    natively with hover tooltips, zoom/pan, legend toggling and PNG export.
    """
    m = dict(l=55, r=25, t=60, b=45)
    if margin:
        m.update(margin)
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color="#2f2e2c", size=12),
        title=dict(x=0.0, xanchor="left", font=dict(size=14, color=INK)),
        margin=m,
        hoverlabel=dict(font_size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=GRID)
    payload = json.loads(fig.to_json())
    payload["config"] = PLOTLY_CONFIG
    display({"application/vnd.plotly.v1+json": payload}, raw=True)


def md(text):
    """Show generated text as Markdown (numbers are filled in at build time)."""
    display(Markdown(text))


def table(frame, caption, formats=None, index=False):
    """Show a DataFrame as a numbered table: caption above, thousands separators, optional formats."""
    md(f"*{caption}*")
    styler = frame.style.format(formats or {}, thousands=",", na_rep="–")
    display(styler if index else styler.hide(axis="index"))


def collapsible_table(frame, summary, max_height=340):
    """Render a DataFrame inside a collapsible HTML <details> block."""
    html_table = frame.to_html(index=False, border=0, classes="dataframe")
    display(HTML(
        f"<details><summary><strong>{summary}</strong></summary>"
        f"<div style='max-height:{max_height}px;overflow:auto;margin-top:8px;'>{html_table}</div>"
        f"</details>"
    ))


def figure_caption(caption):
    md(f"*{caption}*")


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


def benchmark():
    """logs/benchmark.json: the Milestone 1 metrics over every Colab session."""
    return _json("benchmark.json")


def sessions():
    """logs/benchmark_sessions.jsonl: one row per Colab session."""
    frame = pd.DataFrame(_jsonl("benchmark_sessions.jsonl"))
    for column in ("start", "end"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    stages = pd.DataFrame(list(frame.pop("stages_seconds"))).reindex(
        columns=["discovery", "download", "references"])
    return pd.concat([frame, stages.add_suffix("_seconds")], axis=1)


def performance():
    """logs/performance.json (04_monitor format), including the RAM time series."""
    return _json("performance.json")


def run_history():
    """state/download/run_history.jsonl: one row per run of the downloader."""
    frame = pd.json_normalize(_jsonl("run_history.jsonl"))
    frame["finished_at"] = pd.to_datetime(frame["finished_at"], utc=True)
    return frame


def papers():
    """logs/papers.csv: one row per assigned ID, with `range` and `outcome` columns added.

    outcome: not_on_arxiv (no version exists), incomplete (a version is still missing),
    latex (every version has LaTeX), pdf_only (no version has LaTeX), mixed (some do).
    """
    frame = pd.read_csv(DATA_DIR / "papers.csv", dtype={"id": str})
    for column in ("versions", "versions_ok", "size_before", "size_after", "n_refs", "n_arxiv_refs", "seconds"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    complete = frame["error"].fillna("") != "unprocessed source versions"

    def outcome(row, done):
        if row.versions == 0:
            return "not_on_arxiv"
        if not done:
            return "incomplete"
        if row.versions_ok == row.versions:
            return "latex"
        return "pdf_only" if row.versions_ok == 0 else "mixed"

    frame["outcome"] = [outcome(row, done) for row, done in zip(frame.itertuples(), complete)]
    frame["range"] = frame["id"].map(range_of)
    return frame


def metadata():
    """One row per assigned ID from the discovery manifest: versions, primary category, dates."""
    frame = pd.read_csv(DATA_DIR / "metadata.csv", dtype={"id": str}, keep_default_na=False)
    for column in ("submitted", "last_revised"):
        frame[column] = pd.to_datetime(frame[column].replace("", pd.NaT))
    frame["range"] = frame["id"].map(range_of)
    return frame


def versions():
    """One row per processed source version (the download receipts)."""
    frame = pd.read_csv(DATA_DIR / "versions.csv", dtype={"id": str})
    frame["finished_at"] = pd.to_datetime(frame["finished_at"], utc=True)
    frame["range"] = frame["id"].map(range_of)
    return frame


def events():
    """One row per failed (`errors`) or refused (`throttles`) source request."""
    frame = pd.read_csv(DATA_DIR / "download_events.csv", dtype={"id": str})
    frame["at"] = pd.to_datetime(frame["at"], utc=True)
    return frame


def reference_log():
    """logs/references.csv: one row per paper each time its references were requested."""
    frame = pd.read_csv(DATA_DIR / "references_log.csv", dtype={"id": str})
    frame["logged_at"] = pd.to_datetime(frame["logged_at"], utc=True)
    return frame


def reference_fields():
    """Field completeness over every saved reference (all references.json files)."""
    return _json("reference_fields.json")


def corpus_check():
    """`ok` receipts whose vN/ folder was missing when the data was exported."""
    return _json("corpus_check.json")
