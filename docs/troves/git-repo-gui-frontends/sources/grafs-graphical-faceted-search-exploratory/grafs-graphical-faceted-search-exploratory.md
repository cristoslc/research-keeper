---
source-id: "grafs-graphical-faceted-search-exploratory"
title: "GRAFS: Graphical Faceted Search System to Support Conceptual Understanding in Exploratory Search' - Guo et al. (2023)"
type: web
url: "https://arxiv.org/abs/2302.09448"
fetched: 2026-03-30T18:04:37Z
hash: "d0fd9f4c47425ef8e166b652f84eacc84a6a9ae0215646f82d4c92e2ef2ffd0d"
---

# GRAFS: Graphical Faceted Search System to Support Conceptual Understanding in Exploratory Search

Authors: Mengtian Guo, Zhilan Zhou, David Gotz, Yue Wang. Submitted February 19, 2023. Published in ACM Transactions on Interactive Intelligent Systems, Vol. 13, No. 2, March 2023.

## Abstract

When people search for information about a new topic within large document collections, they implicitly construct a mental model of the unfamiliar information space to represent what they currently know and guide their exploration into the unknown. Building this mental model can be challenging as it requires not only finding relevant documents, but also synthesizing important concepts and the relationships that connect those concepts both within and across documents.

This paper describes a novel interactive approach designed to help users construct a mental model of an unfamiliar information space during exploratory search. We propose a new semantic search system to organize and visualize important concepts and their relations for a set of search results. A user study (n=20) was conducted to compare the proposed approach against a baseline faceted search system on exploratory literature search tasks.

Experimental results show that the proposed approach is more effective in helping users recognize relationships between key concepts, leading to a more sophisticated understanding of the search topic while maintaining similar functionality and usability as a faceted search system.

## Significance for Tag-Based Knowledge Systems

GRAFS represents a key evolution beyond traditional faceted search: instead of merely filtering by facets/tags, it visualizes the *relationships between concepts* extracted from search results. This maps directly to the challenge of browsing tag intersections in a knowledge repository -- the system doesn't just let you select tags, it shows you how concepts (analogous to tags) relate to each other across the document collection, helping users build a mental model of the knowledge space.

The system combines:
- Faceted filtering (select/deselect concepts to narrow results)
- Concept relationship visualization (graph showing how concepts connect)
- Document-concept mapping (which documents contain which concepts)
- Exploratory browsing (progressive refinement without requiring prior domain knowledge)

This is precisely the kind of interface that would serve a tag-based knowledge repository where the interesting relationships emerge at tag intersections.
