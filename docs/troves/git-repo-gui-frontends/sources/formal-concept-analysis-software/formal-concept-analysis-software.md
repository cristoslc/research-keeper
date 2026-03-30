---
source-id: "formal-concept-analysis-software"
title: "FCA Software - Formal Concept Analysis Homepage (Uta Priss)"
type: web
url: "https://upriss.github.io/fca/fcasoftware.html"
fetched: 2026-03-30T18:04:37Z
hash: "473ac178a4643a12ac39e665fb03cb2aea78fb459cc1922ede39206d1df78a73"
---

# FCA Software

Maintained by Uta Priss, Formal Concept Analysis Homepage.

## Formal Concept Analysis Applications and Demos

- **Odis-Web** -- Conexp-like online tool (sourcecode of the frontend and the backend available on GitHub)
- **LatViz** and RV-xplorer -- lattice visualization tools
- **Fca Tools bundle** -- online FCA tool suite at fca-tools-bundle.com
- **FcaStone online demo** -- online demo for binary relations and FCA
- **Concept Neighbourhoods in Roget's Thesaurus** -- shows concept lattices derived from Roget's Thesaurus
- **Lattice Drawing Software** -- lattices in general, not FCA-specific, Java applet/download
- **Virtual Museum of the Pacific** -- uses FCA in the background for organizing museum collections
- **RCAVIZ** -- an online tool to visualize and explore a relational dataset with Relational Concept Analysis

## Formal Concept Analysis Software (Downloadable)

FCA Topics page on Github lists many projects. Key tools include:

- **Tockit, Score, ToscanaJ, Tupleware** at sourceforge -- Java-based FCA tools
- **ConExp** (Concept Explorer) -- Java FCA tool at sourceforge
- **ConExp FX** -- partial reimplementation of ConExp by Francesco Kriegel
- **ConExp-NG** -- reimplementation of ConExp by Robert Jaeschke's students, uses FcaLib
- **Conexp-clj** -- Clojure-based FCA tool by Daniel Borchmann
- **Galicia** -- FCA tool from University of Montreal
- **FcaStone** -- format conversion software and command-line lattice generation
- **Camelis** -- Logical Information System based on FCA
- **concepts.py** -- Python implementation by S. Bank (available on PyPI)
- **GALACTIC** -- a set of python3 packages for studying Formal Concept Analysis by K. Bertet, C. Demko and others
- **Python FCA Tool** -- developed at HSE, Russia
- **fcaR** -- an FCA package written in R
- **FCA4J** -- a jar containing Java algorithms to compute concept lattice, Iceberg Lattice, AOC-poset, Duquenne-Guigues Basis
- **Lattice Miner** -- lattice mining tool
- **Lattice Navigator** -- lattice visualisation and context editing, written in C#

## Plugins for Using FCA with Other Software

- FCA Extension for Excel
- Protege plugins (FcaView Tab, OntoComP)
- FcaJava (Eclipse plugin for exploring Java)
- Notes on how to use FCA with Sage and NetworkX

## Relevance to Tag-Based Knowledge Systems

Formal Concept Analysis (FCA) provides the mathematical framework for understanding tag intersections. Given a set of objects (documents/sources) and attributes (tags), FCA constructs a concept lattice where each node represents a "formal concept" -- a maximal set of objects sharing a maximal set of attributes. This is precisely the mathematical structure that emerges from tag intersections in a knowledge repository:

- A formal concept {sources tagged A AND B} with attributes {A, B} is exactly a tag intersection query
- The lattice ordering shows which tag-sets are refinements of others
- Navigation up/down the lattice corresponds to broadening/narrowing tag selections
- The lattice reveals implicit groupings that no single tag captures

FCA tools can visualize these relationships as Hasse diagrams (line diagrams), showing the complete structure of how tags and tagged items relate.
