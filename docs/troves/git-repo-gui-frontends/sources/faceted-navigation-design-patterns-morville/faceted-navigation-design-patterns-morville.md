---
source-id: "faceted-navigation-design-patterns-morville"
title: "Design Patterns: Faceted Navigation' by Peter Morville & Jeffery Callender (A List Apart)"
type: web
url: "https://alistapart.com/article/design-patterns-faceted-navigation/"
fetched: 2026-03-30T18:04:37Z
hash: "8ae74c97028d0102512baab3dfecb4cbda2420b297c2db7c03c319f937ae6bc0"
---

# Design Patterns: Faceted Navigation

By Peter Morville and Jeffery Callender. April 20, 2010. Excerpt from Chapter 4 of Search Patterns (O'Reilly, 2010).

## Faceted Navigation

Also called *guided navigation* and *faceted search*, the faceted navigation model leverages metadata fields and values to provide users with visible options for clarifying and refining queries. Faceted navigation is arguably the most significant search innovation of the past decade. It features an integrated, incremental search and browse experience that lets users begin with a classic keyword search and then scan a list of results. It also serves up a custom map (usually to the left of results) that provides insights into the content and its organization and offers a variety of useful next steps. That's where faceted navigation proves its power. In keeping with the principles of progressive disclosure and incremental construction, users can formulate the equivalent of a sophisticated Boolean query by taking a series of small, simple steps. Faceted navigation addresses the universal need to narrow. Consequently, this pattern has become nearly ubiquitous in e-commerce, given the availability of structured metadata and the clear business value of improving product findability. Faceted navigation is being deployed rapidly across an impressively wide variety of contexts and platforms. In the world of search, faceted navigation is everywhere.

A successful implementation of faceted navigation as a model for interacting with the catalogs of several academic libraries demonstrates how source (roughly equivalent to location) can be deemphasized relative to subject and format. The consortium's goal is to connect students and faculty with the best materials, regardless of which university owns them. This example also hints at the design challenges. Faceted navigation is not simply a feature to check off a list. Success requires painstaking attention to detail and an appreciation for the vast array of possibilities for interaction design. For instance, the libraries run collapsible facets down the left. Only the most relevant facets (subject, format, location) are open. Most are closed by default. Each open facet reveals only the top four or five most heavily populated values. This allows for a small facet footprint that frees up plenty of space on the main stage for the results themselves. The number of matching results for each value (shown within parentheses) is a key element of the map, as is the reformulation of search terms and selected values as stacking breadcrumbs, which let users view and modify their current search parameters.

Applications rely on a mix of *scented widgets* for viewing and interacting with facet values, and some shift facet selectors to the top or right rather than the left. Presenting facets along the top draws added attention to the narrowing facility. Given massive result sets, this is an effective way to highlight the data structure and draw users into filtering. Top placement may sometimes obscure results and cause clutter, but can work well with image collections or when only a few facets are needed. It's often useful to allow for flexibility in the number of facets displayed. Adaptive facets let controls conform to the content as users shift between categories and drill down within collections.

Formal definitions of facets may exclude simple fields and filters, but discrimination is unwarranted in practice, provided that filters operate independently and users can add or remove them in arbitrary order in concert with the updating of results.

The distinction between faceted navigation and parametric search is relevant. In parametric search applications, users specify their search parameters up front using a variety of controls such as checkboxes, pull-downs, and sliders to construct what effectively is an advanced Boolean query. Unfortunately, it's hard for users to set several parameters at once, especially since many combinations will produce zero results.

At the other extreme, live search applications update results dynamically with no submit button and no page refresh. There are some real advantages to this dynamic model, which allows for immediate response, minimal disruption, and elegant transitions.

Faceted navigation is a master pattern. Its deployment impacts all other search patterns and the information architecture as a whole. To oversimplify, there's the Google model and the faceted navigation model. Choosing between these two is a major strategic decision. The infrastructure for faceted navigation can enable a tighter relationship between search and browse. It can shape the structure and navigation of the entire site or application. It also changes how we think about autocomplete and best first. It offers a familiar framework for managing the sources of federated search. Plus, its discriminatory power to clarify intent and refine results may offset the need for personalization and advanced search.

Marti Hearst and her Flamenco project collaborators at UC Berkeley deserve credit for their pioneering research in faceted navigation.
