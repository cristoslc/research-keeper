---
source-id: "sourcegraph-code-search-features"
title: "Code Search Capabilities - Sourcegraph docs"
type: web
url: "https://sourcegraph.com/docs/code-search/features"
fetched: 2026-03-30T18:04:37Z
hash: "510417384365ae4f13c2320b233d04c26391ab9c56633ec7bb8e374ecc5c8195"
---

# Code Search Capabilities

Learn and understand more about Sourcegraph's Code Search features and core functionality.

## Query assist

Query assist lets you describe what you're looking for in plain natural language. A custom-trained large language model translates your input into a precise Sourcegraph search query, so you can search effectively without memorizing the entire query syntax.

## Powerful, flexible queries

Sourcegraph code search performs full-text searches and supports both regular expression and exact queries. By default, Sourcegraph searches across all your repositories. Our search query syntax allows for advanced queries, such as searching over any branch or commit, narrowing searches by programming language or file pattern, and more.

## Data freshness

Searches scoped to specific repositories are always up-to-date. Sourcegraph automatically fetches repository contents with any user action specific to the repository and makes new commits and branches available for searching and browsing immediately.

Unscoped search results over large repository sets may trail latest default branch revisions by some interval of time. This interval is a function of the number of repositories and the computational resources devoted to search indexing.

## Commit diff search

Search over commit diffs using `type:diff` to see how your codebase has changed over time. This is often used to find changes to particular functions, classes, or areas of the codebase when debugging.

You can also search within commit diffs on multiple branches by specifying the branches in a `repo:` field after the `@` sign. After the `@`, separate Git refs with `:`, specify Git ref globs by prefixing them with `*`, and exclude a commit reachable from a ref by prefixing it with `^`. Diff searches can be further narrowed down with parameters that filter by author and time.

## Commit message search

Searching over commit messages is supported in Sourcegraph by adding `type:commit` to your search query. Separately, you can also use the `message:"any string"` parameter to filter `type:diff` searches for a given commit message. Commit message searches can narrowed down further with filters such as author and time.

## Symbol search

Searching for symbols makes it easier to find specific functions, variables, and more. Use the `type:symbol` filter to search for symbol results. Symbol results also appear in typeahead suggestions, so you can jump directly to symbols by name. When on an indexed commit, it uses Zoekt. Otherwise it uses the symbols service.

## Saved searches

Saved searches let you save and describe search queries so you can easily monitor the results on an ongoing basis. You can create a saved search for anything, including diffs and commits across all branches of your repositories. Saved searches can be an early warning system for common problems in your code and a way to monitor best practices, the progress of refactors, etc.

## Search contexts

Search contexts help you search the code you care about on Sourcegraph. A search context represents a set of repositories at specific revisions on a Sourcegraph instance that will be targeted by search queries by default.

Every search on Sourcegraph uses a search context. Search contexts can be defined with the contexts selector shown in the search input, or entered directly in a search query.

## Multi-branch indexing

The most common branch to search is your default branch. To speed up this common operation, Sourcegraph maintains an index of the source code on your default branch. Some organizations have other branches that are regularly searched. To speed up search for those branches, Sourcegraph can be configured to index up to 64 branches per repository.

## Exclude files and directories

You can exclude files and directories from search by adding the file `.sourcegraph/ignore` to the root directory of your repository. Files or directories matching the glob patterns will not show up in the search results.

## RE2 Regular Expressions

The Sourcegraph search language supports RE2 syntax. If you're used to tools like Perl which uses PCRE syntax, you may notice that there are some features that are missing from RE2 like backreferences and lookarounds. We choose to use RE2 for a few reasons:

- It makes it possible to build worst-case linear evaluation engines, which is very desirable for building a production-ready regex search engine.
- It's well-supported in Go, allowing us to take advantage of a rich ecosystem (notably including Zoekt).
- Our API and tooling makes it straightforward to use Sourcegraph with other tools that provide facilities not built in to the search language.

## Search experience

Users on Sourcegraph instance v5.9.0 or more get the improved and new Code Search experience set by default. You get the following improvements:

- In-line diff view: Easily compare commits and see how a file changed over time, all in-line
- Revamped code navigation: Quickly find a list of references of a given symbol, or immediately jump to the definition
- Reworked fuzzy finder: Find files and symbols quickly and easily with our whole new fuzzy finder
- File actions: Like open in editor and open on code host

## Personalized search ranking

Sourcegraph Enterprise users can get more personalized and better-ranked search results in the search bar for their codebases. With this feature, you get:

- Improved ranking for keyword searches like "data router". This capability is enabled by default and cannot be configured.
- Personalized ranking, specifically boosted results from repos you recently contributed to.

These boosted results from your recently contributed repositories make finding the code you care about easier.

## Compare changes across revisions

When you run a search, you can compare the results from two different revisions of the codebase. From your search query results page, click the three-dot icon next to the Contributors tab. Then select the Compare option.

From here, you can execute file and directory filtering and compare large diffs, making it easier to navigate and manage.

## Other search tips

- When viewing a file or directory, press the `y` key to expand the URL to its canonical form (with the full 40-character Git commit SHA).
- To share a link to multi-line range in a file, click on the starting line number and shift-click on the ending line number (in the left-hand gutter).
