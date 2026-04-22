---
source-id: simcse-2021
title: "SimCSE: Simple Contrastive Learning of Sentence Embeddings"
url: "https://arxiv.org/abs/2104.08821"
type: web
fetched: 2026-04-17
---

# SimCSE: Simple Contrastive Learning of Sentence Embeddings

Authors: Tianyu Gao, Xingcheng Yao, Danqi Chen (EMNLP 2021, arXiv:2104.08821)

Code: https://github.com/princeton-nlp/simcse

## Problem statement

How to produce high-quality sentence embeddings from pre-trained models? Can contrastive learning address the anisotropy problem more effectively than post-processing?

## Key findings

**Unsupervised SimCSE: dropout as data augmentation.** Pass the same sentence through the model twice (with different dropout masks) and treat the two outputs as a positive pair. This simple approach performs on par with previous supervised methods.

**Supervised SimCSE: NLI pairs.** Use entailment pairs as positives and contradiction pairs as hard negatives in the contrastive objective. Achieves 81.6% Spearman's correlation on STS benchmarks (vs. 76.3% for unsupervised).

**Theoretical contribution: contrastive learning regularizes toward isotropy.** The authors prove that the InfoNCE objective encourages two properties:
1. **Alignment**: positive pairs should be close in embedding space
2. **Uniformity**: all points should be roughly uniformly distributed on the unit hypersphere

The uniformity property is an explicit isotropy regularizer. This is why contrastive fine-tuning mitigates anisotropy — it pushes embeddings away from the narrow cone toward a fuller distribution.

**Dropout is essential.** Removing dropout (using identical representations as positive pairs) causes representation collapse. Dropout acts as minimal data augmentation — the noise it introduces is just enough to prevent collapse.

## Limitations for personal-scale systems

- Requires GPU-time for fine-tuning the model on training data.
- At personal corpus scale (10^2–10^3 sources), contrastive fine-tuning risks overfitting.
- Modifies the model itself, not just the output — heavier intervention than post-processing.
- Needs a serving path that uses the fine-tuned model (not the default one from Ollama/sentence-transformers).

## Relevance to rk

SimCSE explains *why* anisotropy correction works (uniformity is beneficial for similarity) and provides the theoretical grounding. For rk at personal scale, contrastive fine-tuning is not the right approach, but the alignment-uniformity framework helps understand what whitening approximates: pushing toward uniformity without modifying the model.