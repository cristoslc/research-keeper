---
source-id: "gitlab-wiki-docs"
title: "Wiki | GitLab Docs"
type: web
url: "https://docs.gitlab.com/user/project/wiki/"
fetched: 2026-03-30T18:04:37Z
hash: "b5010dde2bff5d19cde662d9c6c9ed509a1ce692f9d3a3af9049d234c449fb64"
---

# Wiki

- Tier: Free, Premium, Ultimate
- Offering: GitLab.com, GitLab Self-Managed, GitLab Dedicated

Wiki provides project and group documentation in a familiar format. Wiki pages:

- Generate technical documentation, guides, and knowledge bases in Markdown, RDoc, AsciiDoc, or Org formats.
- Create collaborative documents that integrate directly with GitLab projects and groups.
- Store documentation in Git repositories for version control and collaboration.
- Support custom navigation and organization through sidebar customization.
- Export content as PDF files for offline access and sharing.
- Maintain your content separately from your codebase while keeping them in the same project.

Each wiki is a separate Git repository. You can create and edit wiki pages through the GitLab web interface or locally using Git. Wiki pages written in Markdown support all Markdown features and provide wiki-specific behavior for links.

Wiki pages display a sidebar, which you can customize.

## View a project wiki

To access a project wiki:

1. In the top bar, select Search or go to and find your project.
2. To display the wiki, either:
   - In the left sidebar, select Plan > Wiki.
   - On any page in the project, use the `g`+`w` wiki keyboard shortcut.

## Configure a default branch for your wiki

Your wiki repository inherits the default branch name from your instance or group. If no custom branch name is configured, GitLab uses `main`. To rename your wiki's default branch, update the default branch name in your repository.

## Create the wiki home page

When a wiki is created, it is empty. On your first visit, you can create the home page users see when viewing the wiki. This page requires a specific path to be used as your wiki's home page.

## Create a new wiki page

Prerequisites: The Developer, Maintainer, or Owner role.

To create a new wiki page from a project or group:

1. On the top bar, select Search or go to and find your group or project.
2. In the upper-right corner, select Create new, then New wiki page.

### Create or edit wiki pages locally

Wikis are based on Git repositories, so you can clone them locally and edit them like you would do with every other Git repository. To clone a wiki repository locally:

1. Select Plan > Wiki.
2. Select Wiki actions, then Clone repository.
3. Follow the on-screen instructions.

Files you add to your wiki locally must use one of the following supported extensions, depending on the markup language you wish to use:

- Markdown extensions: `.mdown`, `.mkd`, `.mkdn`, `.md`, `.markdown`.
- AsciiDoc extensions: `.adoc`, `.ad`, `.asciidoc`.
- Other markup extensions: `.textile`, `.rdoc`, `.org`, `.creole`, `.wiki`, `.mediawiki`, `.rst`.

### Special characters in page paths

Wiki pages are stored as files in a Git repository, and by default, the filename of a page is also its title. Certain characters in the filename have a special meaning:

- Spaces are converted into hyphens when storing a page.
- Hyphens (`-`) are converted back into spaces when displaying a page.
- Slashes (`/`) are used as path separators, and can't be displayed in titles.

To circumvent these limitations, you can also store the title of a wiki page in a front matter block before a page's contents:

```
---
title: Page title
---
```

## Edit a wiki page

Prerequisites: You must have the Developer, Maintainer, or Owner role.

1. Select Plan > Wiki.
2. Go to the page you want to edit, and either use the `e` wiki keyboard shortcut or select Edit.
3. Edit the content.
4. Select Save changes.

Unsaved changes to a wiki page are preserved in local browser storage to prevent accidental data loss.

## Wiki page templates

You can create templates to use when creating new pages, or to apply to existing pages. Templates are wiki pages that are stored in the `templates/` directory in the wiki repository.

## View history of a wiki page

The changes of a wiki page over time are recorded in the wiki's Git repository. The history page shows:

- The revision of the page.
- The page author.
- The commit message.
- The last update.
- Previous revisions, by selecting a revision number in the Page version column.

### View changes between page versions

You can see the changes made in a version of a wiki page, similar to versioned diff file views.

### Restore a wiki page to a previous version

You can restore a wiki page to any previous version from its history. This creates a new version with the restored content while preserving the full version history.

## Sidebar

Wiki pages display a sidebar that contains a list of pages in the wiki, displayed as a nested tree, with sibling pages listed in alphabetical order.

You can find a page by its title in the wiki using the search box in the sidebar. You can toggle the sidebar open or closed using the sidebar toggle located in the upper-left corner of the page.

For performance reasons, the sidebar is limited to displaying 5000 entries.

### Customize sidebar

You can manually edit the contents of the sidebar navigation. This process creates a wiki page named `_sidebar` which fully replaces the default sidebar navigation.

A `_sidebar` example, formatted with Markdown:

```
### Home

- [Hello World](hello)
- [Foo](foo)
- [Bar](bar)

---

- [Sidebar](_sidebar)
```

## Rich text editor

GitLab provides a rich text editing experience for GitLab Flavored Markdown in wikis.

Support includes:

- Formatting text, including using bold, italics, block quotes, headings, and inline code.
- Formatting ordered lists, unordered lists, and checklists.
- Creating and editing table structure.
- Inserting and formatting code blocks with syntax highlighting.
- Previewing Mermaid, PlantUML, and Kroki diagrams.

## Track wiki events

GitLab tracks wiki creation, deletion, and update events. These events are displayed on user profile and activity pages.

Commits to wikis are not counted in repository analytics.

## Related topics

- Wiki settings for administrators
- Project wikis API
- Group wikis API
- Wiki keyboard shortcuts
- GitLab Flavored Markdown
- AsciiDoc
