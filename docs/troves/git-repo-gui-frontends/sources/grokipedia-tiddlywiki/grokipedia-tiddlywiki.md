---
source-id: "grokipedia-tiddlywiki"
title: "TiddlyWiki - Grokipedia"
type: web
url: "https://grokipedia.com/page/TiddlyWiki"
fetched: 2026-03-30T18:04:37Z
hash: "5a36ffc518f1aec83d3d557122848341c7524b3ab20e5c63d99b4db14627edd8"
---

# TiddlyWiki

TiddlyWiki is a non-linear personal web notebook that functions as a complete interactive wiki implemented entirely in JavaScript, stored within a single HTML file that combines both the application code and user data, requiring only a web browser for operation. It enables users to capture, organize, and share complex information through small, interlinked content units known as **tiddlers**, which support rich text, images, macros, and hyperlinks for flexible, non-hierarchical structuring. Created by British software developer Jeremy Ruston, TiddlyWiki was first released on 20 September 2004 as an open-source project emphasizing privacy and portability.

Since its inception, TiddlyWiki has evolved through multiple versions, with the current major iteration, TiddlyWiki 5 (released in 2013 and actively maintained), introducing advanced features like plugin extensibility and server-side capabilities via Node.js. Key enhancements include a hackable WikiText markup language for content creation, support for dynamic filters to query and display tiddlers, and integration with external services for synchronization and backups, making it suitable for personal knowledge management, project planning, or even full websites. The tool's single-file format allows easy portability across devices, while its plugin ecosystem -- managed through an official library -- enables users to add functionalities like themes, search enhancements, and data import/export without altering the core code.

## Overview and Purpose

TiddlyWiki is a non-linear personal web notebook designed for capturing, organizing, and sharing complex information in an associative, hypertext format. Implemented entirely as a single HTML file, it encapsulates all content, structure, and interactive functionality through embedded JavaScript, requiring no installation or external dependencies beyond a standard web browser. This self-contained design enables seamless portability, allowing users to open and use the notebook offline on any device without server reliance.

The primary purpose of TiddlyWiki is to facilitate personal knowledge management by enabling users to link and retrieve ideas fluidly, making it suitable for note-taking, idea brainstorming, or lightweight project coordination where traditional linear tools fall short. Unlike conventional databases or document editors, it supports hypertext navigation to mimic the interconnected nature of human thought, promoting efficient retrieval and reorganization of information.

## Key Characteristics

- **Single-file architecture:** Encapsulates the entire wiki -- including all content, code, and functionality -- within one self-contained HTML file that requires no external server, database, or installation beyond a web browser. Initial file size is approximately 2.4 MB for an empty wiki.
- **Browser-based execution:** Executes entirely in the browser using JavaScript, facilitating offline editing and ensuring cross-platform compatibility across operating systems.
- **Associative structure:** Based on hyperlinked content units called tiddlers, eschewing rigid hierarchies in favor of flexible, non-linear organization that supports dynamic views such as timelines, indexes, and searches.
- **Extensibility without programming:** Leverages built-in WikiText for customizations and supports transclusion to embed content from one tiddler directly into another for reusable, modular composition.
- **Privacy and security:** Prioritizes local file storage by default, where all data resides on the user's device with no automatic cloud synchronization or external data transmission unless explicitly configured.

## Core Concepts: Tiddlers

In TiddlyWiki, tiddlers represent the smallest atomic units of information, functioning as modular, reusable chunks of content similar to digital notecards. Each tiddler encapsulates a discrete idea, fact, or element. The structure of a tiddler consists of fields (key-value pairs storing both content and metadata):

- `title` -- unique identifier
- `text` -- main body content
- `tags` -- space-separated list for categorizing and filtering
- `created` -- timestamp of initial creation
- `modified` -- timestamp of the last update
- `type` -- specifies rendering instructions (e.g., "text/x-markdown" for Markdown parsing or "application/json" for data storage)

Types of tiddlers: ordinary tiddlers (standard user content), draft tiddlers (temporary workspaces for edits), and shadow tiddlers (predefined, immutable defaults loaded from plugins at startup).

## Macros and Widgets

Macros are reusable snippets of WikiText that can be invoked to perform specific tasks, such as formatting dates or generating lists. Widgets provide structured UI elements that render content based on filters and attributes. Central to widgets like `<$list>` is TiddlyWiki's filter language, a pipeline of operators that selects, sorts, and manipulates sets of tiddler titles. Example: `[tag[important]sort[title]]` queries tiddlers tagged "important" and sorts them by title.

## Plugins and Customization

TiddlyWiki's plugin system enables users to extend core functionality by installing bundles of tiddlers that encapsulate JavaScript modules, CSS stylesheets, templates, and other content. Installation is straightforward: users download plugins as `.tid` files from the official library and drag them directly into the open wiki. Over 500 community-contributed plugins are available.

Notable plugins include: LaTeX Plugin for mathematical equations, Gantt Plugin for project timeline visualizations, Encryption Plugin for password-protected tiddler encryption, and a Markdown plugin for standard Markdown support.

Customization extends to theming, where users create or modify StyleSheet tiddlers to inject custom CSS rules directly into the wiki's rendering cascade.

## Saving and Synchronization

Default saving relies on the HTML5 saver: edits trigger a "dirty state," and upon clicking save, the browser prompts the user to download an updated single HTML file. Alternative saving methods include:

- Node.js edition: writes tiddlers as individual text files to the local file system
- BrowserStorage plugin: stores tiddlers in the browser's localStorage API
- External tools like Dropbox for cloud synchronization

Advanced options include built-in password protection through AES-128 encryption, and MultiWikiServer for collaborative environments supporting multiple simultaneous users.

## History

Created by Jeremy Ruston in September 2004. V2 released in late 2004, introducing transclusion and macros. The transition to V5 began around 2012, as a comprehensive rewrite to support modern browsers, mobile devices, and improved performance. Current stable version is 5.3.8, released on August 7, 2025.

## Current Development

Recent advancements in 2025 center on expanding server-side capabilities through MultiWikiServer (Node.js-based plugin for hosting multiple wikis with SQLite/MySQL support). Mobile responsiveness improvements include a native iOS app using SwiftUI. The 2025 community survey highlights user demands for AI tool integrations and enhanced search functionalities.

## Alternatives

In 2026, modern alternatives include Obsidian (local Markdown files with plugins and graph views), Logseq (open-source outliner with block-level notes), and Feather Wiki (lightweight single-file wiki at 58 KB).
