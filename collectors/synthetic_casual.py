"""
Generate synthetic, casual, first-person medical questions via templates.

This exists because the real casual-text sources available (HealthTap
questions, ~1.5k unique) aren't enough volume to meaningfully shift the
register balance of the medical class away from formal/PubMed-dominated
text. Templates give us controllable, unlimited, guaranteed-casual volume
in exactly the register that mattered in testing: short, first-person,
informal symptom questions -- the kind BotMed will actually see in
production.

Not a substitute for real data -- a complement. Combined with
medquestionpairs.py's real HealthTap questions, this directly targets the
formal-vs-casual register gap that testing surfaced (the model was
classifying every casual query as non_medical, despite 99%+ test accuracy
on formal/source-matched text).
"""
import random
from botmed_dataset_builder.config import MEDICAL_LABEL, QUOTAS, RANDOM_SEED
from botmed_dataset_builder.schema import make_records, save_partial

SYMPTOMS = [
    "a headache", "a fever", "a sore throat", "a stomach ache", "back pain",
    "chest pain", "dizziness", "a rash", "a cough", "nausea", "fatigue",
    "blurry vision", "joint pain", "ear pain", "shortness of breath",
    "diarrhea", "constipation", "swelling in my ankles", "numbness in my hand",
    "itching all over", "bruising really easily", "hair loss",
    "unexplained weight loss", "trouble sleeping", "panic attacks",
    "heart palpitations", "night sweats", "chills", "muscle cramps",
    "a swollen knee", "a twisted ankle", "burning when i pee",
    "blood in my stool", "blood in my urine", "a lump in my neck",
    "trouble swallowing", "ringing in my ears", "watery eyes", "a dry mouth",
    "mouth sores", "bleeding gums", "a stiff neck", "tingling in my feet",
    "a racing heartbeat", "cold sweats", "a persistent cough",
    "pain when i breathe in", "a burning sensation in my chest",
    "swollen lymph nodes", "yellowish skin", "dark urine", "pale stool",
    "excessive thirst", "frequent urination", "cracked heels",
    "a metallic taste in my mouth", "sensitivity to light",
    "sudden hearing loss", "double vision", "difficulty breathing at night",
]

DURATIONS = [
    "for 2 days", "since yesterday", "for about a week now",
    "on and off for a month", "since this morning", "for the past few hours",
    "for 3 weeks", "since last night", "for a couple days", "for a few weeks",
    "since last week", "for the past hour", "for like 5 days", "all day today",
    "for the past couple months", "randomly for a while now",
]

SYMPTOM_TEMPLATES = [
    "I've had {symptom} {duration}, should I be worried?",
    "having {symptom} {duration}, is this normal?",
    "why do i have {symptom} {duration}",
    "{symptom} {duration} and its getting worse, what could this be",
    "is it normal to have {symptom} {duration}",
    "i've been dealing with {symptom} {duration}, any idea what's causing it",
    "my kid has {symptom} {duration}, should i take them to a doctor",
    "does {symptom} {duration} mean something serious",
    "should i go to the er for {symptom} that's been going on {duration}",
    "{symptom} {duration}, anyone know what this could be from",
    "what could cause {symptom} {duration}",
    "is {symptom} {duration} something to worry about or will it just go away",
    "i keep getting {symptom} {duration} and idk why",
    "started having {symptom} {duration}, is that a bad sign",
    "{symptom} {duration} -- worth seeing a doctor or just wait it out?",
]

GENERAL_HEALTH_TEMPLATES = [
    "can i take ibuprofen and tylenol together",
    "is it safe to drink alcohol with antibiotics",
    "how long does a uti usually last",
    "what happens if i miss a birth control pill",
    "how much melatonin is safe to take",
    "is it bad to take expired medicine",
    "can i take painkillers on an empty stomach",
    "how many hours after eating should i take my medication",
    "is it normal for antibiotics to make you feel nauseous",
    "can you overdose on vitamin d",
    "whats the difference between a cold and the flu",
    "how do i know if a cut is infected",
    "is it okay to work out with a fever",
    "how long should i rest a sprained ankle",
    "can dehydration cause headaches",
    "is it safe to take melatonin every night",
    "how do you bring a fever down fast",
    "can lack of sleep cause chest pain",
    "why does my knee hurt more in the morning",
    "is it normal to feel dizzy when standing up fast",
    "can stress cause stomach problems",
    "how long is the flu contagious for",
    "should i be worried about a mole that changed color",
    "is it safe to exercise with a cold",
    "can allergies cause a sore throat",
    "how much water should i drink a day",
    "is it bad to crack your knuckles a lot",
    "can not eating enough cause dizziness",
    "why do i get headaches every afternoon",
    "is a resting heart rate of 100 normal",
]

# Light informality perturbations, applied probabilistically -- real users
# often skip apostrophes, use lowercase, or drop punctuation entirely
INFORMALITY_SUBS = [
    (" i've ", " ive "), (" it's ", " its "), (" don't ", " dont "),
    (" can't ", " cant "), (" i'm ", " im "), (" doesn't ", " doesnt "),
]


def _informalize(text, rng):
    text = text[0].lower() + text[1:] if text else text
    for old, new in INFORMALITY_SUBS:
        if rng.random() < 0.4 and old in f" {text} ":
            text = f" {text} ".replace(old, new).strip()
    if rng.random() < 0.3 and text.endswith("?"):
        text = text[:-1]  # drop trailing question mark sometimes
    return text


def collect():
    target = QUOTAS["synthetic_casual"]
    rng = random.Random(RANDOM_SEED)

    generated = set()
    attempts = 0
    max_attempts = target * 20  # combinatorial space is large; avoid infinite loop if target is huge

    while len(generated) < target and attempts < max_attempts:
        attempts += 1
        if rng.random() < 0.75:
            template = rng.choice(SYMPTOM_TEMPLATES)
            symptom = rng.choice(SYMPTOMS)
            duration = rng.choice(DURATIONS)
            text = template.format(symptom=symptom, duration=duration)
        else:
            text = rng.choice(GENERAL_HEALTH_TEMPLATES)

        text = _informalize(text, rng)
        generated.add(text)

    texts = list(generated)[:target]
    records = make_records(texts, MEDICAL_LABEL, source="synthetic_casual", subtopic="templated_query")
    return save_partial(records, "synthetic_casual")


if __name__ == "__main__":
    collect()
