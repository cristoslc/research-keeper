---
title: "Twitter Thread Extraction — Pragmatic Path"
artifact: SPIKE-004
track: container
status: Active
author: cristos
created: 2026-04-05
last-updated: 2026-04-05
question: "Can we reliably extract Twitter/X threads and search for tweets using free, low-dependency strategies that fit rk's existing normalizer pipeline?"
gate: Pre-MVP
parent-initiative: INITIATIVE-001
risks-addressed:
  - "Twitter content inaccessible due to API lockdown"
  - "Third-party extraction services unreliable or discontinued"
evidence-pool: ""
---

# Twitter Thread Extraction — Pragmatic Path

## Summary

<!-- Final-pass section: populated when transitioning to Complete. -->

## Question

Can we reliably extract Twitter/X threads and search for tweets using free, low-dependency strategies that fit rk's existing normalizer pipeline?

Specifically:
1. Does ThreadReaderApp work as a proxy to convert threads into WebNormalizer-friendly HTML?
2. Does the Twitter syndication embed API work for single-tweet fallback?
3. Can Google `site:x.com` search serve as a practical Twitter search strategy?
4. What URL patterns do we need to detect `x.com` and `twitter.com` links in the identifier?

## Go / No-Go Criteria

| # | Criterion | Threshold | Measured by |
|---|-----------|-----------|-------------|
| 1 | ThreadReaderApp extraction rate | >= 70% of threads tested produce >= 50 words via WebNormalizer | Manual test of 10+ thread URLs across types (short, long, media-heavy, quote-tweets) |
| 2 | Single-tweet syndication fallback | >= 80% of single tweets return usable text content | Manual test of 10+ tweet URLs |
| 3 | Google site search coverage | Returns relevant results for 3 out of 5 test queries on known topics | Manual search test |
| 4 | Implementation effort | TwitterNormalizer fits within ~200 LOC and adds zero required new dependencies | Code estimation after strategy validation |

**Go** if criteria 1 and 4 pass and at least one of 2 or 3 passes.
**No-Go** if criterion 1 fails (ThreadReaderApp is the keystone strategy).

## Pivot Recommendation

If ThreadReaderApp proves unreliable:
- **Pivot A — Manual paste intake.** Add a `twitter` content type that accepts pre-copied thread text (user pastes the thread). No external fetching. Simple, zero-dependency, but high friction.
- **Pivot B — Twitter API Basic tier.** $100/month gets reliable thread retrieval and recent search. Only justified if Twitter is a primary research source for the operator.
- **Pivot C — Browser extension approach.** A lightweight browser extension or bookmarklet that captures thread HTML from the authenticated page and passes it to `rk add`. Sidesteps API issues entirely.

## Investigation Plan

### Track 1: ThreadReaderApp as primary extraction

**What to test:**
- Fetch `https://threadreaderapp.com/thread/{tweet_id}.html` for a variety of thread types
- Pass the fetched HTML through the existing `WebNormalizer`
- Measure: word count, metadata extraction quality (author, date, title), content completeness

**Thread types to cover:**
- Short thread (2-3 tweets)
- Long thread (10+ tweets)
- Thread with images/video embeds
- Thread with quote tweets
- Thread with polls
- Deleted or private thread (expected failure — document behavior)
- Very recent thread (< 1 hour old — ThreadReaderApp may not have indexed it)

**Key questions:**
- Does ThreadReaderApp require the thread to be "unrolled" first (via @threadreaderapp mention), or does it index threads proactively?
- What's the latency between tweet posting and ThreadReaderApp availability?
- Are there rate limits or anti-bot protections on ThreadReaderApp?

### Track 2: Twitter syndication/embed API fallback

**What to test:**
- `GET https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=...`
- `GET https://publish.twitter.com/oembed?url=https://x.com/user/status/{id}`
- Determine if either endpoint returns structured text content (not just embed HTML)
- Check if thread context (parent/child tweets) is accessible

**Key questions:**
- Does the syndication API require authentication?
- Is the response JSON with tweet text, or just an iframe embed?
- Can we follow reply chains to reconstruct threads?

### Track 3: Google site:x.com search

**What to test:**
- Query `site:x.com "knowledge graph"` and similar topic searches
- Assess result relevance and freshness
- Test whether rk's existing research/query system can issue these searches

**Key questions:**
- Does Google index tweet content reliably, or just profile pages?
- How fresh are the results (hours, days, weeks)?
- Can we extract tweet IDs from Google result URLs to feed into Track 1/2?

### Track 4: URL pattern detection

**What to implement in `identifier.py`:**

```python
# Patterns to add to URL_PATTERNS
r"(twitter\.com|x\.com)/\w+/status/": "twitter",
r"(twitter\.com|x\.com)/\w+$": "twitter",   # profile URLs (future)
r"threadreaderapp\.com/thread/": "twitter",   # already-unrolled threads
```

**Key questions:**
- Should `twitter` be its own content type or a subtype of `web`?
- How do we handle URLs with tracking parameters (`?s=20`, `?t=...`)?
- Do we need to normalize `twitter.com` URLs to `x.com` or vice versa?

## Findings

<!-- Populated during Active phase investigation. -->

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-05 | — | Initial creation |
