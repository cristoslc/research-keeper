# Summary: Agent Memory Contract

**Source:** https://gowtham0992.github.io/link/memory-contract.html

**Why selected:** This is Link's formal *contract* — the exact tool surface and the rules an
agent must follow. It is the best source for comparing Link's MCP tool contract with rk's MCP
server (SPEC-015) and its sidecar protocol (SPEC-019/027/028).

**What it says:** Link defines a small, repeatable agent memory contract over local Markdown.
Five tool groups: `status` (readiness), `recall` (bounded, budgeted retrieval), `remember`/`review`
(approved writes), `ingest` (raw→wiki), `admin` (maintenance). The recommended agent loop is
explicit and step-ordered. Write rules gate `remember` on explicit user approval and mandate
duplicate/conflict handling. Sharing semantics separate `scope` (user/project/global — where a
memory applies) from `visibility` (private/project/team — who sees it).

**Aspects covered:** tool contract, agent loop, write gating, duplicate/conflict candidates,
confidence labels, budgets, scope vs visibility.

**Relevance to trove topic:** rk's SPEC-015 MCP server is smaller — it exposes ingest/query/
synthesize style operations but does not define a `remember`/`review` approved-write contract or
duplicate/conflict handling. Link's write-gate discipline (no durable write without explicit
approval, conflict/duplicate refusal) is a design rk's memory lifecycle (INITIATIVE-003) should
study. The budgeted `recall_capsule` packet is also directly relevant to rk's query-packet and
`--budget` design.
