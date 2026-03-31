# GUI Frontends for a Git-Based Knowledge Repository

## Context

research-keeper (rk) stores knowledge as markdown files with YAML frontmatter in a git repo. Sources are tagged, and each tag has a synthesis directory with generated summaries. The interesting relationships emerge at tag intersections ("what do I know tagged both X and Y?"). This trove explores what existing tools, patterns, and approaches could provide a visual/interactive layer over rk's data model.

---

## Key Findings

### 1. No single tool matches rk's full model

rk combines four capabilities that no existing tool unifies:
- **Git-native storage** (markdown + YAML frontmatter)
- **Tag-based organization** with tag syntheses (generated summaries per tag)
- **Tag intersection browsing** (multi-tag faceted queries)
- **Evolving knowledge** (syntheses update as new sources arrive)

Every tool reviewed excels at 1-2 of these but none covers all four. A viable GUI will likely compose multiple approaches.

### 2. Three architectural tiers emerge

**Tier 1 — Read-only renderers** (lowest effort, narrowest fit):
Obsidian, Quartz, MkDocs Material, Gollum, wikmd, VitePress. These render markdown from a directory or git repo. They handle frontmatter, search, and basic navigation. Obsidian adds graph visualization and bidirectional links. Quartz publishes an Obsidian vault as a static site with graph view, search, and backlinks. MkDocs Material supports tags and git repo integration natively. wikmd is notable for being a file-based wiki with a built-in knowledge graph. **Gap**: None of these understand tag syntheses or faceted tag intersection queries.

**Tier 2 — Faceted/tag-aware browsers** (moderate effort, better model fit):
Faceted search UIs (Ranganathan's classification theory, Hearst's Flamenco project, enterprise faceted navigation) are the closest UX pattern to rk's tag model. The key insight: tags in rk are facets, and intersecting tags is equivalent to faceted drill-down. AO3's "curated folksonomy" is the most successful real-world implementation of this pattern at scale. Raindrop.io's tag filtering feature request thread documents exactly the UX rk needs — progressive tag narrowing where selecting a tag reduces the visible tag list to only co-occurring tags. **Gap**: No off-the-shelf faceted browser works with markdown files on disk. This layer would need to be built, likely as a lightweight web app reading rk's index.

**Tier 3 — AI-powered knowledge interfaces** (highest effort, strongest model fit):
Khoj, QMD, NotebookLM, and local RAG setups (AnythingLLM, Reor) represent the frontier. QMD (17k stars, by Shopify's founder) is particularly relevant — it indexes markdown collections with hybrid BM25 + vector search + LLM re-ranking, all running locally, and exposes an MCP server. Khoj integrates with Obsidian vaults for conversational search over personal knowledge. These tools could provide the "ask rk a question" interface on top of rk's existing embeddings and syntheses. **Gap**: None of these understand rk's tag-synthesis model natively, but they could index the synthesis files as high-value documents.

### 3. The knowledge relationship model matters more than the rendering

Sources broadly agree: the choice isn't "which wiki engine" but "which relationship model." rk's model is closest to:

- **Folksonomy with generated synthesis** — like AO3's curated folksonomy but with LLM-generated tag summaries instead of human curation
- **Faceted classification** — Ranganathan's 1933 insight that items have multiple independent classification axes, formalized in Formal Concept Analysis (FCA) as concept lattices showing tag intersections
- **Zettelkasten with tags** — Luhmann's approach, but rk uses tags as the primary association (what the Zettelkasten community calls "indirect connections") rather than direct links

The most compatible visualization would be:
- **UpSet plots** for showing tag intersection cardinalities (which tag combinations have the most sources)
- **Concept lattices** (FCA) for navigating the tag hierarchy implied by co-occurrence
- **Force-directed graphs** (Sigma.js, D3) for showing source-to-tag-to-source relationships

### 4. Progressive summarization is the synthesis model rk already uses

Readwise's IDEA workflow, Tiago Forte's progressive summarization, and the adaptive summarization research on HuggingFace all describe the pattern rk implements: information flows through layers of increasing distillation (raw source → highlights → synthesis → query answer). The GUI should expose these layers, not flatten them. NotebookLM and Dovetail both demonstrate UIs that show raw material alongside generated understanding — this is the right pattern for rk.

### 5. TiddlyWiki deserves special attention

TiddlyWiki's data model (tiddlers with tags, fields, filters, and transclusion) is remarkably close to rk's. Its filter language (`[tag[X]tag[Y]sort[modified]]`) is essentially a tag intersection query. TiddlyWiki's plugin ecosystem, single-file portability, and 20-year track record make it worth evaluating as a read-only viewer for rk data, potentially with a custom plugin that reads rk's directory structure.

---

## Points of Agreement

- **Markdown + git is the right storage layer** — every source confirms this provides portability, version control, and tool interoperability
- **Graph views are pretty but limited** — Obsidian's graph view gets consistently mixed reviews; users find local graph more useful than global graph; the real value is in structured queries, not visual exploration
- **Faceted navigation is the proven UX pattern** for multi-dimensional categorization — from e-commerce to libraries to AO3
- **Local-first AI search is production-ready** — QMD, Khoj, and RAG frameworks have matured enough for real use on personal knowledge bases

## Points of Disagreement

- **Tags vs. links as primary association**: Matuschak argues tags are weak associations and curated index entries are better. The Zettelkasten community prefers direct links. rk bets on tags with generated syntheses as the primary mechanism — this is a deliberate design choice, not an oversight.
- **Obsidian as universal reader**: Some sources treat Obsidian as the obvious choice for browsing any markdown repo; others note it's closed-source, has soft lock-in via wikilink syntax, and its graph view is "just dots." The symlink workaround for off-vault files works but is fragile.
- **Build vs. compose**: Some argue for building a custom SPA (the Memgraph/Orb approach); others favor composing existing tools (Obsidian + Quartz + Khoj).

## Gaps

- **No existing tool does faceted tag browsing over markdown files on disk** — this is the main gap. The UX pattern is well-understood (faceted navigation), the math exists (FCA/concept lattices), the visualization exists (UpSet), but nobody has assembled these for a local markdown knowledge base.
- **Tag co-occurrence visualization is underdeveloped** — tools like InfraNodus do network analysis of note content, but none visualize tag co-occurrence patterns specifically (which tag pairs/triples share the most sources).
- **Living synthesis UIs barely exist** — Dovetail's Channels feature is the closest to "synthesis that updates as new data arrives," but it's a SaaS product for user research, not a local knowledge base tool.
- **No tool bridges the git history dimension** — rk's data evolves over time in git, but no viewer exposes the temporal dimension of knowledge evolution (how a tag's synthesis changed as sources were added).

---

## Recommendations for rk

1. **Short-term**: Use MkDocs Material or Quartz as a read-only web view. Both handle YAML frontmatter tags, have built-in search, and can be generated from rk's data directory. MkDocs Material's tag plugin natively renders tag pages.

2. **Medium-term**: Add QMD as a semantic search layer. It indexes markdown, runs locally, and exposes an MCP server — rk could use it alongside its own embeddings.

3. **Long-term**: Build a lightweight faceted browser (likely a single-page app using Sigma.js for graph + UpSet.js for intersections + a faceted sidebar) that reads rk's tag index and synthesis files. This is the piece that doesn't exist yet and would be rk's unique contribution.

4. **Evaluate TiddlyWiki** as an alternative to building from scratch — its filter language and plugin model might be close enough to rk's needs to avoid a custom build.
