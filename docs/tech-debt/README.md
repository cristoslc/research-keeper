# Tech debt

Pre-existing type errors, lint violations, and other debt that is too large or risky to fix inline. Minor single-file errors are fixed in their own `chore:` commit instead of being logged here.

## Entry format

One file per item, named `YYYY-MM-DD-{slug}.md`, with: what the problem is, where it lives (files and diagnostics, quoted verbatim), why it was not fixed inline, and a suggested fix.

## Lifecycle

Delete the entry in the commit that fixes the problem. The full policy is in `~/.agents/agents-md-detail/lsp-errors.md`.

No entries today.
