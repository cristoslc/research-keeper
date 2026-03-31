---
source-id: "why-i-chose-zola"
title: "Why I chose Zola to build this site - The Data Quarry"
type: web
url: "https://thedataquarry.com/blog/static-site-zola/"
fetched: 2026-03-30T18:04:37Z
hash: "8f7a3b64803b5a75234123e2e573ba293e380b43e481fd8ff7ba495103b5a5a7"
---

# Why I chose Zola to build this site

Nov 29, 2023 -- 13 min read

> "My thoughts on blogging, static sites and how to deploy a Zola site via GitHub Pages"

## My trysts with blogging

I've been writing blogs on and off for a few years now. Like most people, I began my journey via a platform that had a low barrier to entry, namely, Medium, because I could just get to writing straight away, and I didn't have to worry about hosting, security, or any of the other things that come with running a website. I just wanted to write good technical content, and Medium was a good place to do that a few years ago.

### Why I self-host

Below, I list some of my fundamental ideas about blogging and open knowledge-sharing.

- Knowledge that I gained from the public domain should, ideally, be shared back within the public domain -- I believe this is what advances human knowledge and understanding.
- Reading and writing content should, to a certain degree, be a personal experience and not a cookie-cutter one.
- Content should appear in a format that's easy to read, and not be cluttered with ads, pop-ups, and other distractions.
- To stand out in a sea of otherwise similar-looking content, you need the ability to customize aspects of your blog, such as the layout, the fonts, the colours, and so on.

## Static vs. Dynamic sites

Static sites are faster to load and, in my view, provide a much smoother reading experience than dynamic websites. For blogs, where the primary medium of interest is text, using a static site seems like a no-brainer. However, it does require some understanding of the modern web, including HTML, CSS and JavaScript.

## Static Site Generators (SSGs)

Of course, nobody in their right mind would want to put in days of work to structure their website. This is where Static Site Generators come in.

> *If you've ever taken a good look at HTML, it should be clear that it isn't fun to write it all by hand. Therefore, we invented the Static Site Generator (SSG): a program that takes an HTML template and some text in a more human-friendly form (usually Markdown), and mashes them together, yielding a servable HTML file.*

There are a ton of SSGs out there, including Jekyll, Hugo and Pelican. The main benefit of using an SSG is that it allows you to write content in a human-friendly format, such as Markdown, and then generates the HTML files prior to deployment. All it then takes is a bit of tweaking the CSS and adding some minimal JavaScript to get the static site up and running.

## What is Zola?

Zola is:

> *A fast static site generator in a single binary with everything built-in. This tool and its template engine were born from an intense dislike of the (insane) Golang template engine and therefore of Hugo that I was using before for 6+ sites.*

## Moving on from Hugo

Hugo, the world's most popular SSG written in Golang, was my first choice until recently. However, once I discovered Zola, an equivalent SSG written in Rust, I was immediately hooked. Just like the creator of Zola mentioned, the main issue for me with Hugo is its underlying Go template engine, which made it immensely difficult to customize the look and feel of a theme I liked. I found myself spending hours, or even days, trying to figure out how to get my site to look the way I wanted it to, rather than actually writing content.

Although Hugo is hugely popular and there's tons of examples online, it was still proving too hard for me to learn how to effectively use its templates and short codes. Zola addressed all these concerns, and more. Within a few days of looking up the documentation on Zola's template engine, Tera, I was productive enough to get my site's customizations up and running.

## The anatomy of a Zola site

A Zola site is just a collection of files and folders, with a specific structure.

```
.
├── config.toml
├── content
│   ├── about
│   │   └── _index.md
│   ├── posts
│   │   ├── post-1.md
│   │   ├── post-2.md
│   │   └── _index.md
│   └── projects
│   │   └── _index.md
│   └── _index.md
├── sass
│   └── main.scss
├── static
│   ├── font
│   │   └── custom_font.woff2
│   ├── img
│   │   └── icon.png
│   └── js
│       └── main.js
└── templates
    ├── base.html
    ├── index.html
    ├── page.html
    ├── post.html
    └── section.html
```

- `config.toml` is the main configuration file for your site. It contains information such as the site's title, description, the theme to use, and so on.
- `_index.md` at each directory is a special file that tells Zola to generate a page structure based on the declared front matter.
- `content` is the folder where you'll write your content. Each file in this folder is a page on your site. Zola allows the concept of section and page to keep things clean and organized.
- `sass` is the folder where you'll keep your CSS stylesheets. Zola uses the Sass CSS preprocessor.
- `static` is the folder where you'll keep all your static assets, such as images, fonts, and JavaScript files.
- `templates` is the folder where you'll keep your HTML templates, which can be customized via shortcodes. Zola uses the Tera template engine, which allows you to generate HTML pages via a template language very much like Python's Jinja2.

## Steps to setting up a Zola site

### Install Zola

Zola is a single binary, which means you can just download the binary for your platform. On Mac: `brew install zola`. Navigate to an empty directory and type in `zola init` to initiate a base Zola site.

### Define your requirements

For me, these were the main requirements:
- LaTeX math equations
- Code syntax highlighting
- Customizable themes and layouts
- Table of contents
- Footnotes and references
- Callout boxes (info, warning, etc.)
- Comments
- Privacy-focused site analytics

### Pick a base theme

Zola has an excellent list of starter themes that you can choose from. Always pick a theme that gets you most of the way towards your requirements -- the styles, layouts and templates can then be customized later.

### Customize the theme

Decide on what features matter to you the most, and begin tinkering with the stylesheets, templates and configuration files to get the theme to look the way you want it to. This is a time-consuming step up front, but with Zola, I found this to be much more intuitive and fun than I did with Hugo.

### Write content and test locally

Navigate to the content directory and begin writing a post in Markdown. You can use the `zola serve` command to start a local server that will serve your site on localhost:1111.

### Deploy

To get the site up and running on the web, you'll need to deploy it somewhere. GitHub Pages is free and easy to set up right within the source repo. Netlify and Vercel are also options with free tiers.

## Conclusions

In this post, I covered some of the basics of static sites, SSGs, and how to deploy a Zola site via GitHub Pages. Putting down your thoughts and learnings in writing is a great way to push your boundaries, contribute to the open sharing of knowledge, and to make a mark on the world, no matter how small.
