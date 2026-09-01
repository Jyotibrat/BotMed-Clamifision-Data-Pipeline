"""
Central configuration for the BotMed dataset builder.

All collectors read their quotas and credentials from here. Nothing here
hits the network by itself -- this is just constants and env var lookups.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env in the current working directory, if present

RANDOM_SEED = 42

MEDICAL_LABEL = 1
NON_MEDICAL_LABEL = 0

RAW_DIR = "data/raw"
FINAL_DIR = "data/final"

# --------------------------------------------------------------------------
# Per-source quotas. These sum to ~25,000 medical + ~25,000 non-medical
# = ~50,000 rows before cleaning/dedup (expect ~10-15% loss after cleaning,
# so aim a little high). Tune these if a source runs dry (e.g. MedQuAD
# only has ~47k QA pairs total across its XML files) or if you want a
# different medical:non-medical ratio.
# --------------------------------------------------------------------------
QUOTAS = {
    # ---- medical ----
    "pubmed": 15000,          # bumped up further -- proven reliable at volume once retry/fault-isolation was added, and has no real supply ceiling
    "medquad": 5500,
    "mtsamples": 4500,        # MTSamples has ~4999 total records, this asks for ~all of them
    "wikipedia_medical": 2000,  # scaled WAY down -- see note below
    "medquestionpairs": 3000,   # real casual patient-asked questions (HealthTap via curaihealth) -- see note below; actual yield will likely be lower, capped by the dataset's real size (~1.5k unique questions across both columns)
    "synthetic_casual": 6000,   # template-generated casual symptom queries -- see note below

    # ---- non-medical ----
    "agnews": 10500,          # bumped up -- ran cleanly and fast in practice
    "newsgroups20": 4500,
    "amazon_yelp": 10000,     # bumped up -- ran cleanly and fast in practice
    "wikipedia_nonmedical": 2000,  # scaled WAY down -- see note below
}

# --------------------------------------------------------------------------
# medquestionpairs + synthetic_casual were added after real training/testing
# showed a genuine register-gap failure: a fine-tuned model hit 99.95% test
# accuracy but classified EVERY short, casual, first-person medical query
# (e.g. "my chest hurts when i breathe, should i worry") as non_medical with
# 1.000 confidence. The model had learned to recognize PubMed/MedQuAD/
# MTSamples's formal writing style, not the underlying "is this medical"
# concept -- because nothing in the medical class was casual/first-person
# register, while the non-medical class (Amazon/Yelp reviews) had plenty of
# short casual text. These two sources exist specifically to close that gap:
#   - medquestionpairs: REAL patient-asked questions (small, ~1.5k, but
#     authentic register)
#   - synthetic_casual: template-generated casual symptom questions
#     (unlimited volume, controllable, guaranteed-casual register, but not
#     real user data -- a complement to medquestionpairs, not a replacement)
# These were deliberately added WITHOUT rebalancing pubmed/medquad/mtsamples
# quotas down -- PubMed's dominant share of the medical class is still a
# real underlying issue (see config comments above), just not addressed in
# this pass. Revisit if the register gap persists after retraining.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# webmd_mayo is disabled by default -- Mayo Clinic's robots.txt disallows
# crawling the entire /diseases-conditions/ path (confirmed by an actual
# run: every letter A-Z came back "robots.txt disallows"). Not a bug, just
# the site's own crawl policy being correctly respected.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Wikipedia quotas were cut from 7000/6000 down to 2000/2000 after a real
# run showed Wikimedia's anonymous-API rate limiting is the actual
# bottleneck, not a code bug -- a run with proper retry/backoff still only
# got 549/7000 and 548/6000 through in a very long wall-clock time. This is
# most likely IP-level throttling (possibly a cooldown carried over from an
# earlier, un-throttled run hammering the API). If Wikipedia keeps 429-ing
# heavily even at the smaller quota, wait ~1 hour before re-running that
# collector alone (rate-limit windows are typically time-boxed, not
# permanent), and make sure WIKIPEDIA_CONTACT is set in .env -- Wikimedia's
# User-Agent policy throttles non-compliant/anonymous-looking clients harder.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Credentials / contact info -- set these as environment variables rather
# than hardcoding them. See README.md for how to obtain each one.
# --------------------------------------------------------------------------
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "")          # required by NCBI E-utilities etiquette
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")      # optional, raises rate limit from 3/s to 10/s

# Wikimedia's User-Agent policy (https://meta.wikimedia.org/wiki/User-Agent_policy)
# requires a contact URL or email in the User-Agent string. Requests without
# one get throttled more aggressively than ones that comply -- reuses
# NCBI_EMAIL as a sensible default so you don't need a second env var, but
# feel free to set this separately if you want a different contact.
WIKIPEDIA_CONTACT = os.environ.get("WIKIPEDIA_CONTACT", NCBI_EMAIL)

KAGGLE_USERNAME = os.environ.get("KAGGLE_USERNAME", "")  # used only if you let kaggle.json auto-auth instead
KAGGLE_KEY = os.environ.get("KAGGLE_KEY", "")

MIN_TEXT_LENGTH_CHARS = 20
MAX_TEXT_LENGTH_CHARS = 4000  # truncate very long docs (e.g. full Wikipedia articles) to keep things manageable
