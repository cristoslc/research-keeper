---
source-id: "adaptive-progressive-summarization-hf"
title: "Distilling from Dialogues: Finding Meaning in LLM Interactions — Adaptive/Progressive Summarization"
type: web
url: "https://huggingface.co/blog/chansung/adaptive-summarization"
fetched: 2026-03-30T18:04:37Z
hash: "37cda5f72b135ef9d6ad500a57b4a80aacb463ec3c00a4a54d7f7a774a1ae8f4"
---

# Distilling from Dialogues: Finding Meaning in LLM Interactions

chansung park | February 25, 2025 | Hugging Face Community Article

In the age of Large Language Models (LLMs), engaging in conversations with AI has become increasingly common. However, as these interactions grow longer and more complex, keeping track of the key information and insights can become a challenge. This is where the need for a personalized conversation summarization tool arises, helping users distill the essence of their LLM dialogues and retain valuable knowledge.

This project, called **Adaptive/Progressive Summarization**, aims to address this challenge by providing a unique approach to LLM conversation summarization. Unlike generic summarization methods, the project focuses on creating **personalized summaries that reflect the individual user's interactions and needs**. By tailoring the summarization process to each user, the generated summaries are not only accurate but also relevant and meaningful to the individual.

One of the key features is the **progressive summarization technique**. Instead of generating a completely new summary for each interaction, it **refines and enhances the existing summary based on the latest conversation**. This approach ensures consistency and avoids the problem of disjointed summaries. By incrementally building upon the previous summary, a comprehensive and cohesive record of the entire LLM interaction is created.

## Case Study

At the heart of this project lies the crucial role of prompt engineering. The system prompt guides the LLM toward generating accurate and relevant summaries:

```
## System Prompt

Based on the given summary and the last conversation between you (assistant) and me (user),
update the summary following the below summary guide.

Summary Guide:
* Do not rewrite the entire summary.
* It is allowed to modify the current summary, but do not eliminate.
* Update only the specific portions necessary to reflect new information or changes.
* Only include information we have explicitly discussed.
* Do not introduce any new information or topics, even if you have prior knowledge.
* Ensure the summary is factually accurate and reflects the nuances of our discussion.
* While being detailed, also aim for conciseness and clarity in the summary.
* Use markdown formatting to make the summary more readable.
* Do not separate sections for previous and updated summaries.
```

### How the summary evolves — case study on paper "s1: Simple test-time scaling"

**First summary: "what is this paper about?"**
After a simple question, the model gave a well-written and sufficiently detailed summary covering the paper's problem, approach, methodology, results, contributions, and key ideas.

**Second summary: "how did the author collect reasoning traces?"**
The updated summary accurately mentions the "Google Gemini Flash Thinking API" — and only the part dealing with reasoning traces was updated, leaving the rest completely untouched.

**Third summary: "s1-32B model is fine-tuned to understand 'wait' token?"**
Again, only the relevant part was updated properly, adding that the model is fine-tuned to understand the "Wait" token as a signal to continue reasoning.

**Fourth summary: "what are the limitations of this work?"**
Limitations were appended at the end of the summary without affecting other parts, covering: performance plateau, context window constraints, limited extrapolation, repetitive loops, generalizability concerns, dataset size dependency, pre-trained model dependency, and limited exploration of parallel scaling methods.

## Design of User Interface

To track how the summary changes over time, a Gradio-based application was developed. Within the application, you can navigate the history of summaries and compare them. Highlighted texts in green mean additions, while texts in red mean subtractions compared to the previous summary. A "Download" button allows storing what you've learnt after a long conversation.

The application is hosted on Hugging Face Space, and source codes are managed in a GitHub repository.

**Key insight**: The progressive summarization technique demonstrates that AI-generated summaries can be living documents that evolve incrementally as new information is discussed, rather than being regenerated from scratch each time. Only relevant portions are updated while maintaining the coherence of the whole.
