---
source-id: "obsidian-git-plugin-github"
title: "Obsidian Git Plugin — Integrate Git version control with automatic commit-and-sync in Obsidian.md"
type: web
url: "https://github.com/Vinzent03/obsidian-git"
fetched: 2026-03-30T18:04:37Z
hash: "e0c2529ccb5972955c316d81bf63bf2c897dfcc7281ba67fce9490cfe2aa4b4f"
---

# Obsidian Git Plugin

A powerful community plugin for Obsidian.md that brings Git integration right into your vault. Automatically commit, pull, push, and see your changes — all within Obsidian.

## Documentation

All setup instructions (including mobile), common issues, tips, and advanced configuration can be found in the full documentation at https://publish.obsidian.md/git-doc.

Mobile users: The plugin is highly unstable. Please check the dedicated Mobile section below.

## Key Features

- Automatic commit-and-sync (commit, pull, and push) on a schedule.
- Auto-pull on Obsidian startup
- Submodule support for managing multiple repositories (desktop only and opt-in)
- Source Control View to stage/unstage, commit and diff files - Open it with the "Open source control view" command.
- History View for browsing commit logs and changed files - Open it with the "Open history view" command.
- Diff View for viewing changes in a file - Open it with the "Open diff view" command.
- Signs in the editor to indicate added, modified, and deleted lines/hunks (desktop only).
- GitHub integration to open files and history in your browser

For detailed file history, consider pairing this plugin with the Version History Diff plugin.

## Source Control View

Manage your file changes directly inside Obsidian like stage/unstage individual files and commit them.

## History View

Show the commit history of your repository. The commit message, author, date, and changed files can be shown. Author and date are disabled by default but can be enabled in the settings.

## Diff View

Compare versions with a clear and concise diff viewer. Open it from the source control view or via the "Open diff view" command.

## Signs in the Editor

View line-by-line changes directly in the editor with added, modified, and deleted line/hunk indicators. You can stage and reset changes right from the signs. There are also commands to navigate between hunks and stage/reset hunks under the cursor. Needs to be enabled in the plugin settings.

## Available Commands

### Changes
- List changed files: Lists all changes in a modal
- Open diff view: Open diff view for the current file
- Stage current file
- Unstage current file
- Discard all changes: Discard all changes in the repository

### Commit
- Commit: If files are staged only commits those, otherwise commits only files that have been staged
- Commit with specific message: Same as above, but with a custom message
- Commit all changes: Commits all changes without pushing
- Commit all changes with specific message: Same as above, but with a custom message

### Commit-and-sync
- Commit-and-sync: With default settings, this will commit all changes, pull, and push
- Commit-and-sync with specific message: Same as above, but with a custom message
- Commit-and-sync and close: Same as Commit-and-sync, but if running on desktop, will close the Obsidian window. Will not exit Obsidian app on mobile.

### Remote
- Push, Pull
- Edit remotes: Add new remotes or edit existing remotes
- Remove remote
- Clone an existing remote repo: Opens dialog that will prompt for URL and authentication to clone a remote repo
- Open file on GitHub: Open the file view of the current file on GitHub in a browser window. Note: only works on desktop
- Open file history on GitHub: Open the file history of the current file on GitHub in a browser window. Note: only works on desktop

### Manage local repository
- Initialize a new repo
- Create new branch
- Delete branch
- CAUTION: Delete repository

### Miscellaneous
- Open source control view: Opens side pane displaying Source control view
- Open history view: Opens side pane displaying History view
- Edit .gitignore
- Add file to .gitignore: Add current file to .gitignore

## Desktop Notes

### Authentication
Some Git services may require further setup for HTTPS/SSH authentication. Refer to the Authentication Guide.

### Obsidian on Linux
- Snap is not supported due to its sandboxing restrictions.
- Flatpak is not recommended, because it doesn't have access to all system files.
- Please use AppImage or a full access installation of your system's package manager instead.

## Mobile Support (Experimental)

The Git implementation on mobile is very unstable! I would not recommend using this plugin on mobile, but try other syncing services.

One such alternative is GitSync, which is available on both Android and iOS. It is not associated with this plugin, but it may be a better option for mobile users.

The Git plugin works on mobile thanks to isomorphic-git, a JavaScript-based re-implementation of Git - but it comes with serious limitations and issues. It is not possible for an Obsidian plugin to use a native Git installation on Android or iOS.

### Mobile Feature Limitations
- No SSH authentication
- Limited repo size, because of memory restrictions
- No rebase merge strategy
- No submodules support

### Performance Caveats
Depending on your device and available free RAM, Obsidian may crash on clone/pull, create buffer overflow errors, or run indefinitely. It's caused by the underlying git implementation on mobile, which is not efficient.

### Tips for Mobile Use
If you have a large repo/vault, I recommend staging individual files and only committing staged files.

## Project Stats
- 10.2k stars on GitHub
- 467 forks
- 951 commits
- Latest release: 2.38.0 (March 4, 2026)
- Written in TypeScript (84.6%), Svelte (11.6%), CSS (3.2%), JavaScript (0.6%)
- MIT License
