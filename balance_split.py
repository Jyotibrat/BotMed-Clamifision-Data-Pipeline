from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from botmed_dataset_builder.config import RANDOM_SEED, FINAL_DIR


def balance_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Downsample the majority class so medical/non-medical are 50/50.
    We deliberately downsample rather than upsample -- duplicating rows
    for a text classifier just teaches it to memorize repeats.

    Implemented with explicit boolean-mask + concat rather than
    groupby().apply() -- recent pandas versions can silently drop the
    grouping column from an apply() result, which is a nasty bug to hit
    downstream when 'label' just disappears.
    """
    counts = df["label"].value_counts()
    print(f"Pre-balance class counts:\n{counts}")
    minority_n = counts.min()

    parts = []
    for label_value in sorted(df["label"].unique()):
        subset = df[df["label"] == label_value]
        parts.append(subset.sample(n=minority_n, random_state=RANDOM_SEED))
    balanced = pd.concat(parts, ignore_index=True)

    print(f"Post-balance: {len(balanced)} rows ({minority_n} per class)")
    return balanced


def stratified_split(df: pd.DataFrame, train_frac=0.8, val_frac=0.1):
    """80/10/10 train/val/test, stratified by label AND source, so no split
    accidentally loses an entire source (e.g. all of WebMD ending up only
    in the test set).
    """
    df = df.copy()
    df["strata"] = df["label"].astype(str) + "_" + df["source"].astype(str)

    # sources with too few rows for stratified split get folded into a
    # generic bucket so train_test_split doesn't error on a size-1 group
    strata_counts = df["strata"].value_counts()
    rare = strata_counts[strata_counts < 3].index
    df.loc[df["strata"].isin(rare), "strata"] = df.loc[df["strata"].isin(rare), "label"].astype(str)

    train_df, temp_df = train_test_split(
        df, train_size=train_frac, stratify=df["strata"], random_state=RANDOM_SEED
    )
    relative_val = val_frac / (1 - train_frac)
    val_df, test_df = train_test_split(
        temp_df, train_size=relative_val, stratify=temp_df["strata"], random_state=RANDOM_SEED
    )

    for d in (train_df, val_df, test_df):
        d.drop(columns=["strata"], inplace=True)

    return train_df, val_df, test_df


def save_splits(train_df, val_df, test_df, out_dir=FINAL_DIR):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    train_df.to_csv(Path(out_dir) / "train.csv", index=False)
    val_df.to_csv(Path(out_dir) / "val.csv", index=False)
    test_df.to_csv(Path(out_dir) / "test.csv", index=False)
    print(f"Saved train={len(train_df)} val={len(val_df)} test={len(test_df)} -> {out_dir}/")
