---
source-id: "markdown-kb-client-search"
title: "Adding Search to Your Markdown Knowledge Base Without a Backend"
type: web
url: "https://dev.to/hexshift/adding-search-to-your-markdown-knowledge-base-without-a-backend-35pc"
fetched: 2026-03-30T18:04:37Z
hash: "c858be1b13222da2b2cd8f0bd83b71f702857872c54f11764909c0fdde4336b4"
---

# Adding Search to Your Markdown Knowledge Base Without a Backend

HexShift -- Posted on May 6, 2025

A fast, searchable knowledge base doesn't need a database or heavy frameworks. In this guide, we'll show how to add **client-side search** to your static Markdown-based system using **JavaScript** and **Tailwind CSS** -- no backend required.

## Why Client-Side Search?

- Instant results
- Works offline
- No server dependencies

This method is ideal for lightweight documentation or personal knowledge bases hosted on platforms like GitHub Pages or Netlify.

## Step 1: Structure Your Markdown Files

Organize your `.md` files inside a `docs/` directory. Example:

```
docs/
├── getting-started.md
├── installation.md
├── faq.md
└── features.md
```

Each file should begin with a clear heading and meaningful content for best results.

## Step 2: Index Markdown Files in JavaScript

Create a JSON index of your docs (manually or with a build tool). Here's a simple example:

```javascript
const docsIndex = [
  { title: "Getting Started", path: "docs/getting-started.md" },
  { title: "Installation", path: "docs/installation.md" },
  { title: "FAQ", path: "docs/faq.md" },
  { title: "Features", path: "docs/features.md" }
];
```

You'll loop through these to preload content and search through it.

## Step 3: Build a Search Interface with Tailwind

```html
<input type="text" id="search-box"
  class="w-full p-3 border rounded mb-4"
  placeholder="Search the knowledge base...">

<ul id="search-results" class="space-y-2"></ul>
```

## Step 4: Load and Search Markdown Content

Use `fetch()` and `marked` to load and index Markdown content. Then filter it in the browser.

```javascript
const resultsList = document.getElementById("search-results");
const searchBox = document.getElementById("search-box");
let indexedDocs = [];

async function loadDocs() {
  for (const doc of docsIndex) {
    const res = await fetch(doc.path);
    const text = await res.text();
    indexedDocs.push({
      title: doc.title,
      path: doc.path,
      content: text.toLowerCase()
    });
  }
}

function searchDocs(term) {
  resultsList.innerHTML = "";
  if (!term) return;

  const results = indexedDocs.filter(doc =>
    doc.content.includes(term.toLowerCase())
  );

  results.forEach(result => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${result.path}" class="text-blue-600 underline">${result.title}</a>`;
    resultsList.appendChild(li);
  });
}

searchBox.addEventListener("input", (e) => {
  searchDocs(e.target.value);
});

loadDocs();
```

## Step 5: Style with Tailwind

Enhance your UI with Tailwind utilities -- hover states, focus rings, spacing, and typography -- for a professional look.

```html
<a href="#" class="block px-4 py-2 bg-gray-100 hover:bg-blue-100 rounded">
  Article Title
</a>
```

## Summary

By indexing Markdown files and using a bit of client-side JavaScript, you can build a fast, user-friendly search feature for your knowledge base -- no backend required.

This approach keeps your stack simple and your docs blazing fast.
