---
source-id: "reddit-llm-wiki-bad-idea"
title: "We built Karpathy's LLM Wiki - The LLM read it, understood it, and ignored it anyway"
type: forum
url: "https://www.reddit.com/r/LLM/comments/1smd9sz/we_built_karpathys_llm_wiki_the_llm_read_it/"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
participants:
  - "u/Kooky_Arrival_8588"
  - "various commenters"
post-count: 3
---

# We built Karpathy's LLM Wiki - The LLM read it, understood it, and ignored it anyway

Subreddit: r/LLM
Votes: 28
Comments: 3
Posted by: u/Kooky_Arrival_8588

## Original Post

Built Karpathy's LLM Wiki pattern. The LLM read the sources, appeared to understand them, and then ignored the compiled wiki content when generating answers. This raises serious questions about whether the compilation step actually delivers on its promise.

## Key Discussion Points

**Semantic gravity problem**: The words `FINAL_REASON` hold more weight semantically than anything else inside the wiki. LLM models are trained to confidently guess rather than confidentially know. This can be proven by looking at the models Claude and Codex throw away — which are models that give an "unsure" or "I don't know" answer rather than a confident guess.

**The LLM finds certain words and boldly assumes they MUST be important**, even if other sources tell it that's not true. The model's training bias overrides the carefully compiled wiki content.

**Mitigation attempt**: Intercept the query and filter out problematic columns before letting the LLM process the data. This is a pre-processing step that addresses the symptom but not the root cause — that LLMs have semantic biases that can override curated knowledge.

**Connection to other reports**: This post resonates with broader concerns about LLM reliability when reasoning over structured content. The compiled wiki may be correct, but the model's weight priors can still lead it astray.