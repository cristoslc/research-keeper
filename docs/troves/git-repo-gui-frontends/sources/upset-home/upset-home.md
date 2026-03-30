---
source-id: "upset-home"
title: "UpSet: Visualization of Intersecting Sets"
type: web
url: "https://upset.app/"
fetched: 2026-03-30T18:04:37Z
hash: "d17f44c587b659945be22fbdd993c1faed5655f66c6c1e0b8ba069c1140be0c3"
---

# Visualizing Intersecting Sets

Understanding relationships between sets is an important analysis task. The major challenge in this context is the combinatorial explosion of the number of set intersections if the number of sets exceeds a trivial threshold. The most common set visualization approach -- Venn Diagrams -- doesn't scale beyond three or four sets. **UpSet, in contrast, is well suited for the quantitative analysis of data with more than three sets.**

UpSet visualizes set intersections in a matrix layout. The matrix layout enables the effective representation of associated data, such as the number of elements in the intersections.

## When should you use UpSet?

**UpSet works best for set data with more than three and less than about 30 sets**. For fewer than 4 sets, an area-proportional Venn diagram might be the better choice, as they are immediately familiar to everyone.

**UpSet is well suited for analyzing distributions and properties of many items**. Items are abstracted away as "counts", though attributes of the items can be visualized in integrated or adjacent plots. If you want to see individual items in your set, you should probably go with an Euler Diagram.

**UpSet shines when you want to look at all combinations of how sets intersect.** If you want to look at pairwise intersections between sets, some sort of co-occurrence matrix might be a better choice.

## UpSet Explained

UpSet plots the intersections of a set as a matrix. Each column corresponds to a set, and bar charts on top show the size of the set. Each row corresponds to a possible intersection: the filled-in cells show which set is part of an intersection. Also notice the lines connecting the filled-in cells: they show in which direction you should read the plot.

Here you can see examples of how these intersections correspond to the segments in a Venn diagram. The first row in the figure is completely empty -- it corresponds to all the elements that are in none of the sets. The green (third) row corresponds to the elements that are only in set B, (not in A or C). The orange (fifth) row represents elements that are shared by sets A and B, but not with C. Finally, the last (violet) row represents the elements shared between all sets.

This layout is great because we can plot the size of the intersections (the "cardinality") as bar charts right next to the matrix. This makes the size of intersections easy to compare.

The matrix is also very useful because it can be sorted in various ways. A common way is to sort by the cardinality (size), but it's also possible to sort by degree, or sets, or any other desired sorting.

Finally, UpSet works just as well horizontally or vertically. Vertical layouts are better for interactive UpSet plots that can be scrolled, while horizontal layouts are best for figures in papers.

## Interpreting UpSet Plots

**You should be careful about interpreting data where the size of the sets is very different.** For example, looking at movie genres, the 2-set combination of "Drama" and "Comedy" is the largest two-set intersection. While this is a correct observation it seems odd: dramas and comedy don't seem to go together all that well. What we're seeing here is an effect of the large size of the "Drama" and "Comedy" sets. To understand this, it's important to also look at the set sizes, and hence **no upset plot should omit the visualization of set sizes**. The "Deviation" (orange and blue bars) indicates how much an intersection deviates from the expected size if we assumed that set membership were random.

## UpSet vs. Venn Diagrams

Venn diagrams are not suitable to visualize intersections of more than three or four sets. A six-set venn diagram published in Nature shows the relationship between the banana's genome and the genome of five other species. While this figure looks fun, it is not a useful visualization. It's really hard to trace which intersection involves which sets. It's not obvious which is the biggest intersection from the visualization -- you have to read the labels one by one.

In UpSet, the vast majority of genes is shared between all plants, and the first three species (Oryza_sativa, Sorghum_bicolor, and Brachypodium_distachyon) seem to be highly related, as all of them are part of the top-three intersections. In contrast, the sixth species (Phoenix dactylifera) seems to be most different from the others. Such an analysis is almost impossible with a Venn diagram.

**Citation:** Alexander Lex, Nils Gehlenborg, Hendrik Strobelt, Romain Vuillemot, Hanspeter Pfister. UpSet: Visualization of Intersecting Sets. IEEE Transactions on Visualization and Computer Graphics (InfoVis), 20(12): 1983--1992, doi:10.1109/TVCG.2014.2346248, 2014.
