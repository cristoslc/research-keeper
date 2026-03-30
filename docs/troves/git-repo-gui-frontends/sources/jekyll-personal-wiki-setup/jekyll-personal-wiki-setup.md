---
source-id: "jekyll-personal-wiki-setup"
title: "How to Set Up a Personal Wiki (with Jekyll) - Strikingloo"
type: web
url: "https://strikingloo.github.io/personal-wiki-set-up"
fetched: 2026-03-30T18:04:37Z
hash: "0cb972d2ab28f50d3cf79d4cb817021d20753d8914336dd751ab807fe0ef637b"
---

# How to Set Up a Personal Wiki (with Jekyll)

This is a tutorial on how to make a digital garden / personal wiki using my Jekyll template.

I have been using a personal wiki for note-taking and studying for 2 years. In that time, it has helped me a lot when preparing exams or job interviews, and generally made studying from books or papers feel more productive and enjoyable.

A part of that is just emotional: it feels good to take notes and capture what you learn, knowing you will be able to find it again later. Being more deliberate about what you will remember in the long term, and what resources you have close to hand when writing an essay or programming, frees up a lot of cognitive load from day-to-day studying or processing, and lets you focus on the tasks themselves.

Reviewing a whole topic from a set of notes instead of having to reopen an old book (or books, plural) is also a liberating feature.

## Step 1: Forking the Github Project

I built a template for a personal site with a Digital Garden by stripping away all the content from this site and changing the design.

You can fork it in Github, which allows you to basically copy paste all of my code and then edit on top of it. You are free to edit away any part of it or just leave it all as-is and start using the wiki right away.

To fork, simply go to the project's URL and click on fork if you have a GitHub account, or create one first. This will create your own copy of the project from which you can begin working. Make sure to name it nickname.github.io where nickname is your GitHub username, so everything works correctly. This will make the repository your GitHub personal site.

Once you've cloned the project into your PC (`git clone <project URL>`), you can run the site locally. To do this, you will need to install Jekyll, open a terminal and run the commands:

```
sudo gem install rails
sudo gem install jekyll
sudo gem install jekyll bundler
cd ~/this_project

bundle init
bundle install
bundle add jekyll
bundle exec jekyll serve
```

All of the style and design is packed into a file called `css/main.css`, which you are free to edit and customize as you prefer, until it suits your aesthetic sensibilities.

## Step 2: Making the Site Your Own

There are a few parts of this template you will need to edit to add in your personal touch:

- `index.html` and `about/index.md`, which contain the Homepage and About page respectively.
- The file `_config.yml` has a few configuration fields: one for your twitter username and another for your google analytics ID.
- Go to `_layouts/default.html`. The footer has a few links to social media with their corresponding FontAwesome icons. You can either replace mine with yours, or delete the line to remove that link from your site.

## Step 3: Using the Wiki

Under the `wiki` folder, you will find a default, template article. You'll notice it is on markdown, an extension of plaintext that will let you format files nicely without having to learn how to code. You can do headings, subheadings, lists and links quite easily, and this example file has a little bit of each piece of syntax so you don't have to learn from scratch.

Whenever you want to add a new article to your wiki, all you have to do is create a new .md file in that folder, and give it a title and description like in the example file (between '---'s). You can also add tags, separated by commas, which allow for searching (in the wiki's searchbox, or using a link to /tagged/?q=keyword) and an abstract that will appear in the beginning of the article in a different colored box.

The importance and date fields serve mostly as metadata: the former ranks articles in the /wiki base page, the latter just lets you know when you created an article first.

When you come up with an idea that you like, or read something that surprises you or you think you will want to use or review later, add it to your wiki. Ideally use your own words, but there is no shame in copying and pasting (though future-you will probably be happier if you link or cite your source). Finally, link the article to other articles in your wiki that you think will be relevant or related, so in future traversals you will see how it fits in the bigger picture.

There is a whole philosophy to planting notes in a digital garden, along with the idea of maintaining them so they are 'evergreen' (as opposed to a blog post which is often a temporary thing that loses relevance over time).

Additionally, this personal site comes with support for a blog, in case you want to start writing one. Again each post will be a markdown file, with the only condition that their filenames should start with the date you wrote them in.

## Step 4: Optionally, Host it on Github Pages

If you want to make your wiki public, you can host it for free in many places like Github Pages or Netlify. I think Github has the friendliest workflow for this, but they are both free providers and you can customize the subdomain in either of them, so I don't have a big preference for one of them. You can also buy your own domain and host it there, if you want to and can afford it.

## Conclusions

I think many people can benefit from having their own place in the web, and their own system for note taking. Being able to take notes in public and link them, leveraging the web's capability for connecting thoughts, can make you a more effective writer and, indirectly, thinker.

More directly, it has helped me a lot with studying and it may do the same for you. So if you were on the fence on creating a Digital Garden or personal wiki and didn't know where to start, I hope this tutorial will have given you the push you needed.
