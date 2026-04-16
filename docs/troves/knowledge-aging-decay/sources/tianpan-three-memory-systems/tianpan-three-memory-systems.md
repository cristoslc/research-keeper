---
source-id: tianpan-three-memory-systems
title: "The Three Memory Systems Every Production AI Agent Needs"
url: "https://tianpan.co/blog/long-term-memory-types-ai-agents"
type: web
fetched: 2026-04-16
---

# The Three Memory Systems Every Production AI Agent Needs

Cognitive science recognizes that human memory is not monolithic: episodic, semantic, and procedural memory operate differently, decay differently, and fail differently. AI agents benefit from the same taxonomy.

## Three memory types

### Episodic memory
Stores specific interactions with context intact: what was asked, answered, what tools were called, what the outcome was, and when. Timestamps are load-bearing — "the user said they were evaluating our product" means something different yesterday vs eight months ago. Stores grow without bound; without pruning or summarization, retrieval degrades.

### Semantic memory
Facts extracted from experience, no longer tied to the episode that produced them. "This user's infrastructure is GCP-based" outlives the conversation that revealed it. Key wrinkle: semantic facts go stale. Users change jobs, companies change tech stacks. Production implementations add confidence decay — semantic memories become less authoritative over time unless reinforced by new episodic evidence.

### Procedural memory
Stores how to do things — learned patterns proven effective in context. Not "the user prefers Python" (semantic fact) but "when writing data pipeline code for this user, use Polars instead of Pandas because past responses using Pandas were flagged as unhelpful" (learned heuristic about what to do). Most underused of the three in current agent architectures, and arguably the most valuable. Agent gets measurably better with use.

## Retrieval: three independent signals

Effective retrieval combines three independent signals:

1. **Relevance** — semantic similarity (embedding cosine similarity)
2. **Recency** — exponential decay factor (~0.995 per hour is a reasonable starting point)
3. **Importance** — significance at formation time (LLM-scored at write time, or inferred from user behavior)

Too much recency bias: agent forgets important long-term context. Too little: distracted by stale information.

## The forgetting question

Implementing decay means downweighting memories in retrieval scoring until they fall below a threshold where they're effectively invisible — but can be recovered if specifically requested. This preserves correctness (full history always available) while preventing stale information from polluting active reasoning.

Education platform reduced token costs by 40% with tiered memory and decay.

## Architecture advice

1. **Separate stores by type.** Mixing episodic, semantic, and procedural into a single vector database makes retrieval harder.
2. **Write time is as important as read time.** Quality of retrieval depends entirely on quality of what was stored.
3. **Build measurement before sophistication.** The Memory Trilemma: for the first 30–150 conversations, full context achieves 70–82% accuracy; retrieval-based drops to 30–45%. Needs time to be worth the complexity.