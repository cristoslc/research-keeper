---
source-id: "building-knowledge-graph-obsidian"
title: "Building a personal knowledge graph on Obsidian"
type: web
url: "https://ericmjl.github.io/blog/2020/12/15/building-a-personal-knowledge-graph-on-obsidian/"
fetched: 2026-03-30T18:04:37Z
hash: "be4cc69a23079ad1f63c496223ee20e7057ad0338c88939fbc027c077787329f"
---

# Building a personal knowledge graph on Obsidian

By Eric J. Ma, December 15, 2020

On a recent vacation, since we've got nowhere to go, I decided to re-examine how I made notes in my personal and professional lives. The result is a lot of lessons learned into effective notetaking, and me building yet another thing.

Amidst COVID-19, I decided to take a break from work. During this personal rejuvenation time, I stumbled upon Andy Matuschak's notes, which are famous amongst the "personal knowledge management" community.

At the same time, I also saw the rise of Roam Research and Obsidian, and I was looking with envious eyes at those who had early access to Roam. I was a bit turned off by the subscription and lock-in that characterized Roam and was much more attracted to the Freemium + "respect your data rights" model embraced by Obsidian, so I dipped my toes in. The result is this learning journey building my own "personal knowledge management" system from which I've never turned back.

For a long time, I've known that the way that I think is in a "linked" fashion. I rarely entertain a thought on its own in isolation. Instead, I will jump and hop from one idea to another in my brain. Sometimes, I joke with others that my mind is effectively a random graph: nodes are ideas, and edges are relationships between them. The unfortunate thing is that I don't have the right tools for externalizing the relationships that I uncover.

My previous notetaking tool, Evernote, is better described as an archival tool. Using it as a tool for developing and understanding ideas is a bit like treating a flea market as a museum. Yes, it's a collection of items, but a flea market has everything and anything in there, while a museum is intentionally curated. Intentional curation is the key to internalizing insights from the external knowledge we gain.

## How Obsidian Helps

There are at least three features of Obsidian that help with this.

### Markdown files

Obsidian treats individual notes, implemented as Markdown files, as the unit on which linking happens. When you want to create a wiki-style link to another page, you use a double square bracket (`[[...]]`) and start typing the name of the note that you want to link. A pop-up display will show the note titles, which can help you if you have a fuzzy or approximate notion of the idea you're trying to link. If you use "imperative tone" ideas to name your note files, then linking becomes even more natural.

### Graph view

Obsidian has a graph view. This graph view is nothing more than a node-link diagram, likely implemented using d3.js, with note titles overlaid. Yes, it is fascinating to explore our ideas' connected structure, but the more significant value proposition is quickly identifying every note file that exists as an unlinked singleton. Why? Because one of the goals of linked notetaking is to search for linkable ideas and then explicitly connect them. The visual graph view also helps me surf through concepts; each time I trace a path between the thoughts I've recorded down, I reinforce the link in my unreliable internal store.

### Random notes

Obsidian has a "show me a random note" feature. This feature helps me ruminate through ideas. It's the digital equivalent of me jumping through concepts in my head, except now I have a reliable external store for ideas (Obsidian) rather than an unreliable internal store (my brain). Surfacing up random notes is an extremely excellent way of hopping through my knowledge graph to surface up ideas in a spaced repetition fashion, allowing my mind to uncover and create connections between ideas that I might not have made otherwise.

### Plain text

One other notable feature makes me trust Obsidian over other notetaking services. That feature is Obsidian's choice to rely on simple Markdown files as the unit on which linking happens. This choice stands in contrast to Evernote's expanded XML syntax, which, though open, is not plain enough to have a low barrier to parsing. The choice also stands in contrast to Roam's and Notion's choice to link individual blocks of text, which requires additional tech that, almost by definition, requires specialized data structures — again, being not low enough of a barrier. Effectively, with Obsidian, I own my data, stored using the lowest common denominator of computing: text files.

## Tips for using Obsidian

### Each Markdown file as a single unit of thought

The first tip I picked up was to treat each Markdown file as a coherent and atomic unit of thought. This tip is something I picked up directly from Andy Matuschak's notes, and I believe this is the most crucial tip to making a system like this work. In doing so, we are nudging ourselves to compose a coherent and atomic unit of thought, to which we can establish relationships to other similarly-constructed ideas. Writing them down takes effort, so this mode of notetaking is not for the "collector" type; instead, it is for intentional curators.

### Actively connect ideas

The second tip I picked up was to intentionally try to establish as many connections between ideas as possible. Andy Matuschak calls this "linking densely," and this action is essential: it is how we construct our knowledge graph! A way to make these links is to think of ideas as imperative statements that we make; inside the note, we elaborate on the concept with, say, supporting evidence.

### Tend to the knowledge garden regularly

A third tip that I uncovered through experience is to treat the knowledge graph as a garden that requires regular tending. For me, tending implies:

1. Leveraging the random note feature to find old ideas buried beneath the more recent things I have been thinking about,
2. Browsing through Obsidian's graph view to locate singleton notes and trace paths through them, and
3. Ruminating over the notes at a later date using the random notes feature.

## My notes made public

I've written a lot about how I've used Obsidian to help me organize my knowledge. In line with the principle of working in the open, I put my notes online at https://ericmjl.github.io/notes/, available for others to see, and so that I can reference them when I interact with others.
