"""
Two-pass deduplication:
1. Exact dedup on normalized (lowercased, whitespace-collapsed) text.
2. Near-dup detection using a hash of the first 200 normalized characters --
   catches cases like the same WebMD page scraped twice, or a Wikipedia
   lead paragraph that's byte-identical to a MedQuAD answer copied from it.

This is intentionally lightweight (no MinHash/LSH) since 50k rows is small
enough that an O(n) hash-bucket pass is plenty. If you scale to 500k+ rows
and need fuzzier near-dup detection, look at the `datasketch` library.
"""
import hashlib
import re

_normalize_re = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _normalize_re.sub(" ", text.lower().strip())


def _prefix_hash(text: str, prefix_chars: int = 200) -> str:
    norm = _normalize(text)[:prefix_chars]
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


def deduplicate(records: list[dict]) -> list[dict]:
    seen_exact = set()
    seen_prefix = set()
    out = []
    exact_dupes = 0
    near_dupes = 0

    for r in records:
        norm = _normalize(r["text"])
        exact_key = hashlib.md5(norm.encode("utf-8")).hexdigest()
        if exact_key in seen_exact:
            exact_dupes += 1
            continue

        prefix_key = _prefix_hash(r["text"])
        if prefix_key in seen_prefix:
            near_dupes += 1
            continue

        seen_exact.add(exact_key)
        seen_prefix.add(prefix_key)
        out.append(r)

    print(f"Dedup: removed {exact_dupes} exact + {near_dupes} near-duplicate rows "
          f"({len(records)} -> {len(out)})")
    return out
