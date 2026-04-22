---
source-id: rajaee-2021-finetuning-isotropy
title: "How Does Fine-tuning Affect the Geometry of Embedding Space: A Case Study on Isotropy"
url: "https://arxiv.org/abs/2109.04740"
type: web
fetched: 2026-04-17
---

# How Does Fine-tuning Affect the Geometry of Embedding Space: A Case Study on Isotropy

Authors: Sara Rajaee, Mohammad Taher Pilehvar (EMNLP 2021 Findings, arXiv:2109.04740)

## Problem statement

Fine-tuning pre-trained language models typically improves downstream performance. But how does fine-tuning affect the geometric properties of the embedding space, specifically isotropy? And is increasing isotropy always beneficial?

## Key findings

**Fine-tuning does not consistently increase isotropy.** The relationship between fine-tuning and isotropy is task-dependent. For some tasks, fine-tuning makes the space *more* anisotropic.

**Increasing isotropy via post-processing can hurt performance.** This is the crucial caution. When isotropy is artificially increased on representations that were already well-structured for a task (e.g., classification), the post-processing destroys structure that was useful.

**The caveat is task-specific.** Isotropy helps for similarity search (where uniform distribution of points is desirable) but can harm classification (where cluster structure — which anisotropy creates — is informative).

## Methodology

Measured isotropy using the self-similarity metric and the average pairwise cosine similarity in embedding spaces before and after fine-tuning on various NLU tasks (MNLI, SST-2, QQP, QNLI). Compared raw embeddings with post-processed (isotropy-increased) variants.

## Relevance to rk

This paper justifies the narrow scope of SPEC-058: whitening is appropriate because rk uses embeddings exclusively for similarity search. The caution against increasing isotropy applies to classification or sequence labeling — tasks rk does not perform on its embeddings. If rk later uses embeddings for tag classification (as in the tag-prototype proposal), that part of the pipeline should use raw (or separately-projected) embeddings, not whitened ones.