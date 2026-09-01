"""
Every collector produces a list of dicts with this exact shape, so they can
all be concatenated and processed identically downstream.
"""
from pathlib import Path
import pandas as pd

SCHEMA_COLUMNS = ["text", "label", "source", "subtopic"]


def make_records(texts, label, source, subtopic=None):
    """Wrap a list of raw strings into schema-conformant records.
    Silently drops empty/whitespace-only strings.
    """
    return [
        {"text": t.strip(), "label": label, "source": source, "subtopic": subtopic}
        for t in texts
        if t and t.strip()
    ]


def save_partial(records, name, out_dir="data/raw"):
    """Save one collector's output to its own CSV so a failed/slow source
    doesn't force you to re-run everything else.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records, columns=SCHEMA_COLUMNS)
    path = Path(out_dir) / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"[{name}] saved {len(df)} rows -> {path}")
    return path


def load_partial(name, out_dir="data/raw"):
    path = Path(out_dir) / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame(columns=SCHEMA_COLUMNS)
    return pd.read_csv(path)
