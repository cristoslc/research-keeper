---
source-id: "selfhosted-reddit-markdown-wiki-discussion"
title: "r/selfhosted Discussion: Markdown based wiki I can git push to?"
type: web
url: "https://www.reddit.com/r/selfhosted/comments/oe7xpp/markdown_based_wiki_i_can_git_push_to/"
fetched: 2026-03-30T18:04:37Z
hash: "fedb7657f6f1d26f7d62bbdf26e0969db670dec12be7a3a2b0ca811073c7696c"
---

(Note: Reddit blocked direct page fetch. Content reconstructed from search snippets.)

# Markdown based wiki I can git push to? (r/selfhosted)

Original poster (killermenpl): "I'm looking for a Markdown based wiki software, but with the requirement that I can write markdown on my machine and then git push it to wiki. So far I found some that (can) use git internally, but any changes must still be made through web interface. The closest I found was Gitlab's built-in wiki, but it can only exist as part of a project, not on it's own."

## Notable responses (28 votes, 36 comments):

- **Flowershow.app**: "You can use https://flowershow.app/ for this - turn markdown and especially obsidian markdown into a wiki-like site."

- **Git repo browser as wiki**: "To provide a different option- have you considered just exposing a Git repo browser (such as Gitlab's, or any of the lighter ones, like Gitiles or whatever)? Most of them render Markdown and handle links, so you might get by with just that and save a bit of complexity."

- **MkDocs recommendation**: "I had the same requirements as you, and MkDocs has worked wonderfully well for me. You can use this repository as an example: https://github.com/selfhostedshow/wiki/"

- **Wiki.js note**: "Seems to me like it can sync with an external repository instead of providing a git repository of it's own."

- **MDWiki**: "It's no longer maintained, but MDWiki might work for you. Still works for me for some basic needs."

- **doc-store-template**: "if you just want github to render your wiki, I have a repo that you could try - https://github.com/mhzawadi/doc-store-template"

Key insight from the thread: Many users want to write markdown locally, push to git, and have it rendered as a wiki -- but most wiki engines expect edits through their web interface, with git sync as a secondary feature rather than the primary authoring path.
