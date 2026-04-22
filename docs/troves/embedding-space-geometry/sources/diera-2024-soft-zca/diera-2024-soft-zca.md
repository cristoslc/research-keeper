---
source-id: diera-2024-soft-zca
title: "Isotropy Matters: Soft-ZCA Whitening of Embeddings for Semantic Code Search"
url: "https://arxiv.org/abs/2411.17538"
type: web
fetched: 2026-04-17
---

# Isotropy Matters: Soft-ZCA Whitening of Embeddings for Semantic Code Search

Authors: Andor Diera, Lukas Galke, Ansgar Scherp (arXiv:2411.17538, November 2024)

## Problem statement

Low isotropy in embedding spaces impairs semantic code search. Does controlling isotropy via whitening improve retrieval, and can it complement contrastive fine-tuning?

## Key findings

**Soft-ZCA whitening improves code search across multiple code LMs and programming languages.** Consistent MRR improvements suggest that embedding space geometry is a real factor in semantic search quality.

**Soft-ZCA introduces a regularization parameter epsilon** that controls the degree of whitening:

```
W = U @ diag(1 / sqrt(S + epsilon))
```

When `epsilon -> infinity`, the transform approaches identity (no whitening). When `epsilon = 0`, it is full ZCA whitening. Intermediate values provide partial whitening.

**Why epsilon matters: full ZCA can over-whiten.** In the tail of the eigenspectrum (small eigenvalues), dividing by `sqrt(S)` amplifies noise directions dramatically. Soft-ZCA dampens this amplification, making the transform more robust when the covariance estimate is noisy — which it always is from a finite sample.

**ZCA outperforms PCA for similarity-oriented tasks.** Confirmed for code search: ZCA preserves the orientation of the embedding space, maintaining the geometric relationship between query and code embeddings. PCA rotates the space, which can disrupt this relationship.

**Whitening complements contrastive fine-tuning.** Applying Soft-ZCA on top of contrastive-fine-tuned models still yields improvements, suggesting the two approaches address different aspects of the isotropy problem.

## Practical implications

- The optimal `epsilon` is a hyperparameter that should be tuned on a validation set.
- Soft-ZCA is a post-processing step — no model modification required.
- The epsilon parameter provides a safety net against over-whitening on small corpora.

## Relevance to rk

This is the most directly applicable paper for SPEC-058. At personal scale (10^2–10^3 embeddings), covariance estimates are inherently noisy. The epsilon parameter in Soft-ZCA provides a second safety layer beyond the `min_samples=50` guard. If full ZCA whitening proves too aggressive on rk's small corpus, Soft-ZCA with a small epsilon is the natural next step.

The SPEC-058 design currently uses `epsilon = 1e-8` (effectively full ZCA). If the spike reveals over-whitening artifacts (e.g., some queries getting worse), increasing epsilon is the tuning knob.