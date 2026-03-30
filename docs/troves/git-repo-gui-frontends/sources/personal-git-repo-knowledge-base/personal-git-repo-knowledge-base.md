---
source-id: "personal-git-repo-knowledge-base"
title: "A Personal Git Repo as a Knowledge Base Wiki - DEV Community"
type: web
url: "https://dev.to/adam_b/a-personal-git-repo-as-a-knowledge-base-wiki-j51"
fetched: 2026-03-30T18:04:37Z
hash: "f6229efc46d512e09df1163f48d73ed4efcbb31ca8a86883314a722f43e77bbc"
---

# A Personal Git Repo as a Knowledge Base Wiki

By Adam Braimah, February 19, 2021

While it's not something that everyone likes to do, I've always found it essential to write notes. There are the project-specific notes that only have relevance within a particular workplace and are of course confidential, but then the stacks of notes that cover everything from the content of the training course you last went on to "what's the command-line way to add a new project again?" - and that second category is the one we're going to discuss here.

Besides good old pen and paper I've tried all sorts, with tools like Evernote, Keep, the original Catch Notes (RIP), and Apple Notes each having very different levels of support for formatting, embedding, and crucially, portability of stored data. The latter becomes especially significant if the service closes down, or if (in the case of Apple Notes) you hand back the computer at the end of a job. As I looked at the pages of pencilled notes I'd written while following an online tutorial recently, I realised that a more unified and durable approach would be extremely useful. A solution flashed into my head while updating the wiki for a personal project on Bitbucket - why not have a private repo consisting entirely of Markdown notes, rather than code?

## Benefits

- Markdown is familiar to a large proportion of developers, is easy to write, and widely-supported - but also fairly readable even as plain text without a parser.
- Markdown has great support for inserting the kinds of things we so often need - code snippets, links, tables, and multi-level bullet lists - with minimal effort, allowing you to concentrate on the content.
- Using a Git repo makes it easy to quickly sync the notes across machines.
- This approach removes the reliance on proprietary sites. As each copy of the repo is just the same as any other, even the loss of your online Git account is not catastrophic.

## Basic Structure

The root of the repo has an `index.md` file, with each overall topic being contained in a folder - and each of these also contains an `index.md`. If it's a big enough topic, there might be an extra level, but the aim is just organised enough without having a crazy directory tree structure.

The root `index.md` contains links to the index files in each folder. Those index files, in turn, link to other `.md` files within their own directories for each article.

## Article Content

The beauty of this being your private repo is that you're not beholden to any particular standard - you can be free to write in as formal or as loose a way as you'd like. At some times you might have nothing but a raw text braindump, at others you may have topics that you can write on in a more structured way. The point that is central is that you write in the way that works for you, in the terms that make it the most useful for the way you read, think, and recall.

Code snippets (with the original spacing preserved) and shell commands can be inserted easily, as can links to external resources that might be useful for each topic.

In addition, now that everyone has a camera in their pocket, diagrams can be sketched, photographed, and included as inline images, rather than being laboriously reproduced with a computerised drawing tool.

As an aside, if you need to copy/paste formatted text from other document formats, PuppyPaste is a very handy tool which will convert the formatting to the Markdown equivalent, which you can then copy/paste/edit as necessary.

## Reading

The main online Git sites will support the viewing of Markdown files, but if you want to view them outside of this framework then a small amount of extra work is needed. As web browsers don't generally have native support for Markdown files, you can't get the benefit of using one as a viewer directly, but some very kind people have provided solutions to this. Someone recommended MDwiki and having used it, I will too.

Simply download the HTML file into the root of your repo, and rename it to `index.html`. Pointing a web server at this folder (I wrote an absolutely minimal one with Node.js and Express) makes it an HTML web-browsable wiki.

## Uses and Conclusion

I now have copies of my own repo on a Windows desktop, Mac laptop, and a USB flash drive, as well as on Bitbucket. A quick `git pull` on each grabs the latest changes as needed, and after that the notes are available even if there is no network available. I'll be continually adding to it and think that this is a solid way of preserving the jewels picked up along my development journey. I hope some of you find this approach useful too!
