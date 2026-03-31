---
source-id: "obsidian-off-vault-editor"
title: "Obsidian as editor of off-vault markdown notes: obseditor in GitHub"
type: web
url: "https://forum.obsidian.md/t/obsidian-as-editor-of-off-vault-markdown-notes-obseditor-in-github/107583"
fetched: 2026-03-30T18:04:37Z
hash: "cb83fdeb52c0162c64c82e245faa00e56d63985486ba434e2f576cf58b107995"
---

# Obsidian as editor of off-vault markdown notes: obseditor in GitHub

Posted by msfz751 on the Obsidian Forum, November 3, 2025

Borrowing some ideas from an earlier script for making Obsidian act as a markdown editor for files outside a typical vault, I have made some minor modifications for use in Linux. I use CachyOS with GNOME, and Nemo as File Explorer.

The trick is creating symbolic links of the original .md file and its linked resources, such as images, PDF files, etc. What you have in Obsidian are all symbolic links. Once you finish your editing (text wrangling, formatting, tables, etc.), you could delete the files from the vault. The original files will persist since they are just inodes.

The main change I made on the original script is that instead of creating a Temp folder inside the vault for the outside notes, I recreate the original folder structure where the note was residing. I found that this folder structure is more informative of the note, or notes, I am dealing with, while providing context of location.

The script is ready for selection of multiple MD files; it will loop through every markdown note in the file explorer creating all the necessary symbolic links.

I know it is not a perfect solution but it works. It can serve other purposes as well, such as note importer, or modified, to be a CLI note editor.

The script works by:
1. If the file is inside any vault (in place or linked), just opening it directly
2. If the file is in one of the folders that should be mirrored, replicating the folder's internal directory chain in the vault and putting a link to the file in it
3. In other cases, replicating the note's FULL directory structure in the vault

It also handles linked files (images, PDFs) referenced in the markdown by creating symlinks for those as well, parsing both markdown image syntax `![image](path)` and HTML img tags.

## Follow-up (November 5, 2025)

The code and template were published on GitHub at https://github.com/Physics-of-Data/obsidian-editor

Now includes a Templater template that makes easier to synchronize changes between Obsidian and Typora (or whatever the markdown editor you use). The template addresses several issues that are common when working simultaneously with Obsidian and an external editor:

- Spaces in image links and resources (PDF documents). The template will convert the spaces to "%20" so the file and path can be understood in the external editor
- Conversion of symbolic links to files when editing is completing
- Create and modify objects simultaneously in Obsidian and an external editor
- Moving images and PDF files to the assets subfolder created by the external editor

**Notes:**
1. The author usually starts markdown notes with Typora with some bare content. Then uses this script to bring it to Obsidian, to edit it with Obsidian superpowers: plugins, custom JavaScript scripts, advanced tables, formatting, etc. For instance, Typora only supports live embedding for images, while Obsidian natively supports embedding and viewing PDF files.
2. To make the transition of images (links) to Obsidian, set your Typora preferences to use "relative paths"
