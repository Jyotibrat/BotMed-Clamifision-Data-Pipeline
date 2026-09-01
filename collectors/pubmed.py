"""
Collect PubMed abstracts via NCBI E-utilities.
Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/

Uses a broad list of search topics (not one query) so the resulting
abstracts aren't all clustered around a single specialty.
"""
import time
import requests
from botmed_dataset_builder.config import (
    NCBI_EMAIL, NCBI_API_KEY, MEDICAL_LABEL, QUOTAS,
)
from botmed_dataset_builder.schema import make_records, save_partial

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Broad spread of topics/specialties so the sample isn't dominated by one field
SEARCH_TOPICS = [
    "cardiology", "oncology", "diabetes", "infectious disease", "neurology",
    "psychiatry", "pediatrics", "dermatology", "orthopedics", "endocrinology",
    "gastroenterology", "pulmonology", "nephrology", "hematology", "rheumatology",
    "obstetrics", "surgery", "immunology", "public health", "pharmacology",
    "geriatrics", "emergency medicine", "radiology", "pathology", "anesthesiology",
]

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _rate_limit_delay():
    time.sleep(0.34 if NCBI_API_KEY else 0.4)  # ~10/s with key, ~3/s without (staying under limit)


def _request_with_retry(method, url, max_retries=4, base_delay=2.0, **kwargs):
    """NCBI's servers occasionally 502/503 under load -- this is expected
    and transient, not something to crash the whole run over. Retries with
    exponential backoff; gives up and raises only after max_retries."""
    delay = base_delay
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = method(url, timeout=kwargs.pop("timeout", 30), **kwargs)
            if resp.status_code in RETRYABLE_STATUS:
                print(f"[pubmed] {resp.status_code} on attempt {attempt + 1}/{max_retries}, "
                      f"retrying in {delay:.0f}s...")
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_exc = e
            print(f"[pubmed] request error on attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"[pubmed] exceeded {max_retries} retries for {url}") from last_exc


def _esearch(term, retmax):
    params = {
        "db": "pubmed", "term": term, "retmax": retmax, "retmode": "json",
        "sort": "relevance", "email": NCBI_EMAIL,
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    resp = _request_with_retry(requests.get, ESEARCH_URL, params=params)
    _rate_limit_delay()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def _efetch_abstracts(pmids, batch_size=100):
    """Fetch abstracts in small batches via POST -- a GET request with 300+
    PMIDs blows past URL length limits (414 Request-URI Too Long).

    Each batch is isolated: if one batch fails after retries, we log it and
    keep whatever batches already succeeded, rather than losing everything.
    """
    if not pmids:
        return []

    all_chunks = []
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = {
            "db": "pubmed", "id": ",".join(batch), "rettype": "abstract",
            "retmode": "text", "email": NCBI_EMAIL,
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        try:
            resp = _request_with_retry(requests.post, EFETCH_URL, data=params, timeout=60)
        except RuntimeError as e:
            print(f"[pubmed] batch {i}-{i + len(batch)} FAILED after retries, skipping "
                  f"this batch only: {e}")
            continue
        _rate_limit_delay()
        raw = resp.text
        chunks = [c.strip() for c in raw.split("\n\n\n") if c.strip()]
        all_chunks.extend(chunks)

    return all_chunks


def collect():
    if not NCBI_EMAIL:
        print("[pubmed] WARNING: NCBI_EMAIL is not set in your environment. "
              "NCBI asks for a contact email as etiquette -- see README.")

    target = QUOTAS["pubmed"]
    per_topic = max(1, target // len(SEARCH_TOPICS))
    all_abstracts = []

    for topic in SEARCH_TOPICS:
        if len(all_abstracts) >= target:
            break
        try:
            pmids = _esearch(topic, retmax=per_topic)
            abstracts = _efetch_abstracts(pmids)
        except Exception as e:
            # one topic failing entirely (e.g. esearch itself down) should
            # not lose the abstracts already gathered from prior topics
            print(f"[pubmed] topic '{topic}' FAILED, skipping this topic only: {e}")
            continue
        all_abstracts.extend(abstracts)
        print(f"[pubmed] '{topic}': +{len(abstracts)} (total {len(all_abstracts)})")

    all_abstracts = all_abstracts[:target]
    records = make_records(all_abstracts, MEDICAL_LABEL, source="pubmed", subtopic="abstract")
    return save_partial(records, "pubmed")


if __name__ == "__main__":
    collect()
