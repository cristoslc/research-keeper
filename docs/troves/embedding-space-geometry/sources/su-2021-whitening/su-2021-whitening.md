---
source-id: su-2021-whitening
title: "Whitening Sentence Representations for Better Semantics and Faster Retrieval"
url: "https://arxiv.org/abs/2103.15316"
type: web
fetched: 2026-04-17
---

# Whitening Sentence Representations for Better Semantics and Faster Retrieval

Authors: Jianlin Su, Jiarun Cao, Weijie Liu, Yangyiwen Ou (arXiv:2103.15316, March 2021)

Code: https://github.com/bojone/BERT-whitening

## Problem statement

The anisotropy problem in BERT sentence embeddings limits semantic similarity performance. Flow-based methods (BERT-flow) work but require learned parameters. Can simpler, parameter-free methods achieve the same effect?

## Key findings

**Whitening achieves competitive results with BERT-flow, without any learned parameters.** The transform is purely algebraic: center the embeddings at zero, then decorrelate dimensions by applying a whitening matrix derived from SVD of the covariance matrix.

**The whitening operation is:**
```
x' = (x - mu) @ W
```
Where:
- `mu` = mean of all embeddings in the corpus
- `W` = whitening matrix from eigendecomposition of covariance

**Two variants tested:**
- PCA whitening: `W = diag(1/sqrt(S)) @ V^T` — rotates to principal components, then scales
- ZCA whitening: `W = U @ diag(1/sqrt(S))` — preserves original orientation while decorrelating

**ZCA slightly outperforms PCA for similarity tasks** because it preserves the relative positions of points in the space. PCA rotates the space, which can break the geometric relationship between query and document embeddings.

**Whitening enables dimensionality reduction.** By truncating to top-k eigenvalues, you can reduce from 768 dims to 128 or 256 dims while maintaining or improving similarity performance. This reduces storage and speeds up retrieval.

**Results on STS benchmarks:** Comparable to BERT-flow, sometimes better. The key advantage is simplicity: no training, no parameters, no convergence concerns.

## Practical details

- Requires computing SVD of a d x d covariance matrix (where d = embedding dimension). For 768-dim embeddings, this is a 768x768 SVD — trivial on CPU.
- The mean and whitening matrix are computed from the corpus embeddings, then stored for reuse.
- The transform is applied at retrieval time to both query and document embeddings.

## Relevance to rk

This is the primary technique behind SPEC-058. The four-line numpy implementation, zero training overhead, and ZCA variant preference are all adopted directly from this paper.