---
source-id: "upsetjs-ecosystem"
title: "UpSet.js -- The UpSet.js Ecosystem (an interactive JavaScript re-implementation of UpSet(R))"
type: web
url: "https://medium.com/@sgratzl/upset-js-the-upset-js-ecosystem-ab6692d2f34a"
fetched: 2026-03-30T18:04:37Z
hash: "ccea166966d9fef910bf9e0d8021159d229eade93c72033eca1a9245785aa1cd"
---

# UpSet.js -- The UpSet.js Ecosystem

## an interactive JavaScript re-implementation of UpSet(R)

by Samuel Gratzl -- May 3, 2020

## Background and Motivation

Venn diagrams are a common way to show set intersections between sets. However, with more than three sets things get messy. In 2014, Lex et. al. published an InfoVis paper about *UpSet* -- a visualization technique for showing set intersections with more than three sets. UpSet addresses the inherent issues of Venn diagrams for more than three sets by using a completely different approach to visualize the sets and set intersections.

An UpSet plot consists of three areas:

- The bottom left area shows the list of sets as a vertical bar chart. The length of the bar corresponds to the cardinality of the set, i.e., the number of elements in this set.
- The top right area shows the list of set intersections as a horizontal bar chart. Again the length corresponds to the cardinality of the set.
- The bottom right area shows which intersection consists of which sets. A dark dot indicates that the set is part of this set intersection. The line connecting the dots is to visually group the dots.

UpSet was well received and later got some momentum when UpSetR was published. UpSetR is an R package for creating static UpSet plots. In contrast to the original publication, the authors of UpSetR flipped the UpSet plot such that set intersections are shown horizontally instead of vertically.

UpSetR is a generic R package for generating UpSet plots with three different input formats. UpSetR got popular due to its simplicity to use and the expressiveness of UpSet plots for comparing set intersections. However, the plots are static thus removing a powerful aspect of interactive visual exploration. Moreover, the library is limited to R only.

I believe that UpSet plots are sophisticated and well designed visualization technique for exploring set intersections with more than three sets. However, the existing prototypes and libraries dampen its potential by either limiting its broad usage or interactivity. Thus, the idea for *UpSet.js* was born.

**Design goals:**
- easy to use JavaScript library with few dependencies
- full interactivity within the UpSet plot including highlights, tooltips, and linked selections
- fast amount of customization option especially regarding coloring
- a pure functional library without any internal state or side effects
- integrated export options to formats such as PNG, SVG, or Vega Lite
- integrations in data science tools such as R, Jupyter Python Notebooks, PowerBI, or Tableau

## Features

### Interaction

When hovering over a bar in UpSet.js all related elements are highlighted in orange. For example, when hovering over a set intersection, UpSet.js will highlight the common elements in all other sets in orange.

UpSet.js is a stateless component which means that all interactions are directly reported back to the calling component. The caller has then to decide how to react on the event. This stateless nature and shifting the interaction logic from the library to the caller allows numerous different user interactions without changing the library itself.

For example, another possible variant: when the user clicks on a set, it is selected and persisted. When hovering over another set while holding the Control modifier key, the interaction mode changes -- not the hovered set is highlighted but the set intersection that is built by combining the persisted selection and the hovered set. This allows to quickly identify intersection locations among all set intersections.

### Queries

UpSet.js supports user defined queries. The first and primary query is visualized similar to a selection, whereas all other secondary queries are just indicated using small marks with an additional line going through the bar. This simplifies the comparison task and makes queries more salient.

### Numerical Attributes

Each numerical attribute is summarized using a box plot. One can easily detect interesting patterns by looking at the distribution in a set or set intersection. Since interactivity was a major design criteria, also the box plots highlight the selected subset by overlaying a box plot just of the common elements.

## Integrations and Applications

### UpSet.js App
A single page application that allows users to import, explore, and export UpSet.js data. Client only -- all uploaded data are stored in the browser with no server involved. Supports exporting to CodePen, CodeSandbox, static images (SVG, PNG), Vega Lite specification, CSV file, and JSON dump format. An embedded link can be generated that has all the data encoded in the URL in a compressed format.

### R/RShiny/RMarkDown
R wrapper using HTMLWidgets. Supports similar data input formats as UpSetR. Can be used in standalone plots, RMarkDown files, or R Shiny environments with custom events for linking charts.

### Jupyter Notebooks
Jupyter lab and notebook extension for showing interactive UpSet.js plots. Works with Jupyter widget interact command for interactive linked updates.

### PowerBI
PowerBI custom visual extension with proper data and synchronized selection support.

### Tableau
Tableau Dashboard extension. Fully interactive with synchronized selections.

## Implementation

UpSet.js is written in TypeScript using React and hosted on Github at https://github.com/upsetjs. The core library is written in React but provides also bundle editions for plain JavaScript use.

Also supports Euler Diagrams, Venn Diagrams, and Karnaugh Maps as alternative set visualization approaches.

**References:**
1. Lex et al., *UpSet: Visualization of Intersecting Sets*, IEEE TVCG (InfoVis '14), 2014.
2. Conway et al., *UpSetR: An R Package for the Visualization of Intersecting Sets and their Properties*, Bioinformatics, 2017.
3. Gadhave et al., *UpSet 2: From Prototype to Tool*, IEEE InfoVis '19 Posters, 2019.
