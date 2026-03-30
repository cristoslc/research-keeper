---
source-id: "obsidian-data-lock-in-discussion"
title: "Is there a Data Lock-in Policy in Obsidian? — Forum Discussion on Portability and Proprietary Concerns"
type: web
url: "https://forum.obsidian.md/t/is-there-a-data-lock-in-policy-in-obsidian/25277"
fetched: 2026-03-30T18:04:37Z
hash: "958e232ba317b7b1845fc1a38362dca2b5f972eedb15d57f130fdb143519a3e5"
---

# Is there a Data Lock-in Policy in Obsidian?

Obsidian Forum, Basement category, October 2021

## Original Post (cloakboy)

Context: The Landing Page of Obsidian says in summary 'No Data Lock-in and Proprietary Format'.

### Thing I have tried

I have tried copying my essay I written in Obsidian using markdown to MS Word. I discovered a hack, first copy raw text to Typora, then from there to MS Word, but it messes with the formatting.

### What I want to do

I did not find a way to copy formatted text, though we can copy raw text to a place elsewhere. I just want to copy text from preview mode.

## Response (Hellquist)

I think you have mixed up the terminology. The "no data lock-in" is true for anything that is related to flat text files on your computer, for example Markdown files handled by Obsidian. It basically means you can use those files in any app that can handle Markdown, and you are not bound to use Obsidian to edit them. If you move away from Obsidian those files will be just as usable in for example VSCode with Foam, Marked app, iA Writer etc.

This is unlike Evernote, which has their own proprietary format for their data, and also actually unlike some other Markdown based solutions like Notion, which adds all kinds of extra tags to each unit (and which you have to sit and delete afterwards if you wish to export/use it in any other app than Notion).

What you are describing has nothing to do with data lock-in though. Also, I don't understand what doesn't work. If I preview a file in Obsidian, I select the contents in the preview window within Obsidian, copy it and then open MS Word and paste it in, it retains headlines, links, bolded text etc. It looks like crap as it will have been pasted as HTML (which is what the Obsidian Preview renders, just like all Markdown preview software) and Word isn't great for converting HTML in to something a user actually would like to keep, but hey, that falls on Microsoft, not Obsidian.

## Response (Dor)

One of the main reasons that docx files are so much bigger than plaintext is because they contain masses of instructions and formatting for output/printing to a wide range of devices at a given page size. Plaintext is just text, with markdown having a few bits of textual formatting. But not even underline. Designed, with the aid of CSS, for output into HTML, which again has much less formatting than word processor formats.

In general, it's best for writers to concentrate purely on writing with formatting as a second stage. With the formatting designed for a particular output. For those who can only see what they do in its fully formatted form, having been brought up with word processors which give the impression of making it easy, life is more difficult.

## Follow-up (cloakboy)

The problem was solved by copying text from preview mode after turning on light mode.

I saw a 'pure markdown export option' on the roadmap, but my concern is why the devs didn't implemented 'md to docx' as a built-in solution. I feel, it is just a method to secure the revenue model. I think instead of asking this, I should request someone to build a plugin for that. (md to docx)
