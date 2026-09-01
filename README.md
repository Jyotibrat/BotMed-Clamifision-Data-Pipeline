# BotMed Dataset Builder

Builds a curated, balanced, ~50,000-row CSV dataset (`data/final/train.csv`,
`val.csv`, `test.csv`) for training a binary "medical vs non-medical" text
classifier, aggregated from 11 public sources.

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

You'll also need `git` installed (used to clone the MedQuAD repo).

## 2. Set up credentials (.env file)

Credentials are loaded from a `.env` file via `python-dotenv` -- no manual
`export`ing, no shell profile edits.

1. Copy the template: `cp .env.example .env` (place it in the same folder
   you run `python -m botmed_dataset_builder.build_dataset` from -- i.e.
   the parent directory that contains the `botmed_dataset_builder/` folder).
2. Fill in the real values as described below.
3. `.env` is already in `.gitignore` -- never commit it.

### NCBI (PubMed) -- optional but recommended
No account needed, but NCBI asks for a contact email as etiquette, and an
optional free API key raises your rate limit from 3 to 10 requests/sec.
- Email: just any email you're okay identifying requests with.
- API key (optional): create an NCBI account -> Account Settings -> API Key Management.

Set `NCBI_EMAIL` and `NCBI_API_KEY` in `.env`.

### Wikipedia -- rate limiting is real, read this
Wikimedia's [User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy)
throttles anonymous/non-compliant clients more aggressively. Set `WIKIPEDIA_CONTACT`
in `.env` (or leave blank to reuse `NCBI_EMAIL`) so requests carry proper contact info.

Even with that, Wikipedia quotas are intentionally small (2,000 each) because
a real run showed this is the actual bottleneck source -- a 7,000-title
target only yielded 549 rows after a very long, heavily-throttled run. If
you still see constant `429 rate limited` messages at the smaller quota,
that's likely an IP-level cooldown, not something a code fix solves --
wait roughly an hour and re-run just that collector:
```bash
python -m botmed_dataset_builder.build_dataset --only wikipedia_medical wikipedia_nonmedical --force
```

### Kaggle (MTSamples)
1. Go to https://www.kaggle.com/settings/account -> "Create New Token".
2. This downloads `kaggle.json`. Place it at `~/.kaggle/kaggle.json` (Linux/Mac)
   or `C:\Users\<you>\.kaggle\kaggle.json` (Windows).
3. `chmod 600 ~/.kaggle/kaggle.json` on Linux/Mac.

No `.env` entries needed if `kaggle.json` is in place -- the `kaggle` CLI
package picks it up automatically. (The `KAGGLE_USERNAME`/`KAGGLE_KEY` fields
in `.env.example` are only a fallback if you'd rather not use `kaggle.json`.)

### Mayo Clinic scraping -- disabled by default
`collectors/webmd_mayo.py` was written to scrape Mayo Clinic's public
disease/condition pages, checking `robots.txt` before every request. A real
run confirmed Mayo's `robots.txt` **fully disallows crawling** the
`/diseases-conditions/` path across the board -- this isn't a bug, the
collector is correctly refusing to fetch pages the site has blocked. So
it's excluded from `COLLECTORS` in `build_dataset.py` by default, and its
quota has been folded into PubMed/MedQuAD/Wikipedia medical instead (see
`config.py`).

If you want a similar "consumer-facing symptom text" source later, look for
a site whose `robots.txt` actually permits crawling, or use an existing
open-licensed consumer-health dataset instead of scraping.

## 3. Run the full pipeline

From the directory **containing** `botmed_dataset_builder/`:

```bash
python -m botmed_dataset_builder.build_dataset
```

This will:
1. Run all 11 collectors (each saves its own `data/raw/<source>.csv` so a
   failed source doesn't force a full re-run).
2. Combine everything into one DataFrame.
3. Clean text (strip HTML/URLs, normalize whitespace, truncate very long docs).
4. Deduplicate (exact + near-duplicate).
5. Balance classes to exactly 50/50 medical vs non-medical.
6. Split into stratified train/val/test (80/10/10), stratified by both
   label and source so no split accidentally loses an entire source.
7. Save `data/final/train.csv`, `val.csv`, `test.csv` -- each with columns
   `text, label, source, subtopic` (label: 1 = medical, 0 = non-medical).

## Useful flags

```bash
# Only re-run one collector (e.g. after a transient failure)
python -m botmed_dataset_builder.build_dataset --only pubmed --force

# Skip collection entirely, just re-clean/dedup/split already-saved data/raw/*.csv
python -m botmed_dataset_builder.build_dataset --skip-collect
```

## Casual-register sources (medquestionpairs, synthetic_casual)

Added after real training/testing surfaced a genuine problem: a model
trained on the original sources hit 99.95% test accuracy but classified
**every** short, casual, first-person medical query (e.g. "my chest hurts
when i breathe, should i worry") as non-medical with 1.000 confidence. It
had learned to recognize PubMed/MedQuAD/MTSamples's formal writing style,
not the underlying "is this medical" concept.

- `medquestionpairs.py` pulls real patient-asked questions from
  `curaihealth/medical_questions_pairs` (HealthTap, via Curai's doctors) --
  small (~1.5k unique questions) but genuinely authentic register. No
  credentials needed, just `datasets` (already in requirements.txt).
- `synthetic_casual.py` generates unlimited, controllable, template-based
  casual symptom questions locally -- no network calls, no credentials,
  runs instantly. Not a substitute for real data, but the volume lever:
  medquestionpairs alone can't outweigh 15,000 PubMed rows.

These were added on top of existing quotas without rebalancing PubMed/
MedQuAD/MTSamples down -- see the note in `config.py`'s `QUOTAS` dict for
why, and revisit if the register gap persists after retraining and
re-testing with cell 12 of the training notebook.

## Adjusting dataset size or source mix

Edit the `QUOTAS` dict in `config.py`. Current targets sum to ~25k medical +
~25k non-medical = ~50k raw rows before cleaning/dedup (expect the final
balanced dataset to land somewhat below that, since cleaning/dedup and the
50/50 balancing step both trim rows).

## A note on data quality

The single biggest risk for this specific classifier is a **register
mismatch**: formal sources (PubMed, Wikipedia) vs. casual sources (Amazon/
Yelp reviews, forum posts) can let the model learn "formal = medical"
instead of actual topic. Amazon/Yelp reviews cover the casual register on
the non-medical side; there's no equivalent casual, typo-prone, "how real
users actually type a symptom question" source on the medical side in this
pipeline currently. Worth keeping in mind when you spot-check the final
dataset -- if the trained model struggles on short informal medical
queries specifically, that gap is the likely cause, and hand-writing 100-200
realistic example queries is a cheap fix.

After building the dataset, it's worth manually spot-checking ~100-200
random rows from `data/final/train.csv` for mislabels before you spend GPU
time fine-tuning on it.
