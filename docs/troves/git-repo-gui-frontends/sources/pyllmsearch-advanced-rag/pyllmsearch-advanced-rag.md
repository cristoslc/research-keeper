---
source-id: "pyllmsearch-advanced-rag"
title: "pyLLMSearch - Advanced RAG for querying local documents"
type: web
url: "https://github.com/snexus/llm-search"
fetched: 2026-03-30T18:04:37Z
hash: "e7d135f83881ccc5c125f4fd138f7a334c1a5cfddb72b119eea06633ef775e48"
---

# pyLLMSearch - Advanced RAG

649 GitHub stars. MIT License.

The purpose of this package is to offer an advanced question-answering (RAG) system with a simple YAML-based configuration that enables interaction with a collection of local documents. Special attention is given to improvements in various components of the system **in addition to basic LLM-based RAGs** - better document parsing, hybrid search, HyDE, chat history, deep linking, re-ranking, the ability to customize embeddings, and more. The package is designed to work with custom Large Language Models (LLMs) -- whether from OpenAI or installed locally.

Interaction with the package is supported through the built-in frontend, or by exposing an MCP server, allowing clients like Cursor, Windsurf or VSCode GH Copilot to interact with the RAG system.

## Features

* Fast parsing and embedding of medium size document bases (tested on up to few gigabytes of markdown and pdfs)
* Incremental updates for new documents, without a need to re-index the entire document base
* Supported document formats:
  - `.md` - Divides files based on logical components such as headings, subheadings, and code blocks. Supports additional features like cleaning image links, adding custom metadata, and more.
  - `.pdf` - MuPDF-based parser
  - `.docx` - custom parser, supports nested tables
  - Other common formats supported by Unstructured pre-processor
* FastAPI based API + MCP server, allowing communicating with RAG via any MCP client, including VSCode/Windsurf/Cursor and others
* Deep linking into document sections - jump to an individual PDF page or a header in a markdown file
* Allows interaction with embedded documents, supporting:
  - OpenAI compatible models and APIs
  - HuggingFace models
  - Interoperability with LiteLLM + Ollama via OpenAI API, supporting hundreds of different models
* SSE MCP Server enabling interface with popular MCP clients
* Hybrid search and Reranking:
  - Dense embeddings stored in ChromaDB
  - Embedding models: HuggingFace, Sentence-transformers, Instructor-based, OpenAI
  - Sparse embeddings using SPLADE for hybrid search (sparse + dense)
  - "Retrieve and Re-rank" strategy with ms-marco-MiniLM, bge-reranker-v2-m3, and zerank-2 cross-encoders
* Support for table parsing via open-source gmft or Azure Document Intelligence
* Optional image parsing using Gemini API
* HyDE (Hypothetical Document Embeddings) support - generates hypothetical answers to bridge terminology gaps when learning new topics
* Multi-querying inspired by RAG Fusion - original query replaced by 3 variants offering different angles/perspectives
* Optional chat history with question contextualization
* Simple web interfaces
* Ability to save responses to an offline database for future analysis
