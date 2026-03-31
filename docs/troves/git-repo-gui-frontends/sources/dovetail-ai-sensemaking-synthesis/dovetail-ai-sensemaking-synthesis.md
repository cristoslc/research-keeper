---
source-id: "dovetail-ai-sensemaking-synthesis"
title: "Dovetail AI — Sensemaking and Synthesis for User Research Data"
type: web
url: "https://docs.dovetail.com/help/dovetail-ai"
fetched: 2026-03-30T18:04:37Z
hash: "085a855cfc8a89b807dfd5cc3960cae2e6c8d657ded046ac1ed7174e2b42a197"
---

# Dovetail AI

## Overview

Leverage Dovetail's AI Magic features to speed up analysis, generate insights, and answer important questions about your customer data. Dovetail indicates when AI has contributed to your analysis and content in the workspace. The blue magic shuriken icon appears as a contributor on summaries, insights, and any other AI-generated content. If a user edits a summary or accepts a highlight, their avatar is also added, making it easy to see where human input was involved.

## What Dovetail AI can do

### Answer questions about your data
Powered by the latest release of Claude, chat allows you to **conversationally query everything from sales calls to support tickets, with every answer traced back to the source**. It instantly understands your context — whether you're looking at a single transcript or document, an entire project or channel, a specific folder, or even looking across your whole workspace.

### Transcribe video and audio calls
Powered by Amazon Transcribe and Assembly AI, import video and audio files into a project and Dovetail automatically detects the spoken language to generate a transcript.

### Generate insight reports
**Magic insight** provides a powerful starting point, handling the initial heavy lifting of synthesis so you can focus on refining, validating, and driving action with your stakeholders. Use pre-defined prompts or create your own to quickly **synthesize and structure your data**, powered by Claude.

### Analyze high-volume data with Channels
Using LLM and ML techniques, **Channels continuously analyzes incoming data and classifies it**, allowing you to track themes in large data sets, such as support tickets, app reviews, product feedback, and NPS/CSAT. This represents a "living summary" approach where the analysis updates as new data arrives.

### Summarize data in Projects and Channels
Save time identifying key themes in interviews, documents, or customer feedback, and turn them into valuable insights using **Magic summaries**. Add data to your project — including content like PDFs, reels, and transcripts — and Dovetail automatically generates a summary of the key points.

### Translate summaries and transcripts
Translate entire transcripts and summaries in 75 different languages to simplify knowledge sharing across global teams.

### Capture highlights in project data
Automatically find and highlight key moments in customer interviews, sales calls, and usability tests with **Magic highlight**. Magic highlight also uses your existing tag structure to automatically classify and group highlights.

### Cluster highlights on canvas view
Use **Magic cluster** to automatically group highlights with thematic similarities on your canvas view. Themes are created from the content of your highlights, not the tags or titles. Titles are automatically generated for each group.

### Summarize search results
**Magic summaries in search** are automatically generated to include the most relevant results to your search query.

### Redact text, audio, and video
Redact helps teams protect participant PII by blurring and muting video and audio, and redacting text in transcripts.

## Data security

* Dovetail uses tailored processing infrastructure on AWS — user data is NOT used to train models for Dovetail or other customers
* Models are deployed in the same place data is stored; the request is sent to the model, and the response is returned
* A variety of market-leading LLMs are used depending on the task (Claude for chat and synthesis, ML for transcription and sentiment analysis)
* AI is foundational to many of Dovetail's core features, including transcription and sentiment analysis

## Key design pattern: Browsing synthesized knowledge alongside raw sources

Dovetail's architecture demonstrates the pattern of **showing generated understanding alongside raw material**:
- Raw data (interview transcripts, support tickets, feedback) lives in Projects and Channels
- AI-generated summaries, highlights, and insight reports are layered on top
- Chat allows querying across both raw and synthesized content
- Canvas view lets you visually cluster and organize AI-identified themes
- Every AI contribution is visually marked so users can distinguish human from AI analysis
- The system continuously processes incoming data (Channels), making summaries living documents that evolve
