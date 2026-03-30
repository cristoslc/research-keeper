---
source-id: "docusaurus-introduction"
title: "Docusaurus - Introduction (Official Documentation)"
type: web
url: "https://docusaurus.io/docs"
fetched: 2026-03-30T18:04:37Z
hash: "ffc498c55399b6f9ac80b713df211bb0edf6278f0078db3860eb0412fe488283"
---

# Introduction

Docusaurus will help you ship a beautiful documentation site in no time.

Building a custom tech stack is expensive. Instead, focus on your content and just write Markdown files.

Ready for more? Use advanced features like versioning, i18n, search and theme customizations.

Docusaurus is a static-site generator. It builds a single-page application with fast client-side navigation, leveraging the full power of React to make your site interactive. It provides out-of-the-box documentation features but can be used to create any kind of site (personal website, product, blog, marketing landing pages, etc).

## Fast Track

Install Node.js and create a new Docusaurus site:

```
npx create-docusaurus@latest my-website classic
```

Start the site:

```
cd my-website
npx docusaurus start
```

Open http://localhost:3000 and follow the tutorial.

## Features

Docusaurus is built with high attention to the developer and contributor experience.

- Built with React: Extend and customize with React. Gain full control of your site's browsing experience by providing your own React components.
- Pluggable: Bootstrap your site with a basic template, then use advanced features and plugins. Open source your plugins to share with the community.
- Developer experience: Start writing your docs right now. Universal configuration entry point. Hot reloading with lightning-fast incremental build on changes. Route-based code and data splitting. Publish to GitHub Pages, Netlify, Vercel, and other deployment services with ease.
- SEO friendly: HTML files are statically generated for every possible path. Page-specific SEO to help your users land on your official docs.
- Powered by MDX: Write interactive components via JSX and React embedded in Markdown. Share your code in live editors.
- Search: Your full site is searchable.
- Document Versioning: Helps you keep documentation in sync with project releases.
- Internationalization (i18n): Translate your site in multiple locales.
- Lightning-fast: Follows the PRPL Pattern for blazing fast content loading.
- Accessible: Attention to accessibility, making your site equally accessible to all users.

## Design principles

- Little to learn. Docusaurus should be easy to learn and use as the API is quite small.
- Intuitive. Users will not feel overwhelmed when looking at the project directory.
- Layered architecture. The separations of concerns between each layer (content/theming/styling) should be clear.
- Sensible defaults. Common performance optimizations and configurations will be done for users.
- No vendor lock-in. Users are not required to use the default plugins or CSS.

## Comparison with other tools

### MkDocs

MkDocs is a popular Python static site generator with value propositions similar to Docusaurus. It is a good option if you don't need a single-page application and don't plan to leverage React. Material for MkDocs is a beautiful theme.

### Docsify

Docsify makes it easy to create a documentation website, but is not a static-site generator and is not SEO friendly.

### GitBook

GitBook has a very clean design and has been used by many open source projects. With its focus shifting towards a commercial product rather than an open-source tool, many of its requirements no longer fit the needs of open source projects' documentation sites. As a result, many have turned to other products. You may read about Redux's switch to Docusaurus. Currently, GitBook is only free for open-source and non-profit teams. Docusaurus is free for everyone.

### Jekyll

Jekyll is one of the most mature static site generators around and has been a great tool to use -- in fact, before Docusaurus, most of Facebook's Open Source websites are/were built on Jekyll!

### VitePress

VitePress has many similarities with Docusaurus -- both focus heavily on content-centric websites and provides tailored documentation features out of the box. However, VitePress is powered by Vue, while Docusaurus is powered by React.

### Rspress

Rspress is a fast static site generator based on Rspack, a Rust-based bundler. It supports content writing with MDX, integrated text search, multilingual support (i18n), and extensibility through plugins.
