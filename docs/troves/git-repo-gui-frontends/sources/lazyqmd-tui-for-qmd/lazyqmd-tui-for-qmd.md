---
source-id: "lazyqmd-tui-for-qmd"
title: "Introducing lazyqmd: a TUI for QMD - and a little more..."
type: web
url: "https://alexanderzeitler.com/articles/introducing-lazyqmd-a-tui-for-qmd/"
fetched: 2026-03-30T18:04:37Z
hash: "9e08f275b3ca41ce241f9463430f1d48eeed59ae01fa1d0a13b3fcb17483dd92"
---

# Introducing lazyqmd: a TUI for QMD - and a little more...

*Published on Friday, February 13, 2026 - Alexander Zeitler*

## What's it all about?

QMD is a quite popular mini cli search engine for your docs, knowledge bases, meeting notes, whatever. `qmd` has been created by Tobi Luetke, the founder of Shopify and can be found on GitHub.

It allows you to index Markdown files from several locations on your computer. You can search with keywords or natural language. QMD combines BM25 full-text search, vector semantic search, and LLM re-ranking -- all running locally via node-llama-cpp with GGUF models.

After installing it, you can add a new collection like this:

```
qmd collection add ~/notes --name notes
```

Now all Markdown files under `~/notes` will be indexed and be searched. `qmd` also provides an MCP server, so you can integrate it as a memory server into your agentic workflows:

```
qmd mcp --http
```

## Introducing lazyqmd

As with `qmd` itself, `lazyqmd` can be installed using `bun`:

```
bun install -g lazyqmd
```

To use all features, make sure to start the `qmd` MCP server in daemon mode. If you stick with the default port, you're good to go.

Now start `lazyqmd`:

```
lazyqmd
```

If starting from scratch without prior usage of `qmd`, you'll have no collections and `lazyqmd` will look empty. You can add a collection by pressing `a` -- this brings up a dialog to add a new collection (with tab completion for the path).

Wait until the `Indexing...` message disappears. Once indexed, you can navigate collections in the left sidebar using up/down arrows and start a new search by pressing `/`.

### Search modes

By hitting `<CTRL+T>` you can switch between:
* **search** - regular BM25 full-text search
* **vsearch** - QMD Vector search (semantic)
* **query** - hybrid search with re-ranking

For `vsearch`, make sure you've created embeddings first (press `<e>` on the main screen with a collection selected to run `qmd embed`).

### Document preview

When viewing search results, press `<tab>` to jump to the results list, then `Enter` to open a document. The preview includes syntax highlighting for Markdown and YAML frontmatter.

### HTML preview

Within the Markdown preview, press `<p>` to open an HTML preview in Chrome/Chromium/Brave in app mode.

### Edit integration

Press `<e>` to seamlessly open the Markdown file in your `$EDITOR` (e.g., neovim). When saving changes, they are reflected in the HTML preview. Quitting the editor brings you back to lazyqmd.

### Conclusion

After building this, the author notes: "this little TUI + QMD might replace LogSeq and Obsidian for me: file based, run locally and I can have my files where they belong to."

The project provides a terminal-based GUI layer over QMD's semantic search capabilities, turning it from a CLI tool into a browseable knowledge base interface with search, preview, edit, and HTML rendering -- all running locally.
