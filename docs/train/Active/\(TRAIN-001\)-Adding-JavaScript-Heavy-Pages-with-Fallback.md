---
title: "Adding JavaScript-Heavy Pages with Fallback"
artifact: TRAIN-001
track: reference
status: Active
author: cristos
created: 2026-04-07
last-updated: 2026-04-07
type: how-to
domain: adding-sources
linked-artifacts:
  - SPEC-053
  - SPEC-054
  - SPEC-055
  - EPIC-010
---

# Adding JavaScript-Heavy Pages with Fallback

## When to Use This Guide

Use this workflow when `rk add` fails to fetch content from a website. This happens with:

- **JavaScript-rendered pages** — Content loads dynamically after page load
- **Anti-scraping measures** — Sites block automated fetchers like trafilatura
- **Login walls** — Content requires authentication
- **CAPTCHA challenges** — Sites require human verification

## Quick Reference

**Normal add (works for most pages):**
```bash
rk add "https://example.com/article"
```

**Fallback add (when normal fetch fails):**
```bash
# 1. Fetch with Playwright
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com/article')
    content = page.content()
    # Extract text or convert to markdown
    print(page.inner_text('body'))
    browser.close()
" > /tmp/content.md

# 2. Add with --content flag
rk add --content "$(cat /tmp/content.md)" --origin "https://example.com/article"
```

## Step-by-Step Workflow

### Step 1: Try Normal Add

```bash
rk add "https://javascript-heavy.com/article"
```

**Expected outcomes:**

✅ **Success:** Source added, sidecars generated — done!

❌ **Fetch failure:** Error output includes fallback hint:
```
Error adding 'https://javascript-heavy.com': Failed to fetch URL

Hint: If this page requires JavaScript rendering, try:
  rk add --content "<content>" --origin "https://javascript-heavy.com"

Use Playwright or Chrome to fetch the content first.
```

### Step 2: Fetch Content with Browser Automation

**Option A: Playwright (recommended)**

```bash
# Install if needed
uv add playwright

# Fetch and extract
python3 << 'EOF'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://javascript-heavy.com/article")
    
    # Wait for dynamic content
    page.wait_for_load_state("networkidle")
    
    # Extract as markdown or plain text
    # For markdown, you might need a converter like trafilatura
    content = page.inner_text("body")
    print(content)
    
    browser.close()
EOF
```

**Option B: Chrome DevTools Protocol**

```bash
# Using puppeteer via Node.js
node << 'EOF'
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('https://javascript-heavy.com/article');
  const content = await page.content();
  console.log(content);
  await browser.close();
})();
EOF
```

**Option C: Manual save**

If browser automation isn't available:
1. Open the page in your browser
2. Save as markdown or copy the text
3. Paste into `rk add --content`

### Step 3: Add to rk

**With content from command:**
```bash
rk add --content "$(python3 fetch_script.py)" --origin "https://javascript-heavy.com/article"
```

**With content from file:**
```bash
rk add --content "$(cat /tmp/article.md)" --origin "https://javascript-heavy.com/article"
```

**With stdin (for large content):**
```bash
python3 fetch_script.py | rk add --content - --origin "https://javascript-heavy.com/article"
```

### Step 4: Continue Normal Workflow

The fallback is transparent — after `rk add` succeeds:

```bash
# Agent fills tag sidecar
# (automatic if rk skill is installed)

# Resolve to finalize
rk resolve
```

## Troubleshooting

### "Command failed: --origin is required"

**Old behavior:** This error occurred when using `--content` without `--origin`.

**Current behavior:** `--origin` is now **optional**. If omitted, rk sets `origin: "inline"`.

**Best practice:** Always provide `--origin` for web sources so you can trace back to the original URL.

### Content has HTML tags

If your fetched content includes HTML markup:

```bash
# Use trafilatura to clean it
python3 << 'EOF'
import trafilatura
html = open('/tmp/raw.html').read()
text = trafilatura.extract(html)
print(text)
EOF
```

### Site blocks Playwright

Some sites detect and block headless browsers:

```bash
# Try with stealth mode
python3 << 'EOF'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()
    page.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
    page.goto("https://blocked-site.com")
    # ... rest of fetch
EOF
```

### Video content

For YouTube, Instagram, etc., use media-summary skill or yt-dlp:

```bash
# Media summary (if skill installed)
# See media-summary skill for details

# Or yt-dlp
yt-dlp --write-auto-sub --convert-subs srt -o "%(title)s.md" "https://youtube.com/watch?v=..."
rk add "/path/to/video.md"
```

## Examples

### Example 1: News Article (JavaScript-heavy)

```bash
# Normal add fails
rk add "https://nytimes.com/2024/ai-breakthrough"
# Error: Failed to fetch URL

# Fetch with Playwright
python3 << 'EOF' > /tmp/nytimes.md
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://nytimes.com/2024/ai-breakthrough")
    page.wait_for_load_state("networkidle")
    print(page.inner_text("article"))
    browser.close()
EOF

# Add to library
rk add --content "$(cat /tmp/nytimes.md)" --origin "https://nytimes.com/2024/ai-breakthrough"
```

### Example 2: Research Paper (PDF behind JavaScript)

```bash
# Site requires JavaScript to show PDF
python3 << 'EOF'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://arxiv.org/abs/1234.56789")
    page.wait_for_load_state("networkidle")
    # Extract abstract and metadata
    title = page.inner_text("h1.title")
    abstract = page.inner_text(".abstract")
    print(f"# {title}\n\n{abstract}")
    browser.close()
EOF
```

### Example 3: Interactive Dashboard

```bash
# Dashboard loads data dynamically
python3 << 'EOF'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://ourworldindata.org/co2-emissions")
    page.wait_for_load_state("networkidle")
    
    # Wait for charts to render
    page.wait_for_selector(".chart-container")
    
    # Screenshot + data extraction
    page.screenshot(path="chart.png")
    data = page.inner_text(".chart-data")
    print(f"![Chart](chart.png)\n\n{data}")
    browser.close()
EOF

rk add --content "$(python3 fetch_dashboard.py)" --origin "https://ourworldindata.org/co2-emissions"
```

## Related Documentation

- **SPEC-053** — Fallback mechanism design and CLI hints
- **SPEC-054** — `--content` flag implementation details
- **SPEC-055** — rk skill fallback handling
- **EPIC-010** — Complete fallback workflow epic

## Common Mistakes

❌ **Forgetting `--origin`:** While now optional, omitting it loses the source URL for future reference.

❌ **Adding raw HTML:** Always extract text or convert to markdown first — raw HTML clutters your library.

❌ **Skipping the wait:** JavaScript pages need time to load. Use `page.wait_for_load_state("networkidle")`.

❌ **Not checking the fetch:** Verify the fetched content looks right before adding to rk.

## Tips

- **Save fetch scripts:** Keep reusable fetch scripts for sites you query often
- **Batch similar pages:** Fetch multiple pages in one browser session to amortize startup cost
- **Use stdin for large content:** `--content -` avoids shell escaping issues
- **Check rk skill:** With rk skill installed, fallback is automatic — just say "add this" and the agent handles it
