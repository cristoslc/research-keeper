---
source-id: bert-flow-2020
title: "On the Sentence Embeddings from Pre-trained Language Models"
url: "https://arxiv.org/abs/2011.05864"
type: web
fetched: 2026-04-17
---

# On the Sentence Embeddings from Pre-trained Language Models

Authors: Bohan Li, Hao Zhou, Junxian He, Mingxuan Wang, Yiming Yang, Lei Li (EMNLP 2020, arXiv:2011.05864)

## Problem statement

BERT sentence embeddings (without fine-tuning) perform poorly on semantic similarity tasks. Why?

## Key findings

**BERT sentence embeddings occupy an anisotropic, non-smooth region.** The embeddings do not follow a smooth distribution — they cluster in a narrow region of the space. This anisotropy causes two problems: (1) high cosine similarity between any two sentences, even unrelated ones; (2) the similarity scores are compressed into a narrow range, reducing discriminability.

**Normalizing flows can correct the distribution.** The proposed BERT-flow method learns an invertible transformation (normalizing flow) that maps the anisotropic embedding distribution to a smooth, isotropic Gaussian. The flow is learned with an unsupervised objective — no labeled similarity data required.

**Significant gains on STS benchmarks.** BERT-flow achieved state-of-the-art on semantic textual similarity tasks at the time, demonstrating that the embedding geometry (not just the model quality) was the bottleneck.

## Limitations for personal-scale systems

- Normalizing flows require learning parameters (the flow model itself). This needs training data and optimization.
- For a corpus of 10^2–10^3 documents, the flow model may overfit or fail to converge reliably.
- Storage and inference overhead: a flow model must be loaded and applied alongside the embedding model.
- Whitening (Su et al. 2021) achieves competitive results with a simpler, parameter-free approach.

## Relevance to rk

BERT-flow established that anisotropy correction improves semantic similarity. For rk, whitening is the more practical path — same principle (transform to isotropy), but no learned parameters, no training, and negligible storage overhead.