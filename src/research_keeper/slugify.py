from __future__ import annotations
import re
import unicodedata
from urllib.parse import urlparse

def slugify(text: str, max_length: int = 80) -> str:
    if not text.strip():
        return "untitled"
    if text.startswith(("http://", "https://")):
        path = urlparse(text).path.rstrip("/")
        if path:
            text = path.rsplit("/", 1)[-1]
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"['\u2018\u2019]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")
    return text or "untitled"
