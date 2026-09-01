"""
Collect consumer-facing symptom/condition text from Mayo Clinic's public
"Diseases & Conditions" A-Z index.

IMPORTANT -- read before running:
- This checks robots.txt before scraping anything and will refuse to fetch
  disallowed paths, but robots.txt compliance is not the same as compliance
  with a site's Terms of Service. Mayo Clinic's ToS restricts commercial
  use/republishing of their content. This collector is intended for
  *personal, non-commercial research/training-data use only*.
- If BotMed will ever be a commercial or public-facing product, swap this
  source for something with an explicit open license (e.g. expand the
  MedQuAD/Wikipedia quotas instead) rather than shipping scraped copy.
- Quota is deliberately kept small (2,000) and requests are rate-limited
  to 1 req/sec to be a polite, low-impact crawler.
"""
import time
import requests
from urllib import robotparser
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from botmed_dataset_builder.config import MEDICAL_LABEL, QUOTAS
from botmed_dataset_builder.schema import make_records, save_partial

BASE_URL = "https://www.mayoclinic.org"
INDEX_URL = f"{BASE_URL}/diseases-conditions/index?letter=A"
HEADERS = {"User-Agent": "botmed-dataset-builder/0.1 (personal research project, non-commercial)"}
REQUEST_DELAY_SECONDS = 1.0

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _robots_allows(url: str) -> bool:
    rp = robotparser.RobotFileParser()
    rp.set_url(urljoin(url, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        return False  # if we can't read robots.txt, err conservative and skip
    return rp.can_fetch(HEADERS["User-Agent"], url)


def _get_condition_links(letter):
    index_url = f"{BASE_URL}/diseases-conditions/index?letter={letter}"
    if not _robots_allows(index_url):
        print(f"[webmd_mayo] robots.txt disallows {index_url}, skipping")
        return []
    resp = requests.get(index_url, headers=HEADERS, timeout=30)
    time.sleep(REQUEST_DELAY_SECONDS)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.select("a[href*='/diseases-conditions/']"):
        href = a.get("href", "")
        if "/symptoms-causes/" in href or "/diseases-conditions/" in href:
            links.append(urljoin(BASE_URL, href))
    return list(set(links))


def _extract_article_text(url):
    if not _robots_allows(url):
        return None
    resp = requests.get(url, headers=HEADERS, timeout=30)
    time.sleep(REQUEST_DELAY_SECONDS)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    # Mayo Clinic article body typically lives under a content/main region;
    # this selector may need adjusting if their markup changes.
    content = soup.select_one("div#main-content") or soup.select_one("article")
    if not content:
        return None
    paragraphs = [p.get_text(" ", strip=True) for p in content.find_all("p")]
    return " ".join(paragraphs)


def collect():
    target = QUOTAS["webmd_mayo"]
    all_links = []
    for letter in _ALPHABET:
        if len(all_links) >= target:
            break
        all_links.extend(_get_condition_links(letter))

    print(f"[webmd_mayo] found {len(all_links)} candidate condition pages")

    texts = []
    for url in all_links:
        if len(texts) >= target:
            break
        text = _extract_article_text(url)
        if text and len(text) > 100:
            texts.append(text)

    records = make_records(texts, MEDICAL_LABEL, source="webmd_mayo", subtopic="condition_page")
    return save_partial(records, "webmd_mayo")


if __name__ == "__main__":
    collect()
