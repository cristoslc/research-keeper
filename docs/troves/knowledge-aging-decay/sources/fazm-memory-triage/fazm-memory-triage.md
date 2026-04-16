---
source-id: fazm-memory-triage
title: "Memory Triage for AI Agents - Why 100% Retention Is a Bug"
url: "https://fazm.ai/blog/ai-agent-memory-triage-retention-decay"
type: web
fetched: 2026-04-16
---

# Memory Triage for AI Agents — Why 100% Retention Is a Bug

An AI agent that remembers everything is not smart — it is cluttered. When every fact gets the same priority, the agent spends tokens retrieving outdated preferences, stale project contexts, and one-time corrections that no longer apply.

The fix is not better storage. It is intentional forgetting.

## The 100% retention problem

Most agent memory systems are append-only. Every interaction adds new facts, corrections, and preferences. Nothing gets removed. Over weeks, the memory grows into a sprawling collection where critical instructions sit next to trivial observations.

Research from the FiFA benchmark (300 simulation runs across five memory budget levels) shows that naive retention actually degrades task completion scores compared to structured forgetting policies. The best-performing hybrid policy scored ~0.911 composite performance while keeping costs tractable.

## Six forgetting policies, ranked

1. **FIFO** — evict oldest memories first. Simple but blind to importance.
2. **LRU** — evict memories not accessed recently. Optimal when usefulness decays exponentially with time.
3. **Priority Decay** — weight memories by importance score, decay that score over time. Better for heterogeneous memory types.
4. **Reflection-Summary** — compress old memories into summaries rather than deleting them. Preserves signal, reduces tokens.
5. **Random Drop** — probabilistic eviction. Surprisingly useful as a baseline.
6. **Hybrid** — stage the above mechanisms. Best composite performance but requires tuning.

## Decay implementation

```python
def decay_score(memory, current_time, decay_factor=0.995):
    hours_elapsed = (current_time - memory.last_accessed).total_seconds() / 3600
    return memory.base_importance * (decay_factor ** hours_elapsed)

def adaptive_decay_rate(base_rate, recall_count, beta=0.1, gamma=0.5):
    return base_rate * (1 - beta * math.tanh(gamma * recall_count))
```

The intuition: a preference you reference daily should decay slower than a one-time project context.

## Key data

- Mem0 achieves 91% reduction in response time vs loading full context
- Weekly triage result: 847 memories → 41 active (62KB → 3.1KB)
- 57% of memories older than 30 days score below retention threshold
- MAGMA architecture: 83.9% accuracy with only 0.7K–4.2K tokens per query (95%+ reduction)

## Core principle

Natural decay is not data loss. Decayed memories still exist in storage — they are just not loaded by default. They can be retrieved on demand if needed.

Perfect recall is not the goal. Useful recall is.