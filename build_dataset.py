"""
Run this to build the full BotMed medical/non-medical classifier dataset.

Usage (from the directory *containing* botmed_dataset_builder/):
    python -m botmed_dataset_builder.build_dataset

Each collector saves its own CSV to data/raw/<source>.csv, so if one source
fails (bad credentials, a rate limit, a flaky scrape) you can fix that one
collector and re-run this script -- already-saved sources are re-used
automatically unless you pass --force.
"""
import argparse
import pandas as pd
from pathlib import Path

from botmed_dataset_builder.config import RAW_DIR
from botmed_dataset_builder.schema import load_partial, SCHEMA_COLUMNS
from botmed_dataset_builder.cleaning import clean_and_filter
from botmed_dataset_builder.dedup import deduplicate
from botmed_dataset_builder.balance_split import balance_classes, stratified_split, save_splits

# (module_name, collect_function_name) for every active source.
# webmd_mayo is intentionally NOT included -- Mayo Clinic's robots.txt
# fully disallows the pages this pipeline wants. See config.py for details.
COLLECTORS = [
    ("pubmed", "collectors.pubmed"),
    ("medquad", "collectors.medquad"),
    ("mtsamples", "collectors.mtsamples"),
    ("wikipedia_medical", "collectors.wikipedia_medical"),
    ("medquestionpairs", "collectors.medquestionpairs"),
    ("synthetic_casual", "collectors.synthetic_casual"),
    ("agnews", "collectors.agnews"),
    ("newsgroups20", "collectors.newsgroups20"),
    ("amazon_yelp", "collectors.amazon_yelp"),
    ("wikipedia_nonmedical", "collectors.wikipedia_nonmedical"),
]


def run_collectors(force: bool, only: list | None):
    import importlib

    for name, module_path in COLLECTORS:
        if only and name not in only:
            continue

        raw_path = Path(RAW_DIR) / f"{name}.csv"
        if raw_path.exists() and not force:
            print(f"[{name}] already collected, skipping (use --force to re-run)")
            continue

        print(f"\n=== Running collector: {name} ===")
        try:
            module = importlib.import_module(f"botmed_dataset_builder.{module_path}")
            module.collect()
        except Exception as e:
            print(f"[{name}] FAILED: {e}")
            print(f"[{name}] Continuing with other sources -- fix this one and re-run "
                  f"'python -m botmed_dataset_builder.build_dataset --only {name} --force' later.")


def combine_all():
    frames = []
    for name, _ in COLLECTORS:
        df = load_partial(name)
        if not df.empty:
            frames.append(df)
        else:
            print(f"[combine] WARNING: {name} contributed 0 rows")
    if not frames:
        raise RuntimeError("No collectors produced any data -- nothing to combine.")
    combined = pd.concat(frames, ignore_index=True)
    print(f"\n[combine] {len(combined)} total raw rows across {len(frames)} sources")
    return combined


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-run all collectors even if cached")
    parser.add_argument("--only", nargs="*", default=None, help="Only run these collector names")
    parser.add_argument("--skip-collect", action="store_true",
                         help="Skip collection, just re-process already-saved data/raw/*.csv")
    args = parser.parse_args()

    if not args.skip_collect:
        run_collectors(force=args.force, only=args.only)

    combined = combine_all()

    records = combined.to_dict("records")
    records = clean_and_filter(records)
    print(f"[clean] {len(records)} rows after cleaning/length filtering")

    records = deduplicate(records)

    df = pd.DataFrame(records, columns=SCHEMA_COLUMNS)
    df = balance_classes(df)

    train_df, val_df, test_df = stratified_split(df)
    save_splits(train_df, val_df, test_df)

    print("\n=== Done ===")
    print("Per-source breakdown in final dataset:")
    print(df["source"].value_counts())


if __name__ == "__main__":
    main()
