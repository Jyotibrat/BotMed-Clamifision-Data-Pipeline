"""
Collect Wikipedia article text from deliberately non-medical categories,
mirroring wikipedia_medical.py's approach so both classes have the same
"encyclopedic register" represented -- this forces the model to learn
topic, not writing style.
"""
import botmed_dataset_builder.collectors.wikipedia_medical as wm
from botmed_dataset_builder.config import NON_MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial

SEED_CATEGORIES = [
    "Category:History by period",
    "Category:Sports",
    "Category:Technology",
    "Category:Video games",
    "Category:Cooking",
    "Category:Music genres",
    "Category:World economies",
]


def collect():
    target = QUOTAS["wikipedia_nonmedical"]

    # temporarily point the shared category-walker at our non-medical seeds
    original_seeds = wm.SEED_CATEGORIES
    wm.SEED_CATEGORIES = SEED_CATEGORIES
    try:
        titles = wm._collect_titles(target)
    finally:
        wm.SEED_CATEGORIES = original_seeds

    print(f"[wikipedia_nonmedical] found {len(titles)} candidate article titles")
    texts = wm._fetch_extracts(titles)
    texts = texts[:target]
    records = make_records(texts, NON_MEDICAL_LABEL, source="wikipedia_nonmedical", subtopic="article")
    return save_partial(records, "wikipedia_nonmedical")


if __name__ == "__main__":
    collect()
