---
source-id: "practical-bm25-elastic-blog"
title: "Practical BM25 - Part 2: The BM25 Algorithm and its Variables"
type: web
url: "https://www.elastic.co/blog/practical-bm25-part-2-the-bm25-algorithm-and-its-variables"
fetched: 2026-04-18T12:00:00Z
hash: "b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890a"
---

# Practical BM25 - Part 2: The BM25 Algorithm and its Variables

## Introduction

BM25 is a ranking function used by search engines to rank matching documents according to their relevance to a given search query. It is based on the probabilistic retrieval framework developed in the 1970s and 1980s by Stephen E. Robertson and others.

## The BM25 Formula

The BM25 formula combines three key components:

1. **Inverse Document Frequency (IDF)** - Measures how rare a term is across the entire document collection
2. **Term Frequency Saturation** - Prevents over-ranking of documents with excessive term occurrences
3. **Document Length Normalization** - Ensures documents of different lengths are fairly compared

The formula is:

score(q,d) = ∑ IDF(qi) * (f(qi,d) * (k1+1)) / (f(qi,d) + k1 * (1-b+b*|d|/avgdl))

## Parameter Explanation

### k1 - Term Frequency Saturation

k1 is a variable which helps determine term frequency saturation characteristics. That is, it limits how much a single query term can affect the score of a given document. It does this through approaching an asymptote.

- Higher k1 values mean that term frequency has more influence on the score
- Lower k1 values cause term frequency to saturate more quickly
- Typical values range from 1.2 to 2.0

### b - Document Length Normalization

The parameter b controls document length normalization:
- b = 1 will apply full document-length normalization
- b = 0 will ignore the length factor
- Typical value is 0.75

This normalization prevents longer documents from being unfairly favored simply due to their length.

### IDF Calculation

The IDF component is calculated as:

IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5))

Where:
- N is the total number of documents
- n(qi) is the number of documents containing term qi

This formula provides better behavior for very common and very rare terms.

## Practical Considerations

### Score Interpretation

Unlike some other ranking algorithms, BM25 produces unbounded positive scores. The absolute values are less important than the relative ordering of documents.

### Tuning Parameters

While default values work well for many applications, tuning k1 and b for specific domains can provide significant improvements:

- For domains with long, technical documents, lower k1 values may be appropriate
- For domains where exact term matching is more important, higher k1 values may be better
- For very consistent document lengths, b can be reduced

### Integration with Modern Search

BM25 is often used as part of a hybrid search approach:
1. Initial candidate selection using BM25
2. Refinement using neural ranking models
3. Final re-ranking using learning-to-rank techniques

This approach combines BM25's strengths in exact matching with neural models' semantic understanding.