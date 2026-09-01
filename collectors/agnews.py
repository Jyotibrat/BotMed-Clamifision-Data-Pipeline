"""
Collect general news text from the AG News dataset (world/sports/business/
sci-tech) via HuggingFace `datasets`. This is entirely non-medical and gives
broad topical diversity on the negative class.
"""
from datasets import load_dataset
from botmed_dataset_builder.config import NON_MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial


def collect():
    target = QUOTAS["agnews"]
    ds = load_dataset("fancyzhx/ag_news", split="train")  # legacy "ag_news" id was retired by HF Hub
    ds = ds.shuffle(seed=42).select(range(min(target, len(ds))))
    texts = ds["text"]
    records = make_records(texts, NON_MEDICAL_LABEL, source="agnews", subtopic="news")
    return save_partial(records, "agnews")


if __name__ == "__main__":
    collect()
