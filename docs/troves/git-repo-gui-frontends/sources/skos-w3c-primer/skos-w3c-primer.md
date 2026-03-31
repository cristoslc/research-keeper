---
source-id: "skos-w3c-primer"
title: "SKOS Simple Knowledge Organization System Primer -- W3C"
type: web
url: "https://www.w3.org/TR/skos-primer/"
fetched: 2026-03-30T18:04:37Z
hash: "6da627792f49f6e943fdf25f5c9417a129621768778ef80d2959d961dd6feef2"
---

# SKOS Simple Knowledge Organization System Primer

W3C Working Group Note, 18 August 2009

## 1. Introduction

SKOS -- the Simple Knowledge Organization System -- provides a model for expressing the basic structure and content of concept schemes such as thesauri, classification schemes, subject heading lists, taxonomies, folksonomies, and other similar types of controlled vocabulary. As an application of the Resource Description Framework (RDF), SKOS allows concepts to be composed and published on the World Wide Web, linked with data on the Web, and integrated into other concept schemes.

SKOS is designed to provide a low-cost migration path for porting existing knowledge organization systems to the Semantic Web. SKOS also provides a lightweight, intuitive language for developing and sharing new knowledge organization systems. It can be used on its own, or in combination with more-formal languages such as the Web Ontology Language (OWL).

SKOS can also be seen as a bridging technology, providing the missing link between the rigorous logical formalism of ontology languages such as OWL and the chaotic, informal and weakly-structured world of Web-based collaboration tools, as exemplified by social tagging applications.

## 2. The SKOS Data Model

### 2.1 Concepts

The fundamental element of the SKOS vocabulary is the concept. Concepts are the units of thought -- ideas, meanings, or (categories of) objects and events -- which underlie many knowledge organization systems.

As SKOS is based on RDF, every concept is identified by a URI. This makes it possible to unambiguously reference a concept in any SKOS application.

### 2.2 Labels

SKOS provides three properties for attaching lexical labels to concepts:
- **skos:prefLabel** -- the preferred lexical label (one per language)
- **skos:altLabel** -- alternative lexical labels (synonyms, abbreviations, etc.)
- **skos:hiddenLabel** -- hidden labels for variant spellings, common misspellings

### 2.3 Semantic Relations

SKOS provides three core semantic relation properties:
- **skos:broader** -- indicates a more general concept
- **skos:narrower** -- indicates a more specific concept
- **skos:related** -- indicates an associative relationship between concepts that are not hierarchically related

These properties can be used to build hierarchical concept schemes (taxonomies) and add cross-references between concepts.

### 2.4 Concept Schemes

A concept scheme is a set of concepts, optionally including statements about semantic relationships between those concepts. The **skos:ConceptScheme** class represents these, with **skos:inScheme** to link concepts to schemes and **skos:hasTopConcept** to identify the top-level concepts.

### 2.5 Documentation Properties

SKOS provides properties for documentation: **skos:note**, **skos:scopeNote**, **skos:definition**, **skos:example**, **skos:historyNote**, **skos:editorialNote**, **skos:changeNote**.

## 3. Advanced Features

### 3.1 Collections

SKOS supports collections of concepts via **skos:Collection** and **skos:OrderedCollection**. These group concepts that share something in common but where the grouping is not a hierarchical or associative relationship.

### 3.2 Mapping Between Concept Schemes

SKOS provides mapping properties for linking concepts across different schemes:
- **skos:exactMatch** -- concepts with equivalent meaning
- **skos:closeMatch** -- concepts with sufficiently similar meaning to be used interchangeably in some applications
- **skos:broadMatch**, **skos:narrowMatch**, **skos:relatedMatch** -- hierarchical and associative mappings

Note on skos:exactMatch vs. owl:sameAs: SKOS provides skos:exactMatch to map concepts with equivalent meaning, and intentionally does not use owl:sameAs. When two resources are linked with owl:sameAs they are considered to be the same resource and triples are merged. skos:exactMatch conveys a weaker assertion -- the concepts are interchangeable in many contexts but remain separate identities.

### 3.3 Notations

The **skos:notation** property assigns a lexical code to a concept within a given scheme, such as Dewey Decimal numbers.

## 4. Relationship to OWL

SKOS is not a formal knowledge representation language. The "knowledge" in a SKOS concept scheme is about the concepts themselves (e.g., "concept X has preferred label 'Y' and is part of thesaurus Z"), not about facts about the world as might be expressed in a formal ontology. SKOS data are expressed as RDF triples. SKOS may be used alongside OWL, but they serve different purposes: OWL for formal domain modeling, SKOS for lightweight concept organization.

## 5. Use Cases

SKOS is used for:
- Migrating legacy thesauri and classification schemes to the Semantic Web
- Building and sharing controlled vocabularies
- Linking concepts across different knowledge organization systems
- Providing structured concept schemes for information retrieval
- Supporting faceted search and browse interfaces
- Bridging formal ontologies with informal folksonomies
