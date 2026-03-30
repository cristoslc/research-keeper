---
source-id: "gollum-github-readme"
title: "Gollum - A git-based Wiki (GitHub Repository README)"
type: web
url: "https://github.com/gollum/gollum"
fetched: 2026-03-30T18:04:37Z
hash: "72c89ab4054d430059a56e96c5c091fc138283a32881b25ac5040db2d8cb9f89"
---

# gollum - A git-based Wiki

Gollum is a simple wiki system built on top of Git. A Gollum Wiki is simply a git repository of a specific nature:

- A Gollum repository's contents are human-editable text or markup files.
- Pages may be organized into directories any way you choose.
- Other content can also be included, for example images, PDFs and headers/footers for your pages.
- Gollum pages:
  - May be written in a variety of markups.
  - Can be edited with your favourite editor (changes will be visible after committing) or with the built-in web interface.
  - Can be displayed in all versions, reverted, etc.
- Gollum strives to be compatible with GitHub and GitLab wikis.
  - Just clone your GitHub/GitLab wiki and view and edit it locally!
- Gollum supports advanced functionality like:
  - Diagrams using Mermaid or PlantUML
  - BibTeX and Citation support
  - Annotations using CriticMarkup
  - Mathematics via KaTeX or MathJax
  - Macros
  - Redirects
  - RSS Feed of latest changes

## System Requirements

Gollum runs both on Unix-like systems and on Windows.

Gollum runs either using 'normal' Ruby (MRI) or JRuby (Ruby on the Java Virtual Machine). On Windows, Gollum runs only using JRuby (either from source, or prebuilt).

On MRI, Gollum uses the rugged git library, while on JRuby/Java it utilizes the rjgit and JGit libraries.

## Installation

### As a Ruby Gem

Ruby is best installed either via RVM or a package manager of choice. Then simply:

```
gem install gollum
```

### Via Docker

See the wiki for instructions on how to run Gollum via Docker.

### As a Web Application Resource (Java)

The latest Release of Gollum will always contain a downloadable `gollum.war` file that can be directly executed on any system with a working Java installation:

```
java -jar gollum.war -S gollum <your-gollum-arguments-here>
```

## Markups

Gollum allows using different markup languages on different wiki pages. It presently ships with support for the following markups:

- Markdown (see below for more information on Markdown flavors)
- RDoc

You can easily activate support for other markups by installing additional renderers (any that are supported by github-markup):

- AsciiDoc -- `gem install asciidoctor`
- Creole -- `gem install creole`
- MediaWiki -- `gem install wikicloth`
- Org -- `gem install org-ruby`
- Pod -- requires Perl >= 5.10
- ReStructuredText -- requires python >= 3
- Textile -- `gem install RedCloth`

### Markdown Flavors

By default, Gollum ships with the `kramdown` gem to render Markdown. However, you can use any Markdown renderer supported by github-markup. This includes CommonMark support via the `commonmarker` gem.

## Running Gollum

### Quick Start from Command Line

1. Run: `gollum /path/to/wiki` where `/path/to/wiki` is an initialized Git repository.
2. Open `http://localhost:4567` in your browser.

## Command-Line Options

| Option | Arguments | Description |
| --- | --- | --- |
| `--host` | `[HOST]` | Specify the hostname or IP address to listen on. Default: '0.0.0.0'. |
| `--port` | `[PORT]` | Specify the port to bind Gollum with. Default: `4567`. |
| `--config` | `[FILE]` | Specify path to Gollum's configuration file. |
| `--ref` | `[REF]` | Specify the git branch to serve. Default: `main`. |
| `--bare` | | Tell Gollum that the git repository should be treated as bare. |
| `--adapter` | `[ADAPTER]` | Launch Gollum using a specific git adapter. Default: `rugged`. |
| `--base-path` | `[PATH]` | Specify the leading portion of all Gollum URLs (path info). |
| `--page-file-dir` | `[PATH]` | Specify the subdirectory for all pages. If set, Gollum will only serve pages from this directory and its subdirectories. |
| `--css` | | Tell Gollum to inject custom CSS into each page. Uses `custom.css` from wiki root. |
| `--js` | | Tell Gollum to inject custom JS into each page. Uses `custom.js` from wiki root. |
| `--no-edit` | | Disable the feature of editing pages. |
| `--allow-uploads` | `[MODE]` | Enable file uploads. If set to `dir`, stores uploads in `/uploads/`. If set to `page`, stores at currently edited page. |
| `--math` | `[RENDERER]` | Enable rendering of mathematical equations. Valid: `mathjax`, `katex`. |
| `--critic-markup` | | Enable support for annotations using CriticMarkup. |
| `--h1-title` | | Tell Gollum to use the first `<h1>` as page title. |
| `--no-display-metadata` | | Do not render metadata tables in pages. |
| `--emoji` | | Parse and interpret emoji tags. |
| `--lenient-tag-lookup` | | Internal links resolve case-insensitively, treat spaces as hyphens, match first page found anywhere in repo. |

14.2k stars, 1.6k forks. Written in Ruby 44.9%, JavaScript 34.5%. MIT licensed.
