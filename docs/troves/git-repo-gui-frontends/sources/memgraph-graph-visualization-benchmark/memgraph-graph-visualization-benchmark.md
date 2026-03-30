---
source-id: "memgraph-graph-visualization-benchmark"
title: "You Want a Fast, Easy-To-Use, and Popular Graph Visualization Tool? Pick Two!"
type: web
url: "https://memgraph.com/blog/you-want-a-fast-easy-to-use-and-popular-graph-visualization-tool"
fetched: 2026-03-30T18:04:37Z
hash: "1e8b6388f2f4252ba6aad9a08d3a768dde1c699c71dc34527d79c538aa5dc7ba"
---

# You Want a Fast, Easy-To-Use, and Popular Graph Visualization Tool? Pick Two!

By David Lozic, September 15, 2022

In our pursuit of creating the go-to platform for graph development, we researched existing graph visualization libraries since our old Memgraph Lab implementation struggled with performance issues.

There are a lot of visualization options out there. Some have a very wide use case, others are popular but out of date, while the rest have performance issues or provide a terrible developer experience. The main focus of our research was JavaScript libraries since we were looking for a tool to integrate into our ecosystem.

## Requirements

We already used a graph visualization library in our previous Memgraph Lab implementation, so we knew what we were looking for this time around.

### Popularity and maintenance

The library in question needs to be popular and maintained. This was a key requirement since our existing Memgraph Lab implementation relied on a not-so-recently deprecated library -- Vis. And although a passionate community still supports it, we preferred an up-to-date library with official support from the original creators. We measured the popularity by GitHub stars, npm weekly downloads, and how long ago was the latest publish date.

### Ease of use

Ideally, the library has to be easy to use to shorten our development time. To estimate this, we judged the contenders' documentation on a subjective scale from 1 to 5.

### Speed and multithreading capabilities

It would be perfect if the library were fast, but the multithreading capabilities were even more important. In web technologies, multithreading is done via WebWorkers. For them to work, the most computationally expensive operations mustn't depend on the DOM (Document Object Model), because WebWorkers don't have access to the browser window reference, so any library that depends on that won't perform well.

### Styling

The library needs to have a flexible styling system where we can decorate graph properties such as node and edge shapes, colors, sizes, etc.

## Graph visualization landscape overview

| | GitHub stars | Weekly downloads | Latest version / latest publish date | Documentation | Ease of use | Rendering / styling capabilities | Multithreading |
|---|---|---|---|---|---|---|---|
| Vis | 7.9k | 34k | 4.21.0-EOL / 3 years ago deprecated | 5 | 5 | 5 | no |
| vis-network | 2.2k | 70k | 9.1.2 / 5 months | 5 | 5 | 5 | no |
| D3.js | 103k | 1.9M | 7.6.1 / 2 months | 5 | 3 | 1 | yes |
| d3-force | 1.4k | 2.2M | 3.0.0 / 1 year ago | 5 | 3 | 1 | yes |
| SigmaJS | 10.1k | 3.5k | 2.3.1 / 3 months | 2 | 4 | 5 | yes |
| Graphology | 718 | ~70k | 6 months | 5 | 4 | 1 | yes |
| VivaGraphJS | 3.5k | 89 | 3 years | 4 | 4 | 5 | no |
| Cytoscape.js | 8.7k | ~65k | 3.22.1 / 2 months | 5 | 4 | 5 | no |
| NeoVis.js | 1.2k | 500 | 2.0.0 / 2 months | 4 | 5 | 5 | ? |
| Cosmos | 182 | - | 1.0.0 / 2 months | 5 | 5 | 3 | yes |

That is how we ended up with three main candidates - VisJS, D3, and SigmaJS.

### VisJS

A very popular, easy-to-use tool with rich documentation that provides a lot of graph visualization options through the vis-network repository. Our old Memgraph Lab used Vis to simulate and render graph results. What we liked the most was the powerful graph styling options that the library provides.

The problem is that the library is tightly coupled, and it's hard to separate the physics computation simulation from the visual rendering engine. This is a problem in a WebWorker environment, which doesn't have access to the window object. Enormous issues also arise when trying to cram a big graph into Vis. Simulating and rendering such a graph takes ages and what's worse -- blocks the main thread which results in a terrible user experience.

### D3

D3.js is the gold standard of visualization libraries. The strength of D3 lies in its modularity. It's very cleanly segmented into several repositories, which, when combined, form D3 as we know it. One of the drawbacks is that it requires a pretty steep learning curve. Another drawback is that D3 by itself doesn't provide any out-of-the-box graph visualization capabilities if you want to use the HTML5 Canvas API. You have to do the drawings manually.

### SigmaJS

Another candidate is SigmaJS -- a powerful tool with impressive performance. It uses WebGL in its visualization which is by far the fastest option but introduces a layer of complexity. While SigmaJS focuses on visualization, it relies on the Graphology library for graph layout and simulation calculation. The big issue for us with SigmaJS is the lack of documentation. It does, however, have good examples written on the documentation page.

### Others (Honorable Mentions)

- **VivagraphJS** -- Good option with WebGL rendering capabilities but low weekly downloads and prolonged publish dates.
- **Cytoscape** -- Amazing platform originally for molecular interaction networks. DOM-dependent architecture doesn't support multithreading.
- **NeoVis** -- A fork of the Vis library adapted to Neo4j. Low weekly downloads.
- **Cosmos** -- Extremely fast, can render more than 100k nodes. Performs simulation calculations on the GPU. Limited styling capabilities.

### Commercial and standalone products

- **Graphistry** -- Extremely powerful analytics platform for big data.
- **Linkurious** -- Visualization platform for detecting complex criminal activity.
- **Ogma** -- Commercial JavaScript library for large-scale graph visualization, by Linkurious.
- **Gephi** -- Free and open-source graph visualization and exploration platform.

## Benchmark results

| Setup | D3 (Canvas) | Vis (Canvas) | Vis (Canvas, Optimized) | Old Memgraph Lab (Vis) | SigmaJS (WebGL) |
|---|---|---|---|---|---|
| Render first 100 nodes, 100 edges | 0.4s | 2s | 2s | 3s | 1s |
| 1k nodes, 1k edges | 3.2s | 1:14min | 45s | 1min 27s | 2s |
| 10k nodes, 10k edges | 27s | very long | 10.5min | very long | 5-10s |
| Simulate first 100 nodes, 100 edges | 0.2s | 1.2s | 1s | 2s | instant |
| 1k nodes, 1k edges | 2s | 35s | 15s | 1min 15s | 2s |
| 10k nodes, 10k edges | 26s | ~15-20min | 7min | >20min | 15s |

Vis is the slowest of the bunch being an order of magnitude slower than the competitors. The D3-based solution is in the middle of the pack, while the WebGL-based SigmaJS is considerably quicker in rendering bigger graphs.

## Our decision -- enter the Orb

We decided to create our own library called Orb by using the power of d3-force simulations and our own rendering engine, which uses parts of the Vis canvas implementation. The reasoning was that it would be easier to do this than to adapt SigmaJS to fit our GSS specification. We also made Orb extensible and left space for a WebGL renderer in the future.

Testing in Memgraph Lab v2 showed Orb is 20x faster on smaller graphs and up to 40x faster on larger ones:

| Dataset | # of nodes | # of relationships | Old Lab | New Lab | Improvement |
|---------|-----------|-------------------|---------|---------|-------------|
| Game of Thrones | 3000 | 12000 | 10 min | 15 sec | 40x faster |
| Pandora Papers | 400 | 700 | 50 sec | 3 sec | 20x faster |
| Europe road network | 1000 | 60000 | Too much time | 20 sec | -- |

## Conclusion

It seems that there still doesn't exist a go-to graph visualization library that satisfies all needs. The choice between D3, Graphology/SigmaJS, and building your own depends on your priorities around popularity, documentation, styling, performance, and multithreading support. Without the styling requirement, SigmaJS seems like a solid offering and a reasonable choice. Cosmos is an extremely fast library that works great for big graphs by performing simulation calculations and rendering on the GPU, but lacks styling capabilities.
