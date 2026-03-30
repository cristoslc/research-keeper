---
source-id: "gollum-wikipedia"
title: "Gollum (software) - Wikipedia"
type: web
url: "https://en.wikipedia.org/wiki/Gollum_(software)"
fetched: 2026-03-30T18:04:37Z
hash: "ab2c1aa7dbaa018d32b72dfff22f0a344a1e2b4426ddfbfd980d07bb086b66c8"
---

**Gollum** is wiki software that uses Git as the backend storage mechanism, and written mostly in Ruby. It started life as the wiki system used by the GitHub web hosting system. Although the open source Gollum project and the software currently used to run GitHub wikis have diverged from one another, Gollum strives to maintain compatibility with the latter. Currently used by GitLab to store and interconnect wiki-pages with wiki-links; a complete move away from Gollum is planned for the future.

## Formats supported

Gollum wikis are simply Git repositories that adhere to a specific format. Gollum pages may be written in a variety of formats including Markdown, AsciiDoc, ReStructuredText, Creole and MediaWiki markup.

## Features

- YAML Frontmatter for controlling per-page settings
- UML diagrams via PlantUML
- BibTeX and citation support (when using Pandoc for rendering)
- Annotations using CriticMarkup
- Mathematics via MathJax
- Macros
- Redirects
- Support for right-to-left languages

## Editing

Editing the pages can be done via the provided web interface, via its API or with a text editor directly in the Git repository.

| Detail | Value |
| --- | --- |
| Original authors | Tom Preston-Werner, Rick Olson, Dawa Ometto, Bart Kamphorst |
| Developers | GitHub and community |
| Initial release | February 16, 2009 |
| Stable release | 6.1.0 / 23 December 2024 |
| Written in | Ruby |
| Operating system | Unix-like, macOS, Windows |
| Type | wiki software |
| License | MIT License |

## See also

- ikiwiki -- Also uses a version control system to store pages
