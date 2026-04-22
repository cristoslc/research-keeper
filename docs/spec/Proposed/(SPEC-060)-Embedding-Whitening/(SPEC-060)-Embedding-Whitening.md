---
title: "Embedding Whitening for Anisotropy Correction"
artifact: SPEC-060
track: implementable
status: Proposed
author: cristos
created: 2026-04-17
last-updated: 2026-04-17
priority-weight: medium
type: enhancement
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts:
  - DESIGN-012
depends-on-artifacts:
  - SPEC-036
addresses:
  - PERSONA-001
  - PERSONA-002
evidence-pool: "trove: embedding-space-geometry"
source-issue: ""
swain-do: required
---

# Embedding Whitening for Anisotropy Correction

## Problem Statement

`nomic-embed-text-v1.5` and other modern embedding models produce anisotropic embedding spaces — the embedding cloud is squashed into a narrow cone rather than filling the space uniformly. This compresses the dynamic range of cosine similarity: unrelated documents score 0.6–0.8 instead of ~0, making it harder to distinguish strong matches from weak ones. The symptom is marginally noisy retrieval rankings, especially on queries where the semantic signal is already ambiguous.

## Desired Outcomes

After `rk rebuild`, embeddings are transformed with ZCA whitening, decorrelating dimensions and centering the cloud at zero. Cosine similarity on whitened embeddings produces better separation between relevant and irrelevant documents. Retrieved results rank marginally better on edge-case queries — not transformationally different, but measurably improved on the long tail.

## External Behavior

**No CLI changes.** `rk search`, `rk add`, and `rk rebuild` all work the same way. Whitening is an internal optimization applied during rebuild.

**`rk doctor` gains a check for whitening staleness.** If the whitening transform was fitted on a much smaller corpus (e.g., 50 embeddings) and the current corpus has grown substantially (e.g., 200 embeddings), `rk doctor` warns that whitening should be refreshed via `rk rebuild`.

**Retrieval quality improves on marginal queries.** Queries that previously returned borderline-irrelevant results in the top-k now push those further down, promoting better matches. The effect is subtle but measurable on held-out test queries.

## Acceptance Criteria

1. **Given** a corpus with ≥50 embeddings, **when** `rk rebuild` runs, **then** a ZCA whitening transform is fitted per embedding model and stored in the `embedding_transform` table.

2. **Given** a corpus with <50 embeddings, **when** `rk rebuild` runs, **then** no whitening transform is fitted (guard against overfitting on tiny corpora).

3. **Given** a fitted whitening transform, **when** `rk search` runs, **then** the query embedding and all stored embeddings are whitened before computing cosine similarity.

4. **Given** no whitening transform exists (e.g., first build, or corpus too small), **when** `rk search` runs, **then** retrieval works correctly using raw embeddings (graceful no-op).

5. **Given** multiple embedding models in use, **when** whitening is fitted, **then** each model has its own transform (scoped by `embeddings.model` column).

6. **Given** a whitening transform fitted on N samples, **when** the corpus grows to N+Δ, **then** `rk doctor` warns if Δ/N > 0.5 (transform staleness check).

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|
| 1 | Integration test: create 50 sources, run rebuild, assert `embedding_transform` has row with `n_samples >= 50` | |
| 2 | Integration test: create 20 sources, run rebuild, assert `embedding_transform` has no whitening row | |
| 3 | Retrieval test: compare top-k results before/after whitening on held-out query set; expect rank correlation <1.0 but improved precision@k on labeled relevance | |
| 4 | Unit test: `SemanticRetriever._whiten()` returns input unchanged when transform absent; retrieval succeeds | |
| 5 | Integration test: simulate two models (mock embedder), assert two whitening transforms fitted independently | |
| 6 | `rk doctor` test: artificially set `n_samples=50` on transform, add 30 new embeddings, assert warning | |

## Scope & Constraints

- **Whitening is per-model, not global.** Different embedding models have different covariance structure. The `embedding_transform.id` convention is `whitening:{model_name}` (e.g., `whitening:nomic-ai/nomic-embed-text-v1.5`).

- **Soft-ZCA whitening is used (Diera et al. 2024).** ZCA (`W = U diag(1/√(S+ε)) Uᵀ`) preserves orientation and empirically performs better on sentence-similarity tasks. The epsilon parameter prevents over-whitening: at small corpus sizes, covariance estimates are noisy and tail eigenvalues are unreliable — dividing by `sqrt(S)` without a dampener amplifies noise. Epsilon interpolates between full ZCA (ε→0) and no transform (ε→∞).

- **`min_samples=50` is a hard guard.** Below this threshold, the SVD on covariance gives noise and whitening hurts retrieval.

- **Whitening runs at rebuild time, not during `rk add`.** The transform is recomputed on every `rk rebuild` to reflect the full corpus. Incremental updates are not supported in this spec.

- **Storage overhead is acceptable.** For 768-dim embeddings (nomic), the W matrix is 768×768×4 bytes = 2.3 MB. For 1024-dim (future model swap), 4 MB. For 3072-dim, 36 MB. All acceptable for a personal tool.

- **No changes to the `Embedder` port.** Whitening is a post-processing step applied to embeddings after they're generated, not part of the embedder interface.

- **No vectorization optimization in this spec.** The retriever will still do per-row Python dot products. Numpy vectorization can be added later if latency becomes a bottleneck.

## Design

### Storage Schema

New table added to `SqliteIndex._create_schema`:

```sql
CREATE TABLE IF NOT EXISTS embedding_transform (
    id TEXT PRIMARY KEY,        -- 'whitening:<model>'
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    mu BLOB NOT NULL,           -- dim float32s
    w BLOB NOT NULL,            -- dim*dim float32s
    epsilon REAL NOT NULL,      -- soft-ZCA regularization
    n_samples INTEGER NOT NULL,
    created_at TEXT
);
```

### Whitening Fit in `_rebuild_impl`

Called at end of embedding backfill phase (after all embeddings are present):

```python
def _fit_whitening(index: SqliteIndex, min_samples: int = 50, epsilon: float | None = None):
    import numpy as np
    
    # Read epsilon from config if not provided; default 0.01 per Soft-ZCA guidance
    if epsilon is None:
        epsilon = getattr(index, "_whitening_epsilon", 0.01)
    
    cur = index._conn.cursor()
    cur.execute("SELECT model, embedding FROM embeddings WHERE embedding IS NOT NULL AND length(embedding) > 0")
    
    # Group by model
    by_model: dict[str, list[np.ndarray]] = {}
    for row in cur.fetchall():
        model = row["model"]
        emb = np.frombuffer(row["embedding"], dtype=np.float32)
        by_model.setdefault(model, []).append(emb)
    
    for model, vecs in by_model.items():
        if len(vecs) < min_samples:
            logger.info(f"Skipping whitening for {model}: only {len(vecs)} embeddings (need {min_samples})")
            continue
        
        X = np.stack(vecs)  # n_samples x dim
        mu = X.mean(axis=0)
        X_centered = X - mu
        cov = np.cov(X_centered.T)  # dim x dim
        U, S, _ = np.linalg.svd(cov)
        
        # Soft-ZCA whitening: W = U @ diag(1/sqrt(S + epsilon))
        # epsilon > 0 dampens tail eigenvalues, preventing over-whitening on noisy
        # small-sample covariance estimates (Diera et al. 2024, arXiv:2411.17538)
        W = (U @ np.diag(1.0 / np.sqrt(S + epsilon))).astype(np.float32)
        
        # Persist
        cur.execute("""
            INSERT OR REPLACE INTO embedding_transform
            (id, model, dim, mu, w, epsilon, n_samples, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"whitening:{model}",
            model,
            X.shape[1],
            mu.astype(np.float32).tobytes(),
            W.astype(np.float32).tobytes(),
            epsilon,
            len(vecs),
            datetime.now(timezone.utc).isoformat(),
        ))
    
    index._conn.commit()
```

### Retriever Integration

`SemanticRetriever.__init__` loads transforms:

```python
def __init__(self, index: SqliteIndex, half_life_days: int = 30) -> None:
    self._index = index
    self._half_life_days = half_life_days
    self._transforms = self._load_transforms()

def _load_transforms(self) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Load whitening transforms. Returns {model: (mu, W)}."""
    cur = self._index._conn.cursor()
    cur.execute("SELECT model, mu, w FROM embedding_transform WHERE id LIKE 'whitening:%'")
    return {
        row["model"]: (
            np.frombuffer(row["mu"], dtype=np.float32),
            np.frombuffer(row["w"], dtype=np.float32)
        )
        for row in cur.fetchall()
    }

def _whiten(self, emb_bytes: bytes, model: str) -> bytes:
    """Apply whitening transform. Returns input unchanged if transform absent."""
    t = self._transforms.get(model)
    if t is None:
        return emb_bytes
    
    mu, W = t
    x = np.frombuffer(emb_bytes, dtype=np.float32)
    return ((x - mu) @ W).astype(np.float32).tobytes()
```

Apply in `search_by_embedding`:

```python
# Before scoring, whiten query embedding
query_whitened = self._whiten(query_embedding, model)

for row in cur.fetchall():
    embedding = row[1]
    # Whitening stored embedding
    embedding_whitened = self._whiten(embedding, model)
    
    similarity = cosine_similarity(query_whitened, embedding_whitened)
    # ... rest of scoring
```

### `rk doctor` Staleness Check

```python
def doctor_whitening(index: SqliteIndex) -> list[str]:
    """Check if whitening transform is stale. Returns list of warnings."""
    cur = index._conn.cursor()
    
    # Count current embeddings per model
    cur.execute("""
        SELECT model, COUNT(*) as n 
        FROM embeddings 
        WHERE embedding IS NOT NULL AND length(embedding) > 0
        GROUP BY model
    """)
    current_counts = {row["model"]: row["n"] for row in cur.fetchall()}
    
    # Check transform staleness
    cur.execute("SELECT id, model, n_samples FROM embedding_transform WHERE id LIKE 'whitening:%'")
    warnings = []
    for row in cur.fetchall():
        model = row["model"]
        n_samples = row["n_samples"]
        current = current_counts.get(model, 0)
        
        if current > n_samples * 1.5:  # Grown by >50%
            warnings.append(
                f"Whitening for {model} fitted on {n_samples} embeddings, "
                f"but corpus now has {current}. Run 'rk rebuild' to refresh."
            )
    
    return warnings
```

## Dependencies

**numpy requirement:** Whitening requires `numpy` for SVD and matrix operations. The `sentence-transformers` dependency (added in SPEC-056) already pulls in numpy, so no new runtime dependency is needed.

**SPEC-036 (Chunk Embeddings):** This spec assumes the chunk-embedding flow from SPEC-036 is already in place. Whitening operates on the `embeddings` table as designed — no changes needed if SPEC-036 is complete.

**DESIGN-012 (Sentence Transformers Backend):** Whitening is model-agnostic, but the current default model (`nomic-embed-text-v1.5`) is what the covariance analysis in the spike should measure.

## Configuration

New field in `rk.yaml` under `embeddings`:

```yaml
embeddings:
  model: nomic-ai/nomic-embed-text-v1.5
  whitening:
    min_samples: 50        # skip whitening below this threshold
    epsilon: 0.01          # soft-ZCA regularization (Diera et al. 2024)
```

If `whitening` section is absent, defaults apply. If `epsilon: 0.0`, full ZCA whitening (no regularization).

## Open Decisions

1. **Incremental vs. batch whitening refresh.** This spec chooses batch (rebuild-only). If staleness warnings become annoying, incremental updates (e.g., online mean/covariance estimation) could be added later.

2. **Whether to expose `--whitening-only` flag on `rk rebuild`.** For now, whitening always runs if `min_samples` threshold is met. A flag could skip it for debugging or faster rebuilds.

3. **Whether to track which sources were in the training set.** For unsupervised whitening, this is less critical than for supervised projections. The `n_samples` column provides implicit tracking.

4. **Dimensionality reduction?** This spec is whitening only (no dimensionality reduction). If desired later, PCA truncation can be added to the same `embedding_transform` table, with a new `output_dim` column.

5. **Optimal epsilon value.** Default is 0.01 based on Soft-ZCA guidance. The spike should test epsilon values of [0.001, 0.01, 0.1, 1.0] on the actual corpus to find the sweet spot. Too low risks over-whitening; too high approaches the identity transform.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-17 | — | Initial creation |