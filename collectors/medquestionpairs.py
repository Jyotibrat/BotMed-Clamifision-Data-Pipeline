"""
Collect real, casual, first-person patient-asked medical questions from
curaihealth/medical_questions_pairs (sourced from HealthTap by Curai's
doctors). This is the source that specifically addresses the "register
gap" -- PubMed/MedQuAD/MTSamples are formal/structured, this is genuinely
how patients phrase real questions.

The dataset is structured as similar/dissimilar question PAIRS (for a
question-matching task), but we only want the raw question text -- so we
pull both question_1 and question_2 columns and deduplicate, ignoring the
pairing/similarity label entirely.
"""
from datasets import load_dataset
from botmed_dataset_builder.config import MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial


def collect():
    target = QUOTAS["medquestionpairs"]
    ds = load_dataset("curaihealth/medical_questions_pairs", split="train")

    questions = set()
    for row in ds:
        q1 = (row.get("question_1") or "").strip()
        q2 = (row.get("question_2") or "").strip()
        if q1:
            questions.add(q1)
        if q2:
            questions.add(q2)

    texts = list(questions)[:target]
    records = make_records(texts, MEDICAL_LABEL, source="medquestionpairs", subtopic="patient_question")
    return save_partial(records, "medquestionpairs")


if __name__ == "__main__":
    collect()
