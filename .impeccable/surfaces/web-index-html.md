---
version: 1
slug: "web-index-html"
primary_target: "web/index.html"
related_targets: []
---

# Surface: web/index.html (the hosted page)

Mode: Persuade. One page; the visitor (Bend/PL reader, baseball-analytics reader, portfolio viewer) arrives once from a link and must leave believing: the scorebook is proven, every simulated game runs through that proof, and the result tracks MLB's number on real games. Action: reproduce it (commands on the page) or open the source.

Proof on hand: the live/replayed game feed (per-play CSV + meta), the 2026-10-23 benchmark, verbatim code from game.bend / sim.bend, the four laws. Binding constraint: every diagram on the page, including the live win-probability curve, is rendered by Pele (pele.run) from Mermaid source. Numbers are binding; prose may be tightened.

## Direction contract

seed: seed:a6a4d03096313d3c (pick card chosen: The Scorebook)

THESIS: The page is a baseball scorebook being kept, and the thing it keeps is the proof. It refuses the engine-showcase arrangement (headline, stat cards, glowing chart, code block).

OWN-WORLD: Buff card stock; printed scorebook grid in teal; graphite pencil for every entry the engine writes; one red pencil for the play happening now. Printed type is a condensed gothic (Archivo Narrow) for headings, column heads and tables, Archivo for instructions, tabular figures everywhere; pencil entries are a handwriting face (Caveat) used only for what a keeper would write: the outs, the running note, "proven". Rules are 1px teal; no radius, no shadow, no cards. Diagrams (Pele) are printed in teal line on the stock with graphite highlights.

STORY: The visitor sees a real game being scored cell by cell, with Bend's number written beside MLB's after each play; reads at the foot that the box score balances under OBR 9.03(c) because it is proven; learns in the printed instructions how the card is kept (step, 2^d fork, laws, harness) with Pele diagrams of the pipeline, the fork tree, and the proof gate; sees the season benchmark as a standings table; and leaves by the reproduce commands.

FIRST VIEWPORT: Full-width scorebook page. Top rule: "Official Scorebook · Bend vs MLB", game line (away @ home with logos, gamePk, date, feed status printed in pencil). Line score for both teams by inning (runs per inning computed from the feed). Below, left ~65%: the batting team's scorecard page, rows = batting-order slots 1–9 (inferred from plate-appearance count, labelled so), columns = innings; each cell a printed diamond with runners filled in graphite, outs and Bend WP pencilled; the cell of the latest play outlined in red pencil. Tabs on the page edge flip between the two teams' pages. Right ~35%: the keeper's margin: Bend / MLB / Δ as the running tally, the current bases-and-outs, and the Pele xychart of both curves as "Figure 1". Primary action: "Reproduce this card" printed at the top of the margin, linking to the commands; "Source" beside it.

FORM: The scorecard grid is the form; the page flips to the batting team as half-innings change (signature interaction: the red outline redraws into the new cell, the page tab flips). Sections below are the card's printed back: How this book is kept (4 steps + 3 Pele diagrams), Proof of box score (laws table), Season benchmark (tables), Reproduce, Notes (limits).

HONEST RISK: Reads as theme if cells do not carry the real plays; the slot inference must be labelled; 9×9 grid needs horizontal scroll on phones.

Function preserved: 5 s polling, live→replay fallback, ?pk=, freshness indicator, CSV/meta links. Dropped: dark/light toggle (paper has one colour).
