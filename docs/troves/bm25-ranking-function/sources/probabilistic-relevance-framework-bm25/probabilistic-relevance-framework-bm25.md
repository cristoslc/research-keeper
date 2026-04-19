---
source-id: "probabilistic-relevance-framework-bm25"
title: "The Probabilistic Relevance Framework: BM25 and Beyond"
type: web
url: "https://www.researchgate.net/publication/220613776_The_Probabilistic_Relevance_Framework_BM25_and_Beyond"
fetched: 2026-04-18T12:00:00Z
hash: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
---

# The Probabilistic Relevance Framework: BM25 and Beyond

## Abstract

This work presents the PRF from a conceptual point of view, describing the probabilistic modelling assumptions behind the framework and the different ranking algorithms that result from its application: the binary independence model, relevance feedback models, BM25 and BM25F.

## Introduction

The Probabilistic Relevance Framework (PRF) is a formal framework for document retrieval, grounded in work done in the 1970s and 1980s, which led to the development of one of the most successful text-retrieval algorithms, BM25. In recent years, research in the PRF has yielded new retrieval models capable of taking into account document meta-data (especially structure and link-graph information).

## The Binary Independence Model

In this model, documents are represented as binary term-incidence vectors. A query is also represented as a binary term-incidence vector indicating which terms are required. The assumption of "binary independence" means terms occur independently in documents.

The probability ranking principle states that documents should be ranked in decreasing order of their probability of relevance to a given query. This leads to ranking documents by:

P(R=1|d,q) / P(R=0|d,q)

Where R=1 denotes relevance and R=0 denotes non-relevance.

Under the binary independence assumption, this can be rewritten as:

∏(pi/(1-pi))^(xi) *(1-pi)

Where pi is the probability that term i occurs in a relevant document, and xi is 1 if term i occurs in document d and 0 otherwise.

## Development of BM25

By applying various approximations and assumptions, including the Robertson/Sparck Jones weighting formula, the BM25 ranking function was derived:

score(q,d) = ∑ IDF(qi) * (f(qi,d) * (k1+1)) / (f(qi,d) + k1*(1-b+b*|d|/avgdl))

Where:
- IDF(qi) is the inverse document frequency of term qi
- f(qi,d) is the frequency of term qi in document d
- |d| is the length of document d
- avgdl is the average document length in the collection
- k1 and b are free parameters

## BM25F Extension

BM25F extends BM25 to handle multiple document fields with different weights. The document is considered to be composed of several fields with possibly different degrees of importance, term relevance saturation and length normalization.

## Modern Developments

Recent work has extended the PRF to take account of document metadata such as:
- Document structure (headings, titles, etc.)
- Link graph information (similar to PageRank)
- User behavior data

These extensions maintain the probabilistic foundations while incorporating additional relevance signals.