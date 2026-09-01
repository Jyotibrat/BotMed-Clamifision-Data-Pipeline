"""
Collect medical Q&A pairs from MedQuAD (Medical Question Answering Dataset),
a public dataset of consumer health questions curated by NIH.
Repo: https://github.com/abachaa/MedQuAD

We clone the repo and parse its XML files. Each XML has one or more
<QAPair> elements with <Question> and <Answer> children -- we combine
question + answer into one text sample.
"""
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from botmed_dataset_builder.config import MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial

REPO_URL = "https://github.com/abachaa/MedQuAD.git"
CLONE_DIR = Path("data/_cache/MedQuAD")


def _ensure_repo():
    if CLONE_DIR.exists():
        return
    CLONE_DIR.parent.mkdir(parents=True, exist_ok=True)
    print("[medquad] cloning MedQuAD repo (one-time, ~50MB)...")
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(CLONE_DIR)], check=True)


def _parse_xml_file(path: Path):
    texts = []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return texts
    root = tree.getroot()
    for qa_pair in root.iter("QAPair"):
        q_el = qa_pair.find("Question")
        a_el = qa_pair.find("Answer")
        q = (q_el.text or "").strip() if q_el is not None else ""
        a = (a_el.text or "").strip() if a_el is not None else ""
        if q and a:
            texts.append(f"{q} {a}")
        elif a:
            texts.append(a)
    return texts


def collect():
    _ensure_repo()
    target = QUOTAS["medquad"]
    all_texts = []

    for xml_path in CLONE_DIR.rglob("*.xml"):
        if len(all_texts) >= target:
            break
        all_texts.extend(_parse_xml_file(xml_path))

    all_texts = all_texts[:target]
    records = make_records(all_texts, MEDICAL_LABEL, source="medquad", subtopic="qa_pair")
    return save_partial(records, "medquad")


if __name__ == "__main__":
    collect()
