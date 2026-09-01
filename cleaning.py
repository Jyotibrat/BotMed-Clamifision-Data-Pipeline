import re
from botmed_dataset_builder.config import MIN_TEXT_LENGTH_CHARS, MAX_TEXT_LENGTH_CHARS

_URL_RE = re.compile(r"http\S+|www\.\S+")
_HTML_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")  # [text](url) -> text
_REDDIT_QUOTE_RE = re.compile(r"^&gt;.*$", re.MULTILINE)     # strip quoted reply lines
_MULTI_UNDERSCORE_RE = re.compile(r"_{2,}")


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    text = _HTML_RE.sub("", text)
    text = _REDDIT_QUOTE_RE.sub("", text)
    text = _MULTI_UNDERSCORE_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def is_valid_length(text: str) -> bool:
    return MIN_TEXT_LENGTH_CHARS <= len(text) <= MAX_TEXT_LENGTH_CHARS * 4  # generous upper bound pre-truncation


def truncate(text: str, max_chars: int = MAX_TEXT_LENGTH_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    # truncate on a sentence boundary where possible, else hard cut
    cut = text[:max_chars]
    last_period = cut.rfind(". ")
    return cut[: last_period + 1] if last_period > max_chars * 0.5 else cut


def clean_and_filter(records: list[dict]) -> list[dict]:
    """Apply clean_text + length filtering + truncation to a list of schema records."""
    out = []
    for r in records:
        t = clean_text(r["text"])
        if not is_valid_length(t):
            continue
        r = dict(r)
        r["text"] = truncate(t)
        out.append(r)
    return out
