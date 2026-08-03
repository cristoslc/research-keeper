# Summary: Why Link (Positioning)

**Source:** https://gowtham0992.github.io/link/why-link.html

**Why selected:** The strategic positioning page — Link's four architectural commitments, its
comparison table against competitors, and its explicit boundaries. This is the source that most
directly frames *what Link is and is not*, against which rk's own vision can be contrasted.

**What it says:** Link positions itself against the agent-memory incumbent set (Mem0/OpenMemory,
Zep/Graphiti, Letta). Four non-negotiable commitments: (1) memory you can read (plain Markdown),
(2) review-gated writes (agents propose, human decides), (3) no LLM in the memory layer
(deterministic ingest/recall), (4) provably local (CI blocks outbound network code). It calls out
Mem0/Zep as storing memory in vector DBs with a model in the write path. It has a "how to choose"
matrix and a comparison table across Obsidian, Mem0, Letta, Zep/Graphiti, built-in agent memory,
and plain RAG. Boundaries are explicit: not a SaaS, viewer is unauthenticated loopback, ingest
quality depends on the agent, generated memory is not trusted.

**Aspects covered:** positioning, the four commitments, best-fit use cases, session-loop framing,
competitive comparison, trust model, boundaries.

**Relevance to trove topic:** rk's PURPOSE.md shares the "knowledge is yours / local / agent-native"
beliefs. But Link makes a *harder* architectural claim than rk: "no LLM in the memory layer,"
enforced by CI. rk's design intentionally delegates intelligence to the calling agent (sidecar
protocol) — which is philosophically aligned but not "provably local" in Link's enforcement sense.
Link's "memory you can read" and "review-gated writes" map directly to rk's trust/provenance goals
in ADR-008/009. This page is the clearest articulation of the memory-as-product vs
knowledge-as-library difference.
