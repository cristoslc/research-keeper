---
source-id: "mkdocs-material-getting-started"
title: "Material for MkDocs - Getting Started / Installation"
type: web
url: "https://squidfunk.github.io/mkdocs-material/getting-started/"
fetched: 2026-03-30T18:04:37Z
hash: "3b3ba15a3e97e0b8f24028b3f65e24dab85eb93422e9c759d635cb73af7b4e24"
---

# Getting started

Material for MkDocs is a powerful documentation framework on top of MkDocs, a static site generator for project documentation. If you're familiar with Python, you can install Material for MkDocs with `pip`, the Python package manager. If not, we recommend using `docker`.

## Installation

### with pip (recommended)

Material for MkDocs is published as a Python package and can be installed with `pip`, ideally by using a virtual environment. Open up a terminal and install Material for MkDocs with:

```
pip install mkdocs-material
```

This will automatically install compatible versions of all dependencies: MkDocs, Markdown, Pygments and Python Markdown Extensions. Material for MkDocs always strives to support the latest versions, so there's no need to install those packages separately.

### with docker

The official Docker image is a great way to get up and running in a few minutes, as it comes with all dependencies pre-installed. Open up a terminal and pull the image with:

```
docker pull squidfunk/mkdocs-material
```

The `mkdocs` executable is provided as an entry point and `serve` is the default command.

The following plugins are bundled with the Docker image:

- mkdocs-minify-plugin
- mkdocs-redirects

Warning: The Docker container is intended for local previewing purposes only and is not suitable for deployment.

### with git

Material for MkDocs can be directly used from GitHub by cloning the repository into a subfolder of your project root which might be useful if you want to use the very latest version:

```
git clone https://github.com/squidfunk/mkdocs-material.git
```

Next, install the theme and its dependencies with:

```
pip install -e mkdocs-material
```

In 2016, Material for MkDocs started out as a simple theme for MkDocs, but over the course of several years, it's now much more than that -- with the many built-in plugins, settings, and countless customization abilities, Material for MkDocs is now one of the simplest and most powerful frameworks for creating documentation for your project.

Key features of Material for MkDocs include:

- Write documentation in Markdown and create a professional static site in minutes
- Searchable, customizable, in 60+ languages, for all devices
- Color syntax highlighting for code blocks
- Theme files allow customizing the formatting
- Support for YAML frontmatter metadata on pages
- Git repository integration (show edit links, last updated dates, contributors)
- Blog, tags, versioning, social cards built-in
- Code annotations, content tabs, diagrams, math support
- Admonitions (callouts), grids, tooltips
