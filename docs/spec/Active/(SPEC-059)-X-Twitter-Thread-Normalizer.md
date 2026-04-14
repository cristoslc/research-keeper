---
title: "X/Twitter Thread Normalizer"
artifact: SPEC-059
track: implementable
status: Active
author: Cristos L-C
created: 2026-04-13
last-updated: 2026-04-13
priority-weight: high
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts:
  - SPEC-048
depends-on-artifacts:
  - SPEC-048
addresses: []
evidence-pool: "media-summary scripts/fetch_x_thread.py"
source-issue: ""
swain-do: required
---

# X/Twitter Thread Normalizer

## Problem Statement

`rk add` has no handler for X/Twitter URLs. Passing `https://x.com/user/status/123` falls through to the web normalizer, which fetches the HTML redirect page and produces no useful transcript. Multi-tweet threads — a primary format for technical writing on X — cannot be ingested.

The fxtwitter `/2/thread/{id}` JSON API provides structured thread data (full text, author info, self-reply chain, cited posts) with zero authentication and zero new runtime dependencies. The `media-summary` skill already uses this API successfully via `fetch_x_thread.py`.

## Desired Outcomes

X/Twitter thread and single-post URLs are a first-class input to `rk add`. The normalizer produces a structured markdown document capturing the full thread transcript, author metadata, and inline citations.

## External Behavior

### URL detection

All of the following URL forms are recognized as `x-thread` content type:
```
https://x.com/user/status/123456789
https://twitter.com/user/status/123456789
https://fxtwitter.com/user/status/123456789
https://fixupx.com/user/status/123456789
```

### Output format

`rk add https://x.com/user/status/123` produces a `source.md`:

```markdown
# Thread by @username — Title guess from first tweet

**Author:** Full Name (@username)
**Posted:** 2026-03-15
**Posts:** 7

---

[1/7] First tweet text here.

[2/7] Second tweet with a citation:

> **@otheruser (2026-02-01):** Cited tweet content here.
> — https://x.com/otheruser/status/987

[3/7] ...
```

Manifest fields set:
- `title` — first 80 chars of thread opener, or "Thread by @handle"
- `author` — `Name (@handle)`
- `source-url` — canonical x.com URL of the thread root
- `published` — ISO date from fxtwitter `created_at`
- `snapshot-date` — date of ingestion

### Edge case: partial thread (single post returned)

When the fxtwitter deployment returns only 1 post for a URL that looks like a thread opener (contains "1/" or "🧵"), the normalizer raises `NormalizationError` with a clear message:

```
[x-thread-normalize] Thread fetch incomplete: fxtwitter returned 1 post for a
thread opener. The public deployment may lack an account proxy. Try again later,
or add the thread text manually via rk add --note.
```

This triggers the normalization-failure recovery flow (normalize.j2 sidecar) introduced in the normalization feature, so the operator can paste the thread text and resolve it manually.

### Single posts

Single tweets (not thread openers) are normalized as-is — 1 post is valid output.

## Implementation

### Files changed

| File | Change |
|---|---|
| `adapters/normalizers/identifier.py` | Add x.com/twitter.com/fxtwitter.com/fixupx.com patterns → `"x-thread"` |
| `adapters/normalizers/x_thread.py` | New: `XThreadNormalizer` class |
| `cli.py` | Register `XThreadNormalizer` for `"x-thread"` in `rk add` and `rk normalize` |

### No new dependencies

Pure stdlib (`urllib`, `json`, `re`). No package additions to `pyproject.toml`.

### `XThreadNormalizer` interface

```python
class XThreadNormalizer:
    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        """raw is an X/Twitter URL string."""
```

Core logic ported directly from `media-summary/scripts/fetch_x_thread.py`:
- `_extract_tweet_id` — parse status ID from URL or bare ID
- `_http_get_json` — urllib GET with `User-Agent: research-keeper/1.0`
- `_fetch_thread` — call `api.fxtwitter.com/2/thread/{id}`
- `_collect_cited_ids` — find cited tweet IDs in thread text
- `_fetch_cited` — fetch each cited tweet's thread for inline context
- `_render_markdown` — stitch thread posts + blockquote citations into markdown

### Acceptance criteria

- [ ] `rk add https://x.com/user/status/ID` produces `source.md` with thread transcript
- [ ] Single-post tweets (non-thread-opener) produce a 1-post transcript without error
- [ ] Thread-opener with 1 post returned raises `NormalizationError` (triggers normalize.j2)
- [ ] Author, published date, source-url in manifest
- [ ] All four URL variants (x.com, twitter.com, fxtwitter.com, fixupx.com) recognized
- [ ] No new pyproject.toml dependencies

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-13 | -- | Initial creation |
