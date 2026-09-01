# BotMed Clamifision Data Pipeline

Data collection and curation pipeline for **Clamifision**, BotMed's binary medical/non-medical text classifier. Aggregates and cleans data from 10 public sources into a balanced, stratified train/val/test split (~40,000 rows total) ready for fine-tuning.

- **Model:** [BJyotibrat/Clamifision-v1](https://huggingface.co/BJyotibrat/Clamifision-v1)
- **Training & Inference Repository:** [Jyotibrat/BotMed-Clamifision](https://github.com/Jyotibrat/BotMed-Clamifision) 

## Table of contents
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project structure](#project-structure)
- [Output schema](#output-schema)
- [Data sources](#data-sources)
- [Known limitations](#known-limitations)
- [License](#license)

## Installation

```bash
pip install -r requirements.txt
```

Requires `git` (used to clone the MedQuAD repo).

## Configuration

Credentials are loaded from a `.env` file via `python-dotenv`.

```bash
cp .env.example .env
```

Fill in the values below. `.env` is already git-ignored.

| Variable | Required | Notes |
|---|---|---|
| `NCBI_EMAIL` | Recommended | Any contact email, per NCBI E-utilities etiquette |
| `NCBI_API_KEY` | Optional | Raises PubMed rate limit from 3 to 10 req/sec |
| `WIKIPEDIA_CONTACT` | Recommended | Falls back to `NCBI_EMAIL` if unset. Wikimedia throttles non-compliant User-Agents harder |
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | Optional | Only needed if not using `~/.kaggle/kaggle.json` (see below) |

**Kaggle (MTSamples):** create a token at kaggle.com/settings/account, and place the downloaded `kaggle.json` at `~/.kaggle/kaggle.json` (`chmod 600` on Linux/Mac). The `kaggle` CLI picks it up automatically — no `.env` entry needed.

## Usage

From outside the directory `botmed_dataset_builder/`:

```bash
python -m botmed_dataset_builder.build_dataset
```

This runs all active collectors, combines their output, cleans text, deduplicates, balances classes 50/50, and writes a stratified 80/10/10 split to `data/final/`.

```bash
# Re-run a single collector after a transient failure
python -m botmed_dataset_builder.build_dataset --only pubmed --force

# Skip collection, just re-process already-saved data/raw/*.csv
python -m botmed_dataset_builder.build_dataset --skip-collect
```

Each collector caches its output independently in `data/raw/<source>.csv`, so a failed or slow source doesn't force a full re-run.

## Output schema

`train.csv` / `val.csv` / `test.csv` each contain:

| Column | Description |
|---|---|
| `text` | Cleaned input text |
| `label` | `1` = medical, `0` = non-medical |
| `source` | Which collector produced this row |
| `subtopic` | Collector-specific sub-category (e.g. `abstract`, `patient_question`) |

## Data sources

**Medical:** PubMed abstracts, MedQuAD, MTSamples, Wikipedia medical articles, real patient-asked questions ([HealthTap via curaihealth](https://huggingface.co/datasets/curaihealth/medical_questions_pairs)), and template-generated casual symptom queries.

**Non-medical:** AG News, 20 Newsgroups, Amazon/Yelp reviews, Wikipedia non-medical articles.

Two sources are intentionally disabled by default and excluded from `COLLECTORS` in `build_dataset.py`:
- **Mayo Clinic** (`webmd_mayo.py`) — the site's `robots.txt` disallows crawling the relevant paths entirely.
- **Reddit** — removed after Reddit gated new API app registration behind manual approval, making it inaccessible to most developers.

Quotas are configured in `config.py`'s `QUOTAS` dict.

## Known limitations

**Register imbalance.** Formal sources (PubMed, Wikipedia) risk teaching a model "formal writing = medical" rather than actual topic. The `medquestionpairs` and `synthetic_casual` sources exist specifically to counter this by adding short, casual, first-person medical text — but PubMed still dominates the medical class by volume. If a trained model underperforms on short informal queries, this is the likely cause.

**Wikipedia throughput.** Wikimedia's anonymous-API rate limiting is aggressive; quotas are kept deliberately small (2,000/class) because larger targets have been throttled heavily in practice, sometimes indicating an IP-level cooldown rather than a code issue.

Before training, spot-check ~100–200 random rows from `data/final/train.csv` for mislabels.

## License

MIT — see [LICENSE](https://github.com/Jyotibrat/BotMed-Clamifision-Data-Pipeline/blob/main/LICENSE).