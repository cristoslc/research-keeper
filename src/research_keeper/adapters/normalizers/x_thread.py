# src/research_keeper/adapters/normalizers/x_thread.py
"""Normalize X/Twitter thread URLs to structured markdown via the fxtwitter API.

Ported from media-summary/scripts/fetch_x_thread.py (cristoslc/media-summary).
No new runtime dependencies — pure stdlib.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime

from research_keeper.ports.normalizer import NormalizationError

logger = logging.getLogger(__name__)

THREAD_API = "https://api.fxtwitter.com/2/thread/{id}"
UA = {"User-Agent": "research-keeper/1.0"}
MAX_CITATIONS = 25

CITED_URL_RE = re.compile(
    r"https?://(?:x|twitter|fxtwitter|fixupx)\.com/\w+/status/(\d+)",
    re.IGNORECASE,
)

X_URL_RE = re.compile(
    r"https?://(?:x|twitter|fxtwitter|fixupx)\.com/\w+/status/(\d+)",
    re.IGNORECASE,
)


def _extract_tweet_id(raw: str) -> str:
    m = re.search(r"/status/(\d+)", raw)
    if m:
        return m.group(1)
    stripped = raw.strip()
    if stripped.isdigit():
        return stripped
    raise NormalizationError(
        f"Could not extract tweet ID from: {raw!r}",
        stage="x-thread-normalize",
    )


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _fetch_thread(tweet_id: str) -> dict:
    return _http_get_json(THREAD_API.format(id=tweet_id))


def _non_x_external_links(post: dict) -> list[dict]:
    facets = (post.get("raw_text") or {}).get("facets") or []
    out = []
    for f in facets:
        if f.get("type") != "url":
            continue
        repl = f.get("replacement")
        if not repl or re.match(
            r"https?://(?:x|twitter|fxtwitter|fixupx)\.com/", repl
        ):
            continue
        out.append({"url": repl, "display": f.get("display")})
    return out


def _fetch_cited(tweet_id: str) -> dict | None:
    """Fetch a cited tweet and its self-reply chain via /2/thread/.

    Uses the thread endpoint deliberately: authors commonly post a teaser then
    self-reply with the actual article URL. /2/thread/ walks that chain.
    """
    try:
        data = _http_get_json(THREAD_API.format(id=tweet_id))
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None
    if data.get("code") != 200:
        return None
    thread = data.get("thread") or []
    target = next(
        (p for p in thread if str(p.get("id")) == str(tweet_id)), None
    )
    if not target:
        return None

    target_author_id = (target.get("author") or {}).get("id")
    frontier = {str(tweet_id)}
    self_replies = []
    for p in thread:
        pid = str(p.get("id"))
        if pid in frontier:
            continue
        parent = (p.get("replying_to") or {}).get("status")
        if parent in frontier and (p.get("author") or {}).get("id") == target_author_id:
            self_replies.append(p)
            frontier.add(pid)

    external_links = _non_x_external_links(target)
    for r in self_replies:
        external_links.extend(_non_x_external_links(r))

    a = target.get("author") or {}
    return {
        "id": target.get("id"),
        "url": target.get("url"),
        "text": target.get("text"),
        "created_at": target.get("created_at"),
        "author_handle": a.get("screen_name"),
        "author_website": (a.get("website") or {}).get("url"),
        "external_links": external_links,
        "self_replies": [
            {"url": r.get("url"), "text": r.get("text")} for r in self_replies
        ],
    }


def _collect_cited_ids(thread: list[dict]) -> list[str]:
    own = {str(p.get("id")) for p in thread if p.get("id")}
    seen: set[str] = set()
    ordered: list[str] = []
    for p in thread:
        for tid in CITED_URL_RE.findall(p.get("text", "") or ""):
            if tid in own or tid in seen:
                continue
            seen.add(tid)
            ordered.append(tid)
    return ordered[:MAX_CITATIONS]


def _render_markdown(
    thread: list[dict], cited: dict[str, dict], title: str, author: dict
) -> str:
    handle = author.get("screen_name", "unknown")
    name = author.get("name", handle)
    created = _parse_date(thread[0].get("created_at") or "") if thread else ""
    total = len(thread)

    lines: list[str] = [
        f"# {title}",
        "",
        f"**Author:** {name} (@{handle})",
    ]
    if created:
        lines.append(f"**Posted:** {created}")
    lines += [f"**Posts:** {total}", "", "---", ""]

    for i, p in enumerate(thread, 1):
        text = (p.get("text") or "").strip()
        lines.append(f"[{i}/{total}] {text}")

        for tid in CITED_URL_RE.findall(text):
            c = cited.get(tid)
            if not c:
                continue
            quoted = (c.get("text") or "").strip().replace("\n", "\n> ")
            lines.append("")
            cited_date = _parse_date(c.get("created_at") or "") or c.get("created_at", "")
            lines.append(
                f"> **@{c.get('author_handle', '?')} ({cited_date}):**"
                f" {quoted}"
            )
            lines.append(f"> — {c.get('url', '')}")
            ext = c.get("external_links") or []
            if ext:
                links = ", ".join(e["url"] for e in ext if e.get("url"))
                lines.append(f"> external: {links}")
            elif c.get("author_website"):
                lines.append(f"> author site: {c['author_website']}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _parse_date(created_at: str) -> str:
    """Parse fxtwitter's date format to ISO YYYY-MM-DD.

    fxtwitter returns Twitter's legacy format: 'Sat Nov 11 00:48:08 +0000 2023'.
    Falls back to empty string if unparseable.
    """
    if not created_at:
        return ""
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S +0000 %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # If it's already ISO-like, take first 10 chars
        if len(created_at) >= 10 and created_at[4] == "-":
            return created_at[:10]
        return ""


def _make_title(root: dict) -> str:
    text = re.sub(r"^(@\w+\s+)+", "", root.get("text", "")).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > 80:
        cut = text[:80]
        last_space = cut.rfind(" ")
        text = cut[:last_space] if last_space > 40 else cut
    handle = (root.get("author") or {}).get("screen_name", "unknown")
    return text or f"Thread by @{handle}"


class XThreadNormalizer:
    """Normalize X/Twitter thread URLs to structured markdown."""

    def normalize(self, raw: str | bytes, metadata: dict, take_screenshot: bool = False) -> tuple[str, dict, bytes | None]:
        url = raw if isinstance(raw, str) else raw.decode("utf-8")
        url = url.strip()

        tweet_id = _extract_tweet_id(url)

        try:
            data = _fetch_thread(tweet_id)
        except urllib.error.HTTPError as e:
            raise NormalizationError(
                f"fxtwitter HTTP {e.code} for tweet {tweet_id}: {e.reason}",
                stage="x-thread-normalize",
            ) from e
        except urllib.error.URLError as e:
            raise NormalizationError(
                f"fxtwitter unreachable: {e.reason}",
                stage="x-thread-normalize",
            ) from e

        if data.get("code") != 200:
            raise NormalizationError(
                f"fxtwitter returned {data.get('code')}: {data.get('message')}",
                stage="x-thread-normalize",
            )

        thread = data.get("thread") or []
        if not thread:
            raise NormalizationError(
                "fxtwitter returned an empty thread",
                stage="x-thread-normalize",
            )

        root = thread[0]
        root_text = root.get("text", "") or ""

        # Partial thread: opener returned but chain not resolved
        if len(thread) == 1 and re.search(r"(1/\d|🧵)", root_text):
            raise NormalizationError(
                "Thread fetch incomplete: fxtwitter returned 1 post for a thread "
                "opener. The public deployment may lack an account proxy. "
                "Try again later, or add thread text manually via: rk add --note",
                stage="x-thread-normalize",
            )

        cited_ids = _collect_cited_ids(thread)
        cited: dict[str, dict] = {}
        for tid in cited_ids:
            c = _fetch_cited(tid)
            if c is not None:
                cited[tid] = c

        title = _make_title(root)
        author = root.get("author") or {}
        content = _render_markdown(thread, cited, title, author)

        name = author.get("name", "")
        handle = author.get("screen_name", "")
        created_at = root.get("created_at", "") or ""
        source_url = root.get("url") or url

        extracted_meta: dict = {
            "title": title,
            "author": f"{name} (@{handle})" if name else f"@{handle}",
            "source_url": source_url,
        }
        if created_at:
            iso_date = _parse_date(created_at)
            if iso_date:
                extracted_meta["published"] = iso_date

        return content, extracted_meta, None
