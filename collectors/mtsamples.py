"""
Collect real (de-identified) clinical transcription notes from the MTSamples
dataset, mirrored on Kaggle as "tboyle10/medicaltranscriptions".

Requires Kaggle API credentials (~/.kaggle/kaggle.json) -- see README for setup.
This is the single richest source of *formal clinical* register in the whole
pipeline, which is why it gets a large quota despite being one dataset.
"""
import subprocess
import zipfile
from pathlib import Path
import pandas as pd
from botmed_dataset_builder.config import MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial

KAGGLE_DATASET = "tboyle10/medicaltranscriptions"
CACHE_DIR = Path("data/_cache/mtsamples")


def _ensure_downloaded():
    csv_path = CACHE_DIR / "mtsamples.csv"
    if csv_path.exists():
        return csv_path

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print("[mtsamples] downloading via Kaggle API...")
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET, "-p", str(CACHE_DIR)],
        check=True,
    )
    zip_files = list(CACHE_DIR.glob("*.zip"))
    if not zip_files:
        raise FileNotFoundError(
            "[mtsamples] Kaggle download produced no zip file. Check your "
            "kaggle.json credentials are set up (see README)."
        )
    with zipfile.ZipFile(zip_files[0]) as zf:
        zf.extractall(CACHE_DIR)

    # the extracted csv filename varies slightly by mirror version
    candidates = list(CACHE_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError("[mtsamples] No CSV found after extracting Kaggle download.")
    return candidates[0]


def collect():
    csv_path = _ensure_downloaded()
    df = pd.read_csv(csv_path)

    # the mirror's column is usually "transcription"; fall back to description if missing
    text_col = "transcription" if "transcription" in df.columns else "description"
    texts = df[text_col].dropna().astype(str).tolist()

    target = QUOTAS["mtsamples"]
    texts = texts[:target]
    records = make_records(texts, MEDICAL_LABEL, source="mtsamples", subtopic="clinical_note")
    return save_partial(records, "mtsamples")


if __name__ == "__main__":
    collect()
