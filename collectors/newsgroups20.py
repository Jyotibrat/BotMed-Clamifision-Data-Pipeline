"""
Collect discussion-forum-style text from the classic 20 Newsgroups dataset
via scikit-learn. Deliberately excludes 'sci.med' -- everything here should
be genuinely non-medical (politics, religion, tech, hobbies, sports, etc.)
"""
import random
from sklearn.datasets import fetch_20newsgroups
from botmed_dataset_builder.config import NON_MEDICAL_LABEL, QUOTAS, RANDOM_SEED
from botmed_dataset_builder.schema import make_records, save_partial

EXCLUDE_CATEGORIES = {"sci.med"}


def collect():
    target = QUOTAS["newsgroups20"]
    data = fetch_20newsgroups(subset="all", remove=("headers", "footers", "quotes"))
    target_names = data.target_names

    texts = [
        text for text, label_idx in zip(data.data, data.target)
        if target_names[label_idx] not in EXCLUDE_CATEGORIES
    ]

    random.seed(RANDOM_SEED)
    random.shuffle(texts)
    texts = texts[:target]

    records = make_records(texts, NON_MEDICAL_LABEL, source="newsgroups20", subtopic="forum_post")
    return save_partial(records, "newsgroups20")


if __name__ == "__main__":
    collect()
