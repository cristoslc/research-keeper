---
source-id: "facet-web-howto"
title: "How to Make a Faceted Classification and Put It On the Web"
type: web
url: "https://www.miskatonic.org/library/facet-web-howto.html"
fetched: 2026-03-30T18:04:37Z
hash: "127fa6f5648bd97e0184fdfadef60b65d63cca73cd346b7b3de6533f4ddd4ee4"
---

# How to Make a Faceted Classification and Put It On the Web

by William Denton, November 2003 (last modified March 2009)

## 0. Introduction

Faceted classifications are increasingly common on the World Wide Web, especially on commercial web sites (Adkisson 2003). This is not surprising -- facets are a natural way of organizing things. Many web designers have probably rediscovered them independently by asking, "What other ways would people want to view this data? What's another way to slice it?" A survey of the literature shows that faceted classification has its roots in the library science work of Ranganathan and others, and that in the last few years several researchers and practitioners have investigated the use of facets for organizing information on the web. This paper gives a short introduction to the theory and practice of faceted classification, and then shows how to make one and present it on the web.

## 1. What is faceted classification?

In faceted classification, each item in the collection is tagged with terms from multiple facets. Each facet is a taxonomy of terms about one aspect of the item. Users can search or browse the collection by selecting terms from any combination of facets, in any order.

A useful example from Ranganathan: a library book about the cultivation of rice by Japanese farmers in the Meiji era would be classified in most systems under one subject heading -- maybe agriculture. The book would be alongside all other agriculture books. Faceted classification assigns multiple codes: one for the crop (rice), one for the action (cultivation), one for the people doing it (farmers), one for the place (Japan), and one for the time (Meiji era). Users looking for books about rice from any perspective will find this book, as will users looking for books about Japanese agriculture, or about farming in the Meiji era.

## 2. Origins and theory

The pioneer in faceted classification is Shiyali Ramamrita Ranganathan (1892-1972). Ranganathan devised what he called the Colon Classification (because a colon was used to separate the facet codes) while working as a librarian and academic in India.

S.R. Ranganathan's Colon Classification has five facets, now classic (known as PMEST):
- **Personality** (the something in question, e.g. a person or event in a classification of history, or an animal in a classification of zoology)
- **Matter** (the material, substance, or property)
- **Energy** (the action, method, or process)
- **Space** (the geographic location)
- **Time** (the time period or era)

These five, known as PMEST, may be enough for you. If you need more, look to the second edition of the Bliss Bibliographic Classification (BC2) for ideas. Vanda Broughton, one of the editors of BC2, said, "These fundamental thirteen categories have been found to be sufficient for the analysis of vocabulary in almost all areas on knowledge."

## 3. Facets on the web

The key point about facets on the web is this: when, for the purposes of the classification, it is possible to organize the entities by three or more mutually exclusive and jointly exhaustive categories, then facets are probably the appropriate classification. Facets can be used to organize the entire world of knowledge, or the clothes in your cupboard, or anything in between. Ranganathan's Colon Classification and the Bliss Bibliographic Classification are universal classifications.

## 4. How to make a faceted classification

Louise Spiteri (1998) analyzed the complicated sets of rules that Ranganathan and the Classification Research Group laid down for how to make faceted classification systems, and drew up her own simpler set. Her steps:

1. **Collect and group sample entities.** Collect a representative sample of entities (items, documents, web pages, etc.) that will be classified. Informally group related entities together.
2. **Create facets.** Examine the groups. Identify the fundamental categories or facets in the domain. Each facet should represent one clearly defined, mutually exclusive characteristic of division.
3. **Create an array within each facet.** Within each facet, list all the possible values (called foci by Ranganathan, values or terms more commonly). These values should be mutually exclusive within a facet.
4. **Order the array within each facet.** Arrange the terms in each facet in a logical order. This could be alphabetical, chronological, hierarchical, or some other useful ordering.
5. **Order the facets.** Choose an ordering for the facets themselves (which is the primary way of browsing/searching, which secondary, etc.).
6. **Establish a notation.** Optionally create short codes for each term to enable compact representation of multi-facet classifications.

## 5. A worked example: dishwashing detergents

Facets identified: Brand, Form, Scent, Size, Special features.

The example demonstrates how a small product domain can be organized into facets that allow browsing from any angle -- by brand, by form (liquid/powder/gel), by scent, by size, or by features (antibacterial, concentrated, etc.). Each product is tagged with one term from each facet, and users can combine any facet values to narrow down the set.

## 6. Putting it on the web

Several approaches exist:
- **Static HTML** pages linked with a matrix of facet combinations (limited scalability)
- **Database-backed dynamic pages** where facet selections generate SQL queries
- **XFML (eXchangeable Faceted Metadata Language)** -- an XML format designed specifically for exchanging faceted metadata between websites (developed by Peter Van Dijck)

The key UI principle: allow users to select facets in any order, show result counts for each facet value, and dynamically update available facet values as selections are made (to avoid empty result sets).

## References

- Adkisson, Heather. 2003. "Use of faceted classification." Web design practices. http://www.webdesignpractices.com/navigation/facets.html
- Broughton, Vanda. 2001. "Faceted classification as a basis for knowledge organization in a digital environment." New Review of Hypermedia and Multimedia 7: 67-102.
- Ranganathan, S.R. 1962. Elements of library classification. Bombay: Asia Publishing House.
- Spiteri, Louise. 1998. "A simplified model for facet analysis: Ranganathan 101." Canadian Journal of Information and Library Science 23 (1/2) (April-July): 1-30.
- Van Dijck, Peter. 2003. "Introduction to XFML." xml.com. http://www.xml.com/pub/a/2003/01/22/xfml.html
