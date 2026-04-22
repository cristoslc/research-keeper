---
source-id: ethayarajh-2019-anisotropy
title: "How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings"
url: "https://arxiv.org/abs/1909.00512"
type: web
fetched: 2026-04-17
---

# How Contextual are Contextualized Word Representations?

Authors: Kawin Ethayarajh (EMNLP 2019, arXiv:1909.00512)

## Problem statement

Do contextualized word representations (ELMo, BERT, GPT-2) actually encode context, or do they behave like static embeddings? How anisotropic is the embedding space?

## Key findings

**Anisotropy is universal and severe.** In all layers of all three models, randomly sampled word representations have cosine similarity well above zero. This means the embeddings cluster in a narrow cone rather than filling the space uniformly. Higher layers are more anisotropic than lower ones.

**Contextuality is real but limited.** On average, less than 5% of variance in a word's contextualized representations can be explained by a static embedding for that word. Context matters, but the anisotropy bottleneck limits how much that contextuality can help for similarity tasks.

**Self-similarity decreases with layer depth.** The same word in different contexts has lower cosine similarity in higher layers, suggesting upper layers are more context-specific. But this context-specificity is squeezed into the narrow cone, reducing usable dynamic range.

## Methodology

Analyzed last-hidden-layer representations. Measured:
- Self-similarity: cosine similarity between same word in different contexts
- Intra-sentence similarity: pairwise cosine between words in the same sentence
- Maximum explainable variance (MEV): proportion of variance explained by first principal component

All metrics adjusted for anisotropy by subtracting the mean vector.

## Relevance to rk

This is the foundational diagnosis: anisotropy is not a bug in a particular model, it is a structural property of transformer representation spaces. Any system using these embeddings for similarity search faces the same compressed dynamic range. Whitening directly addresses this by decorrelating and centering the cloud.