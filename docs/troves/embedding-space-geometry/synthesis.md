# Synthesis: Embedding Space Geometry — Anisotropy, Isotropy, and Post-Processing

## The core problem

Pre-trained language models produce anisotropic embeddings. The embedding cloud does not fill the space uniformly — it squashes into a narrow cone centered around a common direction. In BERT, ELMo, and GPT-2, randomly sampled word representations have average cosine similarity of 0.6–0.9 depending on the layer, even when the words are semantically unrelated (Ethayarajh 2019). This compresses the dynamic range of cosine similarity: everything looks somewhat similar, making it hard to distinguish strong matches from weak ones.

The problem is structural, not random. Higher layers of transformer models are more anisotropic than lower ones. The mean vector (the direction all embeddings cluster around) acts as a bias that inflates all pairwise similarities.

## Three generations of solutions

### Generation 1: Flow-based correction (BERT-flow)

Li et al. (2020) identified that BERT sentence embeddings occupy an anisotropic, non-smooth region. Their solution: learn a normalizing flow that maps the anisotropic distribution to a smooth, isotropic Gaussian. The flow is unsupervised — it learns from the empirical distribution of embeddings without labels. BERT-flow achieved clear gains on STS benchmarks, especially for BERT-base without any fine-tuning.

Limitation: Normalizing flows are learned neural networks with parameters to optimize. They require training data, converging, and storing model weights. For a personal-scale system, this overhead is disproportionate to the data budget.

### Generation 2: Whitening (Su et al. 2021)

The breakthrough insight: you do not need a learned transform. Simple algebraic whitening — center the embedding cloud at zero, then decorrelate dimensions via SVD on the covariance matrix — achieves competitive results with BERT-flow, but with zero training, zero parameters, and four lines of numpy.

The transform is: `x' = (x - mu) W`, where `mu` is the corpus mean and `W` is derived from SVD of the covariance matrix. Two variants exist:

- **PCA whitening**: `W = diag(1/sqrt(S)) @ V^T`, where V and S come from SVD of the centered data matrix. This rotates the space to align with principal components.
- **ZCA whitening**: `W = U @ diag(1/sqrt(S)) @ U^T = U @ diag(1/sqrt(S))`, where U comes from eigendecomposition of the covariance matrix. This preserves the original orientation of the space while decorrelating — vectors that were close before remain close; they just spread out.

ZCA is preferred for similarity tasks because it preserves orientation. PCA rotates the space, which breaks the geometric relationship between query and document embeddings.

Whitening also enables dimensionality reduction: truncate S to the top-k eigenvalues and you get a lower-dimensional embedding that retains most of the variance. Su et al. showed that 128-dim whitened embeddings match or beat 768-dim raw embeddings on STS tasks.

### Generation 3: Contrastive learning (SimCSE)

Gao et al. (2021) showed that contrastive learning inherently mitigates anisotropy. SimCSE's unsupervised variant passes the same sentence through the model twice (with different dropout masks) as a positive pair. The contrastive objective pushes representations toward uniformity, which directly combats anisotropy.

The theoretical contribution: they proved that the InfoNCE loss encourages both alignment (positive pairs close) and uniformity (all points spread evenly on the unit hypersphere). The uniformity term is an explicit isotropy regularizer.

Limitation: Contrastive fine-tuning requiresGPUtime and training data at a scale above what personal corpora provide. It also modifies the model itself, not just the embeddings — a heavier intervention than post-processing.

## The nuance: isotropy is not always good

Rajaee and Pilehvar (2021) injected an important caution. Their study showed that increasing isotropy via post-processing can *hurt* performance on some downstream tasks. The geometry of embedding space is task-dependent: what helps semantic similarity can harm classification or sequence labeling, where the clustering structure (which anisotropy creates) is actually useful.

Implication for research-keeper: whitening is appropriate because `rk` uses embeddings exclusively for similarity-based retrieval. The caution applies if embeddings were reused for classification tasks, which `rk` does not do.

## Soft-ZCA: the latest refinement

Diera et al. (2024) introduced Soft-ZCA whitening for semantic code search. The key innovation: a regularization parameter `epsilon` that controls the degree of whitening, interpolating between raw embeddings (`epsilon -> infinity`) and full ZCA whitening (`epsilon = 0`).

The modified transform: `W = U @ diag(1/sqrt(S + epsilon))`, where `epsilon` is a hyperparameter. This prevents over-whitening — the problem where full decorrelation amplifies noise in low-variance directions (the tail of the eigenspectrum).

Results: Soft-ZCA improved MRR on code search across multiple code LMs and programming languages. The consistent improvements suggest that partial whitening is more robust than all-or-nothing ZCA, especially when the corpus is small and covariance estimates are noisy.

Implication for `rk`: at personal scale (10^2–10^3 sources), covariance estimates from small samples are unreliable. A soft whitening with `epsilon > 0` is safer than full ZCA. The small-corpus guard in SPEC-058 (`min_samples=50`) is the right boundary, and Soft-ZCA's epsilon parameter provides a second safety layer within that boundary.

## Points of disagreement across sources

**Whether anisotropy is always harmful.** Ethayarajh and the BERT-flow paper treat it as a defect to fix. Rajaee and Pilehvar show it can help on non-similarity tasks. The resolution: anisotropy harms similarity search specifically, which is the task `rk` uses.

**Whether post-processing or fine-tuning is the right intervention level.** SimCSE achieves the best results by modifying the model. Whitening achieves competitive results by modifying the output. The trade-off is model access (SimCSE needs the model) versus data scale (whitening needs no labels, but needs enough embeddings for a stable covariance estimate).

**PCA vs. ZCA for similarity tasks.** Su et al. tested both and found ZCA slightly better for STS tasks. Diera et al. confirmed ZCA superiority for code search. The literature converges on ZCA for similarity-oriented workloads.

## Gaps

**No study evaluates whitening on personal-scale corpora (10^2–10^3 documents).** All evaluations use benchmark datasets with thousands to millions of examples. The stability of small-sample covariance estimates is assumed, not measured. This is the key unknown for research-keeper.

**No study measures the interaction between whitening and freshness-weighted retrieval.** `rk` multiplies cosine similarity by a freshness decay factor. Whether whitening interacts with this multiplicatively or changes the optimal decay rate is unexplored.

**No study compares whitening cost/benefit against hybrid retrieval (BM25 + dense) or cross-encoder reranking.** These are alternative approaches to improving retrieval quality that may dominate whitening's contribution. The `rk` adaptation summary noted this correctly: whitening is a high-ROI tweak, not a paradigm shift.

**The interaction between Matryoshka Representation Learning (variable-dimension embeddings) and whitening is unexplored.** If `rk` later adopts MRL for flexible-dimension embeddings, whitening the top-k dimensions of a Matryoshka embedding may behave differently from whitening a fixed-dimension embedding.

## Implications for research-keeper

1. **Whitening is the right first intervention.** It requires no labels, no model access, no GPU, and four lines of numpy. At the scale `rk` operates at, it is the only post-processing technique with a favorable cost/benefit ratio.

2. **ZCA is the correct variant** for similarity search. PCA rotates the space and breaks the geometric relationship between query and document vectors.

3. **Soft-ZCA (epsilon-regulated) is safer than full ZCA** for personal-scale corpora. The epsilon parameter prevents over-whitening when covariance estimates are noisy from small samples.

4. **The `min_samples=50` guard is empirically justified** by the concern Rajaee and Pilehvar raised: post-processing on noisy estimates can hurt. The Soft-ZCA epsilon provides a secondary control within that boundary.

5. **Whitening should not be oversold.** The literature shows consistent but modest gains on STS tasks. For `rk`, the realistic expectation is better rankings on marginal queries, not transformationally different retrieval quality.