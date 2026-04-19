---
source-id: "reddit-claudecode-llm-wiki-plugin"
title: "Turned Andrej Karpathy's 'LLM Wiki' gist into a Claude Code plugin. Also works in Codex, OpenCode, Cursor, Gemini CLI, Pi, and OpenClaw."
type: forum
url: "https://www.reddit.com/r/ClaudeCode/comments/1sm374u/turned_andrej_karpathys_llm_wiki_gist_into_a/"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
participants:
  - "u/Numerous-Exercise788"
  - "various commenters"
post-count: 5
---

# Turned Andrej Karpathy's "LLM Wiki" gist into a Claude Code plugin

Subreddit: r/ClaudeCode
Votes: 7
Comments: 5
Posted by: u/Numerous-Exercise788

## Original Post

Background: Andrej Karpathy published a gist in April outlining what he calls the "LLM Wiki" pattern. The core observation: RAG re-derives knowledge from raw chunks on every query, so nothing accumulates. His pattern flips this. When a source arrives, the LLM compiles it once into a persistent markdown wiki it owns and maintains.

I turned this into a plugin that works across multiple LLM platforms.

## Known Failure Modes

Three issues the author encountered in practice:

1. **Silent corruption from mis-ingesting one source** — The LLM can introduce errors during compilation that are not immediately visible. The wrong interpretation of a source gets baked into the wiki and propagates.

2. **Wiki-reads-its-own-output drift** — The LLM treats prior wiki pages as ground truth instead of re-checking raw sources. Over time, the wiki drifts away from the original documents because the LLM prefers to read its own compiled output rather than going back to raw sources.

3. **The maintenance ratchet** — Lint reports grow faster than you can review them. As the wiki grows, health checks surface more issues than a single person can address. The lint → fix cycle becomes a bottleneck.

All three are discussed in the skill's SKILL.md with mitigations.

## Cross-Platform Compatibility

The plugin works in: Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Pi, and OpenClaw. This is significant because it means the pattern is not tied to any single LLM vendor.

## Request for Feedback

The author asked: "If you've tried Karpathy's pattern yourself, I'd like to hear what you ingested first and what broke before it worked." This implies the pattern has rough edges that only become visible through actual use, not theoretical analysis.