"""
Collect consumer product/business review text (Amazon + Yelp) via
HuggingFace `datasets`. Reviews are a useful non-medical class because
they're short, opinionated, and conversational -- similar register to a
lot of real chat input, which helps the classifier generalize beyond
formal prose.
"""
from datasets import load_dataset
from botmed_dataset_builder.config import NON_MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial


def collect():
    target = QUOTAS["amazon_yelp"]
    half = target // 2

    # legacy "amazon_polarity" / "yelp_review_full" ids were retired by HF Hub
    amazon = load_dataset("fancyzhx/amazon_polarity", split="train")
    amazon = amazon.shuffle(seed=42).select(range(min(half, len(amazon))))
    amazon_texts = [f"{t} {c}".strip() for t, c in zip(amazon["title"], amazon["content"])]

    yelp = load_dataset("Yelp/yelp_review_full", split="train")
    yelp = yelp.shuffle(seed=42).select(range(min(target - half, len(yelp))))
    yelp_texts = yelp["text"]

    records = make_records(amazon_texts, NON_MEDICAL_LABEL, source="amazon_yelp", subtopic="amazon_review")
    records += make_records(yelp_texts, NON_MEDICAL_LABEL, source="amazon_yelp", subtopic="yelp_review")
    return save_partial(records, "amazon_yelp")


if __name__ == "__main__":
    collect()
