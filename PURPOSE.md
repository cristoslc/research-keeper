# Purpose

Research-keeper exists because knowledge should compound, not decay.

When you encounter something worth knowing — an article, a paper, a talk, a passing insight — it should become part of your understanding, not another bookmark you'll never revisit. The tools we have today either demand disciplined manual organization (which nobody maintains) or treat search as the only access pattern (which surfaces links, not understanding).

Research-keeper takes a different position: **the agent you're already working with should be the one organizing your knowledge.** Not a separate app, not a manual workflow, not another tab. The agent adds a source, tags it, synthesizes it with what you already know, and moves on. Your knowledge base grows as a side effect of doing research, not as a chore you perform after.

## Beliefs

**Intelligence belongs to the caller.** Research-keeper never calls an LLM API. It describes what it needs — tag this content, synthesize these sources, answer this question — and the agent running it provides the intelligence. This means zero API billing, no vendor lock-in, and natural integration with whatever agent stack you use.

**Sidecars are source of truth.** Every source gets a YAML manifest that records what it is, where it came from, when it arrived, and what tags it carries. The database is derived. You can delete it and rebuild from the filesystem. You can read your knowledge base with `ls` and `cat`. No proprietary format, no opaque storage.

**Symlinks are views.** Tags, queries, and investigations don't copy sources — they link to them. A tag directory is a lens, not a container. `cp -rL` on any directory produces a portable export with all referenced content. The filesystem IS the data model.

**Graceful degradation over hard failure.** If the embedder is down, file without embeddings. If no LLM is available, file without tags. If synthesis fails, keep the tags. Every layer degrades independently. Nothing blocks intake.

**Git is the transport.** The knowledge base is a git repo. Cloud agents clone it. Local agents work in place. Collisions are detected and reconciled, not prevented. This is simpler and more durable than any sync protocol.

## Who this is for

Researchers, developers, and knowledge workers who collect more than they organize — and who already work with AI agents as their primary interface. If you use Claude Code, codex, Cursor, or any agentic runtime as part of your daily workflow, research-keeper turns that agent into your librarian.
