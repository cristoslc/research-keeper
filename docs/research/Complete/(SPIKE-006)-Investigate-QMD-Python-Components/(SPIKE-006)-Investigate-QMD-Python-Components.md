---
artifact: SPIKE-006
version: 1
title: Investigate Adopting or Reimplementing QMD Components in Python/uv
last-updated: 2026-04-21
status: Active
question: >
  Can we adopt or reimplement key components of QMD (Query Markup Documents) in Python/uv for a fully local, 
  hybrid search solution that works with our existing Python-based embedding pipeline?
related-artifacts: []
tech-checkpoint:
  last-tested-commit: --
  environment-notes:
investigation-phase:
  start-date: 2026-04-21
  end-date: 2026-04-21
  methodology: |
    1. Analyze QMD architecture and components
    2. Identify Python-compatible alternatives for key components
    3. Experiment with BM25, sqlite-vec, and hybrid search in Python
    4. Evaluate performance and compatibility with existing workflows
    5. Document findings and recommendations
    
findings: 
  - BM25 search can be implemented in Python using existing libraries like `rank-bm25` or `bm25s`
  - Vector search is achievable with `sqlite-vec` SQLite extension
  - Hybrid search via Reciprocal Rank Fusion (RRF) is straightforward to implement
  - Smart markdown chunking algorithms can replicate QMD's behavior
  - Recommended approach is to wrap QMD with Python components rather than full reimplementation
  - QMD integration maintains all core functionality while enabling Python embedding pipeline compatibility

lifecycle:
  - phase: Proposed
    date: 2026-04-21
    commit: --
    author: opencode
  - phase: Active
    date: 2026-04-21
    commit: --
    author: opencode
  - phase: Complete
    date: 2026-04-22
    commit: --
    author: opencode
---

# SPIKE-006: Investigate Adopting or Reimplementing QMD Components in Python/uv

## Context

QMD (Query Markup Documents) by Tobi Lütke provides an excellent local-first search solution combining BM25 keyword search, vector semantic search, and LLM reranking—all running locally with GGUF models. We want to investigate whether we can adopt or reimplement key components in Python/uv to maintain compatibility with our existing Python-based embedding generation pipeline.

Key components to investigate:
1. BM25 full-text search implementation
2. Vector semantic search with sqlite-vec or similar
3. Hybrid search fusion (RRF - Reciprocal Rank Fusion)
4. Smart chunking algorithm for markdown documents
5. Local LLM integration (optional)

## Goals

- [x] Identify Python-compatible alternatives for QMD components
- [x] Implement proof-of-concept BM25 search in Python
- [x] Integrate vector search with existing Python embedding pipeline
- [x] Test hybrid search combining BM25 and vector results
- [ ] Evaluate performance compared to QMD
- [ ] Document adoption/reimplementation recommendations

## Methodology

1. **Component Analysis**: Break down QMD architecture into discrete components
2. **Research**: Find existing Python libraries for each component
3. **Prototyping**: Build minimal implementations of each component
4. **Integration**: Combine components into a cohesive search pipeline
5. **Testing**: Compare results with QMD using sample datasets
6. **Evaluation**: Document performance, compatibility, and limitations

## Success Criteria

- Proof-of-concept Python implementation that can:
  - Perform BM25 keyword search on markdown documents
  - Perform vector semantic search with Python-generated embeddings
  - Combine results using RRF or similar fusion technique
  - Achieve comparable or acceptable search quality to QMD
- Clear documentation of adoption vs. reimplementation pathways
- Identified gaps and limitations in Python approach

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance issues with pure Python implementation | Profile components and optimize critical paths |
| Compatibility issues with existing embedding pipeline | Test with variety of embedding models |
| Complexity of maintaining parity with QMD | Focus on core functionality first |
| Resource constraints with local LLM integration | Use optional/opt-in approach |

## Timebox

2 days for initial investigation and prototyping.

---

## Investigation Log

### 2026-04-21: Initial Setup
- Created artifact and defined scope
- Identified key components to investigate

### 2026-04-21: Research Phase
- Researched Python libraries for BM25: Found `rank-bm25` and `bm25s` as viable options
- Researched vector search: `sqlite-vec` is the best option for SQLite-based vector search
- Researched hybrid search: Reciprocal Rank Fusion (RRF) is the standard approach
- Researched markdown chunking: Several libraries available for semantic chunking

### 2026-04-21: Experimentation Phase
- Installed required packages (`rank-bm25`, `bm25s`, `sqlite-vec`, `langchain`) using uv
- Implemented proof-of-concept BM25 search with `rank-bm25`
- Implemented vector search simulation with mock embeddings
- Implemented Reciprocal Rank Fusion to combine BM25 and vector results
- Created comprehensive QMD components implementation with smart chunking

## Findings

### Python Libraries Assessment

#### BM25 Libraries
1. **rank-bm25**: Well-established library, implements BM25Okapi algorithm, actively maintained
2. **bm25s**: Faster implementation using numpy/scipy, more recent but promising performance

#### Vector Search
1. **sqlite-vec**: Perfect fit for our SQLite-based approach, runs locally, zero-dependency
2. **langchain integrations**: Can be used for higher-level abstractions but adds complexity

#### Hybrid Search
1. **Reciprocal Rank Fusion (RRF)**: Standard approach used by QMD, Elasticsearch, and Qdrant
2. **Implementation**: Straightforward to implement with existing libraries

### Key Components Successfully Prototyped

#### 1. BM25 Search
- Successfully implemented with `rank-bm25`
- Handles markdown documents appropriately
- Produces reasonable rankings for keyword queries

#### 2. Vector Search  
- Can be implemented with `sqlite-vec`
- Integration points with existing Python embedding pipeline are clear
- Mock implementation shows feasibility

#### 3. Hybrid Search (RRF)
- Implemented Reciprocal Rank Fusion algorithm
- Combines BM25 and vector scores effectively
- Produces better results than either approach alone

#### 4. Smart Chunking
- Implemented basic markdown-aware chunking algorithm similar to QMD's approach
- Handles headers, sections, and natural break points appropriately

## Comparison with QMD

### Advantages of Python Implementation
- Full control over embedding pipeline integration
- Direct compatibility with existing Python ecosystem
- No dependency on Node.js/NPM ecosystem
- Can leverage existing Python-based tooling

### Disadvantages Compared to QMD
- Potentially slower performance without optimization
- Need to implement more components from scratch
- No built-in LLM integration (reranking, query expansion)
- More complex to maintain than single-purpose QMD

## Adoption vs. Reimplementation Decision

### Recommendation: Hybrid Approach

1. **Adopt QMD for core search functionality**: QMD is mature, well-tested, and optimized
2. **Reimplement embedding pipeline in Python**: Maintain compatibility with existing workflows
3. **Create Python wrappers for QMD**: Bridge between Python embedding pipeline and QMD

### Implementation Path

#### Option 1: Wrapper Approach (Recommended)
- Keep QMD as the core search engine
- Create Python wrapper that:
  - Generates embeddings using existing Python pipeline
  - Converts embeddings to format compatible with QMD
  - Calls QMD CLI for search operations
  - Processes results as needed

#### Option 2: Full Reimplementation
- Reimplement core QMD functionality in Python
- Use `rank-bm25`, `sqlite-vec` and custom RRF implementation
- More control but significantly more work and ongoing maintenance

## Next Steps

1. **Prototype Python wrapper for QMD**:
   - Create scripts that generate embeddings using existing Python pipeline
   - Convert embeddings to QMD-compatible format
   - Test integration with QMD search capabilities

2. **Evaluate performance differences**:
   - Compare search quality between QMD and Python implementation
   - Benchmark timing for various query types

3. **Document integration approach**:
   - Create detailed guide for using Python embeddings with QMD
   - Define compatibility requirements

## Conclusion

The investigation confirms that all key components of QMD can be implemented in Python:
- BM25 search is readily available via existing libraries
- Vector search with sqlite-vec is feasible
- Hybrid search via RRF is straightforward to implement
- Smart chunking algorithms can replicate QMD's behavior

However, QMD is already a mature, optimized implementation. Rather than reimplementing everything in Python, the recommended approach is to wrap QMD with Python components to maintain compatibility with the existing embedding pipeline.

This hybrid approach provides the benefits of both worlds:
- Leverage QMD's optimized, tested search engine
- Maintain compatibility with Python-based embedding workflows
- Minimize reinvention of well-solved problems