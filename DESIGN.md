---
name: Bend vs MLB
description: A baseball scorebook being kept, and the thing it keeps is the proof.
colors:
  stock: "#efe6d2"
  print: "#275f55"
  print-tint: "rgba(39, 95, 85, 0.09)"
  print-rule: "rgba(39, 95, 85, 0.55)"
  graphite: "#1d1d1b"
  graphite-soft: "#55544c"
  red: "#b3362b"
typography:
  display:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "clamp(30px, 4.4vw, 46px)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.02em"
  headline:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.08em"
  title:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "normal"
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  body-table:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  caption:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label-small:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "0.08em"
  label:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.1em"
  hand:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "21px"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "normal"
  hand-note:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  hand-score:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "19px"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "normal"
  hand-now:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "20px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  hand-tally-phone:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "38px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "normal"
  hand-tally:
    fontFamily: "Caveat, Segoe Print, cursive"
    fontSize: "44px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "normal"
  mono:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  none: "0"
  out-circle: "50%"
spacing:
  hair: "2px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "14px"
  section: "44px"
  page-bottom: "56px"
  cell-w: "72px"
  cell-h: "66px"
components:
  button-primary:
    backgroundColor: "{colors.print}"
    textColor: "{colors.stock}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "7px 14px"
  button-primary-hover:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.stock}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.print}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 0 2px"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.print}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0"
  table-head:
    backgroundColor: "{colors.print-tint}"
    textColor: "{colors.print}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "6px 10px"
  pre-block:
    backgroundColor: "{colors.print-tint}"
    textColor: "{colors.graphite}"
    typography: "{typography.mono}"
    rounded: "{rounded.none}"
    padding: "10px 14px"
  scorecard-cell:
    backgroundColor: "{colors.stock}"
    textColor: "{colors.graphite}"
    rounded: "{rounded.none}"
    padding: "0"
    width: "{spacing.cell-w}"
    height: "{spacing.cell-h}"
---

# Design System: Bend vs MLB

## Overview

**Creative North Star: "The Scorebook"**

The page is a baseball scorebook being kept, and the thing it keeps is the proof. The material is buff card stock; everything the printer put on the card (headings, column heads, rules, tables, diagrams, the MLB number) is one teal ink; everything the engine writes (outs, runners, Bend's number, the running note, "proven") is graphite pencil in a handwriting face; and one red pencil marks the play happening now. There is no second surface. Depth is a thicker rule or a tint of the same ink, never a card, a shadow, or a radius.

Density is a filled-in card's: tight 1px-ruled tables, 72×66 boxes, 8–14px gaps, 72ch measure for printed instructions. The printed voice is condensed, uppercase, letterspaced; the pencilled voice is large, loose, and never used for anything the printer would have set. Pele diagrams are themed to print in the same teal on the same stock with graphite highlights, so the figures read as part of the card rather than as embedded screenshots. The rejected arrangement is the engine showcase: headline, stat cards, glowing chart, dark mode, code block as hero.

**Key Characteristics:**
- One material (buff stock) and three marks on it: teal print, graphite pencil, red pencil.
- Printed vs pencilled is a semantic distinction: the face tells you who wrote the value.
- Rules carry all structure: 3px (page edge), 2px (section head), 1px solid (row/header), 1px at 55% (interior grid).
- No radius, no shadows, no cards, no dark theme; `color-scheme: light` is declared.
- Tabular figures everywhere (`font-variant-numeric: tabular-nums` on body).

## Colors

A single ink on a single stock, with pencil and red pencil as the only other marks.

### Primary
- **Scorebook Teal** (`print`): the printer's ink. Headings, column heads, labels, links, rules, the masthead, the primary action's fill, Pele line work, the MLB number in each box, and the "up" (Bend better) delta state. Two derived strengths of the same ink: **Teal Rule** (`print-rule`, 55% alpha) for interior table/grid borders and the sticky-column hairline; **Teal Tint** (`print-tint`, 9% alpha) for header rows, team rows, the batter column, run totals, and code block backgrounds.

### Secondary
- **Red Pencil** (`red`): the one highlight. The outline of the latest play's box, the live inning's line-score run, the stale/dead feed state (dead is also struck through 2px), and every `:focus-visible` outline. It is a pencil, so it only ever marks something that is happening or wrong right now.

### Neutral
- **Buff Stock** (`stock`): the page and every surface; also the text colour on teal fills and on the filled third-out circle. There is no alternate stock.
- **Graphite** (`graphite`): body text, every pencilled value, the batter's path, the out circle, Pele's accent and first series, hover colour for links/summaries/the primary button, and the "down" delta state.
- **Soft Graphite** (`graphite-soft`): captions, figure/diagram captions, the standings note and caption, tally sub-line, bench caption.

### Named Rules
**The Three Marks Rule.** Every colour on the page is one of three marks on the stock: teal print, graphite pencil, red pencil. There is no fourth ink; tints and alpha rules are strengths of teal, never new hues.

**The Red Pencil Rule.** Red marks only what is happening now or what is wrong now (latest play, live inning, stale feed, focus). It never decorates, never fills a surface larger than a 2px stroke, and never appears on the printed back of the card except as focus.

**The Printed/Pencilled Rule.** If the printer could have known it before the game, it is teal in Archivo Narrow; if the keeper wrote it during the game, it is graphite in Caveat. MLB's number is printed; Bend's is pencilled.

## Typography

**Display Font:** Archivo Narrow (with Arial Narrow, sans-serif), self-hosted at `/fonts/ArchivoNarrow.woff2`, weights 400–700
**Body Font:** Archivo (with system-ui, sans-serif), self-hosted at `/fonts/Archivo.woff2`, weights 400–600
**Hand Font:** Caveat (with Segoe Print, cursive), self-hosted at `/fonts/Caveat.woff2`, weights 400–700
**Mono Font:** ui-monospace stack (SF Mono, Menlo, Consolas)

**Character:** A condensed gothic for everything printed on the card, its wider sibling for the instructions on the back, and a handwriting face reserved for what a keeper writes. Tabular figures are set on `body` so every number in every column lines up.

### Hierarchy
- **Display** (700, `clamp(30px, 4.4vw, 46px)`, 1, 0.02em, uppercase): the masthead `h1` ("Official Scorebook"), teal.
- **Headline** (700, 24px, 1.2, 0.08em, uppercase): section heads on the back of the card, teal, between a 2px top rule and a 1px rule.
- **Title** (700, 18px, 1.25): step titles in the instructions, graphite. Line score team names use 15px of the same face.
- **Body** (400, 15px, 1.5): Archivo, graphite; printed prose, lede, step text. Measure 72ch (`max-width: 72ch`; `.balance` definitions too), table captions 90ch.
- **Caption** (400, 13px, 1.55): Archivo, soft graphite, measure 68ch; figure/diagram captions, the standings caption and note. The key to the sheet is 13px/1.5 Archivo in graphite; the tally sub-line stays 12px.
- **Label** (700, 11–13px, 1.2–1.6, 0.06–0.1em, uppercase): Archivo Narrow, teal; field labels (11px/0.1em), table heads (11px/0.1em), margin `h2` (12px/0.1em), nav and footer (12–12.5px/0.08em), team rows (13px/0.08em, graphite), the half-inning row labels (11px/0.08em), summaries (13px/0.08em), buttons (12–13px/0.1em). Grid column heads are 12px at 0.02em. Printed numbers on the sheet are Archivo Narrow 400 teal: the box's MLB number 12px, the half-inning MLB and market rows 13px, RBI and "×N" 11px. Nothing printed on the sheet is under 11px.
- **Hand** (500, 13–23px, 1–1.25): Caveat, graphite; field values (21px), line-score runs (19px), tally running note (23px), batter names (17px; substitutes 14px), the play (16px, 700; long plays and two-line plays 13px), the box's Bend number (15px, 700), H–AB (18px), the half-inning tally (15px) and Bend row (15px, 700), the "now" line (20px), the "proven" marks in the laws table (21px), step numerals (22px, 700, teal). The out circle is 13px/700, rotated −6°.
- **Hand Tally** (700, 44px, 1; 38px below 720px): the single large pencilled Bend number in the keeper's margin.
- **Mono** (400, 12.5px, 1.5): code blocks on a teal tint with a 1px rule; inline `code` is 0.86em of its context.

### Named Rules
**The Keeper's Hand Rule.** Caveat is used only for what a scorekeeper would write by hand during the game: the batting order's names, the play notation, outs, runs, the inning totals, the win number, the running note, "proven", the step numerals. Never for headings, labels, links, prose, or anything the printer set.

**The Condensed Print Rule.** Anything printed on the card as structure (headings, column heads, labels, navigation, buttons, footer) is Archivo Narrow 700, uppercase, letterspaced 0.06–0.1em. Running prose is Archivo 400 at 15px, never condensed.

## Layout

One page, `.book`, max-width 1260px, centred, padded `22px clamp(12px, 3vw, 32px) 56px`. The masthead is a two-column grid (`1fr auto`, gap 8px 24px, aligned to the baseline) between a 3px top rule and a 1px bottom rule; the game fields below are an `auto-fit, minmax(150px, 1fr)` grid separated by 1px teal-rule dividers.

The spread is a two-column grid: the scorecard sheet (`minmax(0, 1fr)`) and the keeper's margin (fixed 360px), gap 14px 28px, rows `auto auto 1fr`, with named areas `sheet` / `lead` / `rest` / `guide`: the margin's lead (actions + tally) sits beside the top of the sheet, the "Now" note below it, and the guide (the season standings, then the key to the sheet) last. The guide's area runs the rest of the sheet's height, so at ≥1161px wide and ≥860px tall the guide is `position: sticky; top: 12px` and stays beside the sheet as it scrolls (it is about 830px tall, hence the height guard). The sheet is sized to fill its column exactly at the page's full width (88px batter column, nine 72px innings, 50px H–AB); extra innings scroll. Figure 1, the live chart, is printed full width beneath the spread (22px above, 1px teal rule), so the curve gets the page's whole measure; its Pele height is 320px, or 250px when the chart is narrower than 640px. At ≤1160px the guide becomes `display: contents` and the spread stacks `lead → standings → key → sheet → rest` in one column, so the result and the key come before the sheet; Figure 1 is still last. At ≤720px the masthead collapses to one column, hand sizes step down (fields 19px, line-score 17px, tally 38px), and the batter column and the half-inning row labels become sticky (`position: sticky; left: 0`) on an opaque stock background with the tint overlaid via `::before` so the grid can scroll horizontally beneath them; the team name rides along in a sticky span.

Spacing rhythm is small and even: 2px (field label→value), 4px (caption gap), 6px (step text, key and standings prose), 8px (masthead, margin top padding), 10–12px (pre padding, section prose, tables, details), 14px (margin gap, spread gap, linescore top), 22px (between steps, above Figure 1), 28px (spread column gap), 44px (between back-of-card sections and before the footer), 56px (page bottom). The scorecard grid itself is `table-layout: fixed`, `width: max-content`, boxes `72×66px`, header row 24px, team rows 26px, half-inning rows 22px (the first, with its two-line label, about 34px), and scrolls horizontally inside a 1px teal frame (`.grid-scroll`). Every horizontally scrolling region sets `scrollbar-color: var(--print) var(--stock)`.

## Elevation & Depth

Flat. There are no elevation shadows anywhere on the page. Depth is conveyed by rule weight (3px page edge, 2px section head, 1px solid row, 1px at 55% interior) and by the 9% teal tint on header rows, team rows, run totals and code blocks. The `box-shadow`s in the build are not elevation: each is a 1px inset teal-rule line that redraws a grid rule `position: sticky` would otherwise lose (the sticky batter column's `inset -1px 0 0 var(--print-rule)`; on the benchmark page the sticky row-name column below 720px and the sticky column heads of Every game).

### Named Rules
**The No Shadow Rule.** Nothing on the card floats. If a surface needs separation, give it a rule or a tint of the ink; never a drop shadow, blur, or lifted hover.

**The Rule Weight Rule.** Hierarchy of separation is rule weight: 3px for the page edge (masthead top, footer top), 2px for a section head, 1px solid for rows and frames, 1px at 55% alpha for interior cells.

## Shapes

Square. `--pele-radius: 0` and every box on the page has no radius. Borders are 1px (solid teal or 55% teal), with 2–3px only for the page/section rules. The round forms are the scorer's: the pencilled out circle in a box (18px, `border-radius: 50%`, 1.5px graphite border, rotated −6°; filled graphite with stock text on the third out), the pencilled ring around a big swing's win number, and the 5px run dots. The box's diamond is a 38px inline SVG (`viewBox 0 0 44 44`): teal 1px base lines, the batter's path over them in 2.4px graphite with round caps and joins, the whole diamond filled graphite at 30% when he scored. The red pencil outline is an SVG `rect` (2.4px stroke, round joins) inset −1px around the box with `pathLength="1"` so it draws itself.

## Components

Everything is a mark on the card: printed, pencilled, or red. Buttons are printed stamps, tables are the card's ruled grid.

### Buttons
- **Shape:** square (0 radius), no border.
- **Primary** (`.actions a.primary`): teal fill, stock text, Archivo Narrow 700 13px uppercase 0.1em, padding 7px 14px. Used once, for "Reproduce this card".
- **Hover / Focus:** fill turns graphite; focus is the global 2px red outline at 2px offset.
- **Quiet** (`.actions a.quiet`): no fill, teal label text 12px, 1px teal bottom rule with 2px padding below. Used for Source / Raw CSV / Meta beside the primary.

### Tables (line score, laws, benchmark, scorecard grid)
- **Border:** 1px teal-rule on every cell; the scorecard grid uses `border-spacing: 0` with right/bottom rules only, inside a 1px solid teal frame.
- **Header:** 9% teal tint, teal Archivo Narrow 700 (11px/0.1em uppercase for laws/bench; 12–13px for line score and grid).
- **Body:** 14px Archivo for printed cells, padding 6px 10px; line-score runs and laws "proven" marks are Caveat in graphite; run totals (`td.r`) are 700 on the tint; numeric columns right-aligned and `nowrap`.
- **States:** `td.up` teal, `td.down` graphite 600; live inning `td.live` red.
- **Overflow:** wrapped in `.tablewrap` / `.linescore` / `.grid-scroll` with horizontal scroll and teal scrollbars.

### Inputs / Fields
There are no form inputs. The game card fields (`dl.fields`) are printed label (11px teal uppercase 0.1em) over a pencilled value (Caveat 500 21px graphite, single line, ellipsised); `.print` values fall back to Archivo 14px; `.stale` turns red; `.dead` turns red and is struck through at 2px.

### Navigation
- **Masthead nav:** inline uppercase Archivo Narrow 700 12.5px/0.08em teal links, no underline, gap 4px 18px; hover/focus draws a 1px teal bottom border. Wraps on narrow widths.
- **Footer:** same voice over a 3px teal top rule, `space-between`, links with a permanent 1px teal bottom rule.
- **Inline links:** teal, 1px underline offset 3px; hover graphite.

### Code blocks
`pre` is 12.5px mono on 9% teal tint inside a 1px teal rule, padding 10px 14px, 10px above, horizontal scroll with teal scrollbars. Inline `code` is 0.86em mono with no background.

### Scorecard Sheet (signature)
The whole game on one sheet, kept the way a scorer keeps a book: visitors over home, innings across, no page to flip. Each team's block opens with a team row (logo, name, visitors/home and runs; 1px solid teal rule above), then nine batting-order rows, then the after-the-half rows. The key to every mark is printed in the keeper's margin (see below), not under the sheet.
- **Batter column**: the slot number printed (11px teal), the batter who batted there pencilled (Caveat 17px), substitutes beneath (14px soft graphite); slot inferred from the plate-appearance count.
- **H–AB** at the row's end: the batter's hits for at-bats pencilled (Caveat 18px), runs batted in printed beneath (11px teal; no RBI on a double play or an error).
- **After the half**: one row per number, each labelled in the batter column (11px teal uppercase, sticky on phones) and filled in under every inning as it stood when the half ended: "After the half · R · H · LOB" pencilled (Caveat 15px), "Bend" pencilled (Caveat 700 15px), "MLB" printed and "Mkt median" printed (Archivo Narrow 13px teal; the median of the venues, a row only when the feed has market prices). The last row carries the 1px solid teal rule that closes the team's block.

Each 72×66px box is one plate appearance, filed under the half-inning it started in:
- **Diamond** (38px, centred at the top, 1px teal base lines): the batter's trip around the bases pencilled from home (2.4px graphite, round caps) to the last base he reached; shaded graphite at 30% when he scored. The trip is followed with Bend's own play codes (`code`: r3 r2 r1 batter, `-` stays, `X` out, `R` scores, `1–3` the base reached), the same moves Bend's `step` makes.
- **Play** pencilled in the diamond (Caveat 700 16px): K, a mirrored K for a called third strike, 1B…HR, BB, HBP, F8, L7, P4, 6-3, 3U, FC, E6, SF9; plays of five or more characters at 13px; two-part plays (4-6-3 DP, SAC 1-4) on two lines at 13px.
- **Out**: the out this batter made, circled top-left (18px, 1.5px graphite, rotated −6°; filled on the third), even when it came on a later play as a runner. Outs on one play are numbered lead runner first.
- **Runs**: a 5px graphite dot for each run scored on the play, stacked up the box's left edge from the bottom (3px apart), clear of the win numbers.
- **Win numbers** bottom-right, 5px apart: Bend's home-win number after the play pencilled (Caveat 700 15px), MLB's printed beside it (Archivo Narrow 12px teal); a decided game is written 100. A play that moved Bend's number 8 points or more has it circled in pencil, the scorer's mark for a turning point. Each venue's price, the batter and the play are in the box's `title` and screen-reader text; the markets per play are in Figure 1.
- "×N" (11px teal, top-right) when the order bats around and two appearances share a box; the box shows the later one.

The marks (`svg.dia`, `.play`, `.out`, `.dots`, `.nums`, `.more`) are styled once for `.cell` and `.key`; a box only positions them.

The latest play carries the red pencil rectangle; when it moves to a new box (`.drawn`) the rectangle draws itself over 900ms with `cubic-bezier(0.16, 1, 0.3, 1)`, disabled under `prefers-reduced-motion`.

### Keeper's Margin
A stacked aside under a 1px teal rule (14px gaps): the actions row; a 12px teal uppercase `h2`; the tally (Caveat 500 23px with the 44px 700 Bend number on its own line, a 12px soft-graphite Archivo sub-line for MLB and Δ, and a market reference line with each venue linked); then the "Now" note. Below it the guide, sticky on desktop, two sections each under a 1px teal rule:
- **Standings** (`table.stand`, "Bend vs MLB, by season", at most 440px wide): caption "Brier score: lower is better."; one row per benchmark run, built from `/bench/data-2025.json` and `/bench/data.json` (never typed in): the season linked to its benchmark page (Archivo Narrow 700 15px) with its games scored beneath, Bend's and MLB's Brier (Archivo Narrow 15px graphite), Δ with its 95% interval beneath (12px soft graphite), then the verdict on its own line (13px Archivo; 600 for a clear win). A 13px soft-graphite note says what Brier and Δ are and links to the season benchmark. If the data cannot load, the row points to the benchmark page.
- **Key to the sheet**: a one-line intro, then a `dl` of each mark drawn as on the sheet (58px column) beside what it means (13px/1.5 Archivo), in `auto-fill, minmax(300px, 1fr)` columns (one in the margin, two or three when stacked), then the red pencil and the batting-order inference. Every fact of the old sheet footnote is here; nothing depends on hover (each venue's price per play is in Figure 1). The key draws no red: the red pencil is described, not sampled.

The same season numbers are tabled on the back of the card in `#season` (`table.bench`: paired plays, Bend and MLB Brier, Δ with 95% CI, plays closer, games better, verdict).

### Figure 1
The Pele xychart of the home team's win probability after each play, mounted at `fontSize: 14` so tick labels and axis titles are 12px. The lines are told apart by mark, not hue (The Three Marks Rule): Bend (graphite, 2px, filled points), MLB (teal, 2px, open points: stock fill, 1.5px teal ring) and each market venue that priced the game (1.5px, butt caps, no points: Kalshi long-dashed `8 3` soft graphite, Polymarket dash-dot `8 3 1.5 3` teal, Polymarket US round dots `0 4` at 2px soft graphite). Two helper series are drawn first: "50%", a 1px teal-rule line with no points under the others, and "innings", a line at 100 that is never drawn (`display: none`) and exists to carry Pele point labels: the innings printed along the top in Archivo Narrow 700 12px teal, "▲1 ▼1 ▲2…" at the first play of each half-inning, or only "1 2 3…" at each inning's first play when half-innings would fall closer than 24px. Because Pele colours series by position, every data line is inked explicitly by the CSS that `inkLines` writes from `SERIES` / `VENUES` (`web/js/series.js`), the same objects the legend draws from, so a line and its legend sample cannot drift; the two helper series are styled in `web/scorebook.css`, and neither is in the legend or the line count of `accDescr`. The y-axis is named for the home team ("Brewers win %"), the x-axis "play, in order (innings along the top)". Pele's own legend is switched off (`showLegend: false`, which also returns its reserved width to the plot) because it cannot show the dash patterns; a printed legend sits between the heading and the chart, one item per drawn line: a 30px sample stroked exactly as the line (with a filled or open point where the line has points), the name (Archivo Narrow 700 12px uppercase, graphite) and its source in 12px soft graphite ("65,536 simulated games a play", "official win probability", "market price", "international market price", "US-regulated market price"). The caption (13px/1.55 soft graphite, 68ch) says what is plotted and which way favors whom, the 50% rule and the inning marks, where each line's numbers come from, the mean gap between Bend and MLB, how a missing price or MLB value is carried, and that markets are a reference.

### Pele diagrams
Themed via `.pele` custom properties: stock background and surface, teal foreground/line/border/muted, 9% tint alt surface, graphite accent and series 1, teal series 2, red critical/error, Archivo Narrow at 700 for titles and headings, mono stack for code, radius 0. Pencilled nodes (what Bend computes or what the proof gate lets through) are stock with a 1.6px graphite stroke. Wrapped in `figure.diagram` (14px top margin) with a 13px/1.55 soft-graphite caption (68ch) that says which way to read the diagram and what each mark means. Pele lays a diagram out to its box (on a phone the gate reflows top to bottom), and the page sets `--legible-w` on `.pele-src`, the least width at which the SVG's smallest label is still 10px, used as the SVG's `min-width`; narrower than that, the diagram scrolls inside its figure (teal scrollbar), a top-to-bottom one opening scrolled to its root. It is measured again whenever Pele redraws.

### Benchmark page (`/bench/`)
The back of the card set as standings, rendered from the run's JSON (`data.json`, `data-<season>.json` via `?run=`).
- **Result line:** under the lede, one line from the loaded run's paired MLB numbers: a 13px teal "Against MLB" label, the verdict stamp, Δ Brier with its 95% CI, and "Bend better in n of m games" (Archivo 16px graphite; Δ and the CI never break across lines).
- **Verdict stamps** (`b.v`): Archivo Narrow 700 12px (13px in the result line) uppercase 0.1em, padding 1px 7px, 1px border, `nowrap`. Clear win is a filled teal stamp with stock text, clear loss a filled graphite stamp with stock text, no clear difference an outline only (55% teal rule, soft-graphite text), so a result reads before its words.
- **Comparison tables** lead with the result: row name, Verdict, Δ (95% CI), then the detail columns. Row names never wrap. Below 1100px each CI drops under its Δ. Below 720px the Verdict column folds into the name cell (stamp under the name), the name column is sticky on opaque stock (9% tint over stock in the head) with its 1px inset rule, and a table wider than its column prints a cue under it (Archivo Narrow 700 11px teal uppercase: "Swipe the table for N more columns", counted live as it scrolls). Sticky cells sit at −1px so collapsed rules leave no gap for scrolled text.
- **Scores** caption opens "Not paired", with each source's play count, because its Briers come from different plays than Head to head.
- **Every game:** a short list (games Bend better/worse from the sign test, its furthest-ahead and furthest-behind game, any game that failed to replay), then one `details` fold per month (summary: month in the 13px label voice, game count in 13px soft-graphite Archivo), each table built on first open. Column heads are sticky (opaque tint over stock, 1px inset bottom rule): to the viewport above 720px, inside a 75vh scroll box below. The Unscored column prints only when some game has unscored rows.
- **Calibration figure:** a near-square Pele xychart (width = height, at most 520px, `fontSize: 14` so ticks and axis titles render 12px) with the printed legend stacked and the caption beside it above 720px, below it on phones. Bend is graphite with filled points, MLB teal with open points (stock fill, 1.5px teal ring) as on the scorebook's Figure 1, the ideal diagonal 1.5px dashed `6 4` teal rule; `bench.js` inks the lines (`inkLines`) and draws the legend from the same `SERIES` entries and its `IDEAL` mark.
- **Captions** are the 13px bench caption, capped at 90ch.
- **Missing run** (`?run=` with no file): the lede says there is no such run and links the runs on file (from the Runs field's links and titles); the data sections and their nav links are hidden.

## Do's and Don'ts

### Do:
- **Do** set every printed structural label in Archivo Narrow 700 uppercase with 0.06–0.1em tracking in teal (`print`).
- **Do** use Caveat only for values a scorekeeper writes during the game, in graphite, at 13px or larger (13px only for long and two-line plays inside the diamond; The Keeper's Hand Rule).
- **Do** separate with rules: 3px page edge, 2px section head, 1px row, 1px at 55% interior (The Rule Weight Rule).
- **Do** keep red to the latest play, the live inning, the stale feed and focus (The Red Pencil Rule).
- **Do** theme every Pele diagram through `.pele { --pele-* }` so it prints in teal on the stock with graphite highlights.
- **Do** keep `font-variant-numeric: tabular-nums` and right-align numeric columns.
- **Do** keep prose at 72ch and footnotes at 90ch.

### Don't:
- **Don't** add a radius to any box; the only round form is the pencilled out circle (The No Shadow Rule covers lift; Shapes covers corners).
- **Don't** add box-shadows, blurs, cards, or raised surfaces; depth is rule weight and 9% tint.
- **Don't** introduce a dark theme or a second stock colour; `color-scheme: light` is declared.
- **Don't** introduce a fourth hue; every colour is a strength of teal, graphite, or red on buff.
- **Don't** set headings, labels, links or prose in Caveat, or set the pencilled Bend number in a printed face.
- **Don't** render a diagram or chart with anything other than Pele.
