"""Load the Milestone 3 logs and label summaries, plus shared table and interactive Plotly helpers.

The files in `data/` are written by `tools/export_m3_data.py` from the Milestone 3 `logs/` and `labels/`
folders (see README.md). Every table, figure and computed number in chapters 3–5 is produced from them when
the book is built. Set REPORT_DATA_DIR to read them from another folder.
"""

import json
import os
from pathlib import Path

import pandas as pd
from IPython.display import Markdown, display

DATA_DIR = Path(os.environ.get("REPORT_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
REQUIRED = (
    "m3_data_summary.json",
    "m3_labels.json",
    "m3_feature_report.csv",
    "m3_cleaning_report.csv",
    "m3_metrics.json",
    "m3_model_selection.csv",
    "m3_run.json",
    "m3_requirements.json",
    "m3_hf_export.json",
    "m3_split.json",
    "m3_selection.csv",
)

MEMBERS = {
    "TV1": ("La Anh Hào", "2603.20580–2603.25579"),
    "TV2": ("Võ Nguyễn Vân Anh", "2609.32834–2609.37833"),
    "TV3": ("Lưu Minh Quân", "2605.17338–2605.22337"),
    "TV4": ("Phạm Tấn Nhật Thịnh", "2605.07338–2605.12337"),
}

# Shared report palette (matches Milestones 1 and 2).
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
PURPLE, TEAL, SLATE = "#7a5cc7", "#1e8e9e", "#6e737b"
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, PURPLE, TEAL, SLATE]
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def check():
    """Stop the build with a clear message if any Milestone 3 data file is missing."""
    missing = [name for name in REQUIRED if not (DATA_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing in {DATA_DIR}: {', '.join(missing)}. Run tools/export_m3_data.py on the Milestone 3 "
            "logs folder (see README.md).")


def show(fig, height=380, margin=None):
    """Display an interactive Plotly figure using the native Jupyter Book 2 (MyST) Plotly mimebundle."""
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
    display(Markdown(text))


def table(frame, caption, formats=None, index=False):
    md(f"*{caption}*")
    styler = frame.style.format(formats or {}, thousands=",", na_rep="–")
    display(styler if index else styler.hide(axis="index"))


def figure_caption(caption):
    md(f"*{caption}*")


def hm(seconds):
    s = int(round(seconds))
    if s >= 3600:
        return f"{s // 3600} h {s % 3600 // 60:02d} min"
    if s >= 60:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{seconds:.1f} s"


def _json(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def data_summary():
    return _json("m3_data_summary.json")


def labels():
    return _json("m3_labels.json")


def feature_report():
    return pd.read_csv(DATA_DIR / "m3_feature_report.csv")


def cleaning_report():
    return pd.read_csv(DATA_DIR / "m3_cleaning_report.csv")


def metrics():
    return _json("m3_metrics.json")


def model_selection():
    return pd.read_csv(DATA_DIR / "m3_model_selection.csv")


def run_log():
    return _json("m3_run.json")


def requirements():
    return _json("m3_requirements.json")


def hf_export():
    return _json("m3_hf_export.json")


def split():
    return _json("m3_split.json")


def selection():
    return pd.read_csv(DATA_DIR / "m3_selection.csv", dtype={"arxiv_id": str})
