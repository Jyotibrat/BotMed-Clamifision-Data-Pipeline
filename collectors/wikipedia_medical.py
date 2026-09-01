"""
Collect Wikipedia article text from medical categories via the MediaWiki API.
Docs: https://www.mediawiki.org/wiki/API:Main_page

We do a shallow breadth-first walk of a handful of seed categories
(diseases, symptoms, medications, etc.) to gather page titles, then fetch
the plain-text extract of each page.

NOTE ON RATE LIMITING: Wikimedia's anonymous-API rate limiting is fairly
aggressive, especially for a User-Agent that doesn't meet their policy
(https://meta.wikimedia.org/wiki/User-Agent_policy -- requires contact info).
Set WIKIPEDIA_CONTACT in .env to reduce throttling. If you're still hitting
constant 429s, it may be an IP-level cooldown from a prior run -- waiting
roughly an hour before retrying usually clears it.
"""
import time
import requests
from botmed_dataset_builder.config import MEDICAL_LABEL, QUOTAS, WIKIPEDIA_CONTACT
from botmed_dataset_builder.schema import make_records, save_partial

API_URL = "https://en.wikipedia.org/w/api.php"

_contact = WIKIPEDIA_CONTACT or "no-contact-set-see-README"
HEADERS = {
    "User-Agent": f"botmed-dataset-builder/0.1 ({_contact}) research/educational use"
}

SEED_CATEGORIES = [
    "Category:Diseases and disorders",
    "Category:Symptoms and signs",
    "Category:Medical specialties",
    "Category:Drugs",
    "Category:Medical treatments",
    "Category:Infectious diseases",
    "Category:Mental and behavioural disorders",
]

MAX_DEPTH = 1  # how many levels of subcategories to follow from each seed


def _request_with_retry(params, max_retries=4, base_delay=1.0):
    """GET with exponential backoff on 429, respecting Retry-After when present.
    max_retries kept modest -- if Wikipedia keeps saying "wait 45s" over and
    over, that's telling us something (likely an IP-level cooldown), and
    hammering retries harder won't fix it. Better to fail this batch fast
    and let the caller move on / the run finish sooner.
    """
    delay = base_delay
    for attempt in range(max_retries):
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", delay))
            print(f"[wikipedia] 429 rate limited, waiting {wait:.1f}s "
                  f"(attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"[wikipedia] exceeded {max_retries} retries for params={params}")


def _get_category_members(category, cmtype="page|subcat", limit=200):
    params = {
        "action": "query", "list": "categorymembers", "cmtitle": category,
        "cmtype": cmtype, "cmlimit": limit, "format": "json",
    }
    try:
        resp = _request_with_retry(params)
    except RuntimeError as e:
        print(f"[wikipedia] category '{category}' FAILED, skipping: {e}")
        return []
    time.sleep(1.0)
    return resp.json().get("query", {}).get("categorymembers", [])


def _collect_titles(target_count):
    titles = set()
    frontier = list(SEED_CATEGORIES)
    depth = 0

    while frontier and len(titles) < target_count and depth <= MAX_DEPTH:
        next_frontier = []
        for cat in frontier:
            if len(titles) >= target_count:
                break
            members = _get_category_members(cat)
            for m in members:
                if m["ns"] == 0:  # ns 0 = article
                    titles.add(m["title"])
                elif m["ns"] == 14:  # ns 14 = subcategory
                    next_frontier.append(m["title"])
        frontier = next_frontier
        depth += 1

    return list(titles)[:target_count]


def _fetch_extracts(titles, batch_size=20):
    """batch_size=20 (up from 10) roughly halves the number of requests
    needed, which matters a lot when each request risks a long 429 wait.
    Each batch is isolated: a batch that fails after retries is skipped,
    not fatal to everything already collected.
    """
    texts = []
    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        params = {
            "action": "query", "prop": "extracts", "explaintext": 1,
            "titles": "|".join(batch), "format": "json",
        }
        try:
            resp = _request_with_retry(params)
        except RuntimeError as e:
            print(f"[wikipedia] extract batch {i}-{i + len(batch)} FAILED, skipping: {e}")
            continue
        time.sleep(1.0)
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            extract = page.get("extract", "")
            if extract:
                texts.append(extract)
    return texts


def collect():
    if not WIKIPEDIA_CONTACT:
        print("[wikipedia_medical] WARNING: WIKIPEDIA_CONTACT (or NCBI_EMAIL) not set. "
              "Wikimedia throttles non-compliant User-Agents harder -- see README.")

    target = QUOTAS["wikipedia_medical"]
    titles = _collect_titles(target)
    print(f"[wikipedia_medical] found {len(titles)} candidate article titles")
    texts = _fetch_extracts(titles)
    texts = texts[:target]
    records = make_records(texts, MEDICAL_LABEL, source="wikipedia_medical", subtopic="article")
    return save_partial(records, "wikipedia_medical")


if __name__ == "__main__":
    collect()
