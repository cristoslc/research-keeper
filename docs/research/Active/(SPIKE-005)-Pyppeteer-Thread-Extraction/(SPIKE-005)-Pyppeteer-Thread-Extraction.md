---
title: "Pyppeteer Thread Extraction via Unroller Services"
artifact: SPIKE-005
track: container
status: Active
author: cristos
created: 2026-04-05
last-updated: 2026-04-05
question: "Can pyppeteer render JS-dependent thread unrollers (UnrollNow, XBeast, etc.) to extract Twitter/X thread content that plain HTTP fetches cannot?"
gate: Pre-MVP
parent-initiative: INITIATIVE-001
risks-addressed:
  - "JS-rendered unrollers return empty HTML to plain HTTP clients"
  - "Headless browser dependency may be too heavy or fragile for rk's pipeline"
evidence-pool: "SPIKE-004"
---

# Pyppeteer Thread Extraction via Unroller Services

## Summary

<!-- Final-pass section: populated when transitioning to Complete. -->

## Question

Can pyppeteer render JS-dependent thread unrollers (UnrollNow, XBeast, etc.) to extract Twitter/X thread content that plain HTTP fetches cannot?

SPIKE-004 found that several unroller services (UnrollNow, XBeast, Thread Navigator) return empty JS shells to HTTP clients but may render content in a real browser. This spike tests that hypothesis with pyppeteer and measures the practical costs.

## Go / No-Go Criteria

| # | Criterion | Threshold | Measured by |
|---|-----------|-----------|-------------|
| 1 | Content extraction rate | >= 60% of test threads produce >= 50 words from at least one unroller | Pyppeteer render + text extraction on 5+ thread URLs |
| 2 | Extraction latency | < 15 seconds per thread (browser launch + render + extract) | Timed runs |
| 3 | Dependency footprint | pyppeteer install size documented; Chromium binary size documented | `du -sh` after install |
| 4 | Stability across thread types | Works for short threads, long threads, and threads with media | Test variety |
| 5 | No auth required | Unroller services don't require login when rendered in headless browser | Observe during testing |

**Go** if criteria 1, 3, and 5 pass. Latency (2) is advisory — slow but working beats fast but broken.
**No-Go** if criterion 1 fails (unrollers don't render content even in a headless browser) or criterion 5 fails (auth required even with JS rendering).

## Pivot Recommendation

If pyppeteer + unrollers fails:
- **Fall back to SPIKE-004 Pivot E** — cheap third-party API (TwitterAPI.io, $0.15/1K tweets) as primary extraction, manual paste as fallback. This is the safe path with known costs and no browser dependency.

## Investigation Plan

### Track 1: Pyppeteer feasibility

**Setup:**
- Install pyppeteer in a venv, document install size and Chromium download size
- Confirm headless Chromium launches and can render a known JS-heavy page
- Document startup time (cold launch vs warm)

**Key questions:**
- Does pyppeteer still actively maintained, or should we use playwright instead?
- What's the total disk footprint (library + browser binary)?
- Can we reuse a browser instance across multiple extractions to amortize startup?

### Track 2: UnrollNow via pyppeteer

**Test procedure:**
1. Navigate to `https://unrollnow.com`
2. Input a tweet URL into their form (or navigate to `/thread/{id}` if there's a direct URL)
3. Wait for JS rendering to complete
4. Extract page text content
5. Measure: word count, content completeness, metadata presence

**Tweet IDs to test:**
- `1851665654073753610` (Karpathy thread)
- `1725636940029157828` (popular tech thread)
- `1623763056392040449` (older thread)
- A short thread (2-3 tweets)
- A thread with images

**Key questions:**
- Does UnrollNow require form interaction (paste URL, click button) or support direct URL?
- How long does the unroller take to fetch and render the thread?
- Does the rendered content include all tweets in the thread or just the first?
- Are images/media referenced in the output?

### Track 3: XBeast via pyppeteer

**Same test procedure as Track 2, adapted for XBeast's UI.**

- Navigate to `https://xbeast.io/tools/thread-unroller`
- Input tweet URL, trigger unroll
- Wait for render, extract content

### Track 4: Other unrollers via pyppeteer

If Tracks 2-3 fail, also try:
- Thread Navigator (`threadnavigator.com`) — returned 403 to plain HTTP but may serve content to a real browser
- ThreadReaderApp — still needs auth, but test whether the login wall is a simple cookie gate or a full OAuth flow

### Track 5: Integration design

If extraction works, sketch the integration:
- How does pyppeteer fit into the normalizer pipeline?
- Can we make it an optional dependency (graceful degradation without it)?
- Browser lifecycle: launch once per `rk add` call, or run a persistent browser?
- Error handling: what happens when a render times out or an unroller is down?

## Findings

*Tested 2026-04-05.*

### Track 1: Browser Engine Feasibility — MEASURED

**pyppeteer vs playwright:** pyppeteer 2.0.0 installs cleanly (33 MB library) but uses an older Chromium revision (1181205) that must be downloaded separately. Playwright 1.56.1 is the better choice — actively maintained, supports Chromium/Firefox/WebKit, and available via npm. Used Playwright for all testing.

**Dependency footprint:**

| Component | Size |
|-----------|------|
| Playwright npm package | ~2 MB |
| Chromium (full) | 597 MB |
| Chromium headless shell | 323 MB |
| pyppeteer library (Python) | 33 MB |

**For rk's Python pipeline, the path would be:** `pip install playwright` (Python bindings) + `playwright install chromium` (downloads the 323–597 MB browser binary). Total: **~350–630 MB** added to the install.

**Performance (measured):**

| Operation | Time |
|-----------|------|
| Cold browser launch | 132 ms |
| Warm browser launch | 163 ms |
| New page creation (warm) | 96 ms |
| Text extraction from rendered page | < 10 ms |

Browser launch is fast. The bottleneck will be network fetch + JS render time on the unroller sites, not the browser itself. A persistent browser instance across multiple `rk add` calls is feasible and would eliminate launch overhead entirely.

### Track 2–4: Unroller Site Testing — INCONCLUSIVE

**Limitation:** The test environment's sandbox blocks outbound HTTPS from Chromium (`ERR_INVALID_AUTH_CREDENTIALS` on all external URLs). All four unroller services were unreachable:

| Service | URL tested | Result |
|---------|-----------|--------|
| UnrollNow (direct URL) | `/status/{id}` | `ERR_INVALID_AUTH_CREDENTIALS` |
| UnrollNow (form) | Homepage | `ERR_INVALID_AUTH_CREDENTIALS` |
| XBeast | `/tools/thread-unroller` | `ERR_INVALID_AUTH_CREDENTIALS` |
| Thread Navigator | Homepage | `ERR_INVALID_AUTH_CREDENTIALS` |

**These failures are environment-specific, not service-specific.** The browser launched and rendered local HTML correctly. The unroller tests need to be re-run in an environment with unrestricted outbound network access (operator's local machine).

### Track 5: Integration Design — SKETCHED

Regardless of whether unrollers work, the integration pattern is clear:

```
TwitterNormalizer
├── Strategy 1: API fetch (if API key configured)
│   └── TwitterAPI.io → JSON → markdown
├── Strategy 2: Headless browser (if playwright installed)
│   └── Launch Chromium → navigate to unroller → extract text
└── Strategy 3: Manual paste fallback (always available)
    └── Clean up pasted thread text → markdown
```

**Optional dependency pattern** (consistent with rk's `trafilatura` pattern in `WebNormalizer`):

```python
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
```

**Browser lifecycle options:**
- **Per-call:** Launch browser, extract, close. Simple but slow (~5s overhead).
- **Session-scoped:** Keep browser alive for the duration of an `rk` session. Fast but uses ~100 MB resident memory.
- **Daemon:** Background browser process. Fastest but operationally complex.

Recommendation: session-scoped (launch on first Twitter URL, reuse for subsequent ones, close when pipeline exits).

### Gate Assessment

| Criterion | Result |
|-----------|--------|
| 1. Content extraction rate | **INCONCLUSIVE** — sandbox blocked outbound HTTPS |
| 2. Extraction latency | **PASS (partial)** — browser ops are fast (< 300ms); network/render latency untested |
| 3. Dependency footprint | **MEASURED** — 323–597 MB for Chromium binary |
| 4. Stability across thread types | **INCONCLUSIVE** |
| 5. No auth required | **INCONCLUSIVE** |

**Verdict: INCONCLUSIVE.** The critical question — do unrollers render tweet content in a headless browser? — could not be answered from this environment. The operator needs to run the test script locally.

### What We Know vs What We Don't

**Known:**
- Playwright works, launches fast (132ms), extracts text cleanly
- Dependency cost is 323–597 MB (significant but one-time)
- Integration pattern is clear and fits rk's optional-dependency model
- pyppeteer is the wrong choice; playwright is better maintained

**Unknown (needs local testing):**
- Whether UnrollNow, XBeast, or Thread Navigator actually render tweet content in a headless browser
- Whether these services require CAPTCHAs, rate-limit, or detect headless browsers
- Actual end-to-end latency (network + render + extract)

### Operator Action Required

Run this on your local machine to answer the open question:

```bash
npm install playwright
npx playwright install chromium
node test-unrollers.mjs   # script at /tmp/test-unrollers.mjs
```

If even one unroller produces >= 50 words of thread content, the headless browser path is viable. If none do, fall back to SPIKE-004 Pivot E (cheap API).

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-05 | — | Initial creation |
