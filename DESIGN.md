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
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
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
- **Soft Graphite** (`graphite-soft`): captions, figure/diagram captions, sheet footnote, tally sub-line, bench caption.

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
- **Body** (400, 15px, 1.5): Archivo, graphite; printed prose, lede, step text. Measure 72ch (`max-width: 72ch`), footnotes 90ch.
- **Caption** (400, 12px, 1.5): Archivo, soft graphite; figure/diagram captions, sheet footnote, tally sub-line. The bench caption is 13px.
- **Label** (700, 10–13px, 1.2–1.6, 0.06–0.1em, uppercase): Archivo Narrow, teal; field labels (11px/0.1em), table heads (11px/0.1em), margin `h2` (12px/0.1em), nav and footer (12–12.5px/0.08em), team rows (13px/0.08em, graphite), the half-inning strip label (10px/0.08em), summaries (13px/0.08em), buttons (12–13px/0.1em). Grid column heads are 12px at 0.02em; the box's printed MLB number is 10px/0.02em.
- **Hand** (500, 14–23px, 1–1.25): Caveat, graphite; field values (21px), line-score runs (19px), tally running note (23px), batter names (17px; substitutes 14px), the play (16px, 700), the box's Bend number (15px, 700), H–AB (18px), the half-inning tally (15px), the "now" line (20px), the "proven" marks in the laws table (21px), step numerals (22px, 700, teal). The out circle is 13px/700, rotated −6°.
- **Hand Tally** (700, 44px, 1; 38px below 720px): the single large pencilled Bend number in the keeper's margin.
- **Mono** (400, 12.5px, 1.5): code blocks on a teal tint with a 1px rule; inline `code` is 0.86em of its context.

### Named Rules
**The Keeper's Hand Rule.** Caveat is used only for what a scorekeeper would write by hand during the game: the batting order's names, the play notation, outs, runs, the inning totals, the win number, the running note, "proven", the step numerals. Never for headings, labels, links, prose, or anything the printer set.

**The Condensed Print Rule.** Anything printed on the card as structure (headings, column heads, labels, navigation, buttons, footer) is Archivo Narrow 700, uppercase, letterspaced 0.06–0.1em. Running prose is Archivo 400 at 15px, never condensed.

## Layout

One page, `.book`, max-width 1260px, centred, padded `22px clamp(12px, 3vw, 32px) 56px`. The masthead is a two-column grid (`1fr auto`, gap 8px 24px, aligned to the baseline) between a 3px top rule and a 1px bottom rule; the game fields below are an `auto-fit, minmax(150px, 1fr)` grid separated by 1px teal-rule dividers.

The spread is a two-column grid: the scorecard sheet (`minmax(0, 1fr)`) and the keeper's margin (fixed 360px), gap 14px 28px, with named areas `sheet` / `lead` / `rest` so the margin's lead (actions + tally) sits beside the sheet and the "Now" note sits below it. The sheet is sized to fill its column exactly at the page's full width (88px batter column, nine 72px innings, 50px H–AB); extra innings scroll. Figure 1, the live chart, is printed full width beneath the spread (22px above, 1px teal rule), so the curve gets the page's whole measure; its Pele height is 320px, or 250px when the chart is narrower than 640px. At ≤1160px the spread stacks `lead → sheet → rest` in one column, Figure 1 still last. At ≤720px the masthead collapses to one column, hand sizes step down (fields 19px, line-score 17px, tally 38px), and the batter column and the half-inning strip labels become sticky (`position: sticky; left: 0`) on an opaque stock background with the tint overlaid via `::before` so the grid can scroll horizontally beneath them; the team name rides along in a sticky span.

Spacing rhythm is small and even: 2px (field label→value), 4px (caption gap), 6px (sheet footnote, step text), 8px (masthead, margin top padding), 10–12px (pre padding, section prose, tables, details), 14px (margin gap, spread gap, linescore top), 22px (between steps, above Figure 1), 28px (spread column gap), 44px (between back-of-card sections and before the footer), 56px (page bottom). The scorecard grid itself is `table-layout: fixed`, `width: max-content`, boxes `72×66px`, header row 24px, team rows 26px, half-inning strips 52px, and scrolls horizontally inside a 1px teal frame (`.grid-scroll`). Every horizontally scrolling region sets `scrollbar-color: var(--print) var(--stock)`.

## Elevation & Depth

Flat. There are no elevation shadows anywhere on the page. Depth is conveyed by rule weight (3px page edge, 2px section head, 1px solid row, 1px at 55% interior) and by the 9% teal tint on header rows, team rows, run totals and code blocks. The one `box-shadow` in the build is not elevation: the sticky batter column's `inset -1px 0 0 var(--print-rule)` redraws the grid rule that `position: sticky` would otherwise lose.

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
The whole game on one sheet, kept the way a scorer keeps a book: visitors over home, innings across, no page to flip. Each team's block opens with a team row (logo, name, visitors/home and runs; 1px solid teal rule above), then nine batting-order rows, then a half-inning strip.
- **Batter column**: the slot number printed (11px teal), the batter who batted there pencilled (Caveat 17px), substitutes beneath (14px soft graphite); slot inferred from the plate-appearance count.
- **H–AB** at the row's end: the batter's hits for at-bats pencilled (Caveat 18px), runs batted in printed beneath (10px teal; no RBI on a double play or an error).
- **Half-inning strip** (52px, 1px solid teal rule below): R · H · LOB pencilled, then count boxes with Bend's home-win number pencilled and MLB's and the market median printed as they stood when the half ended (MLB's and Bend's only when the feed has no market prices). The keyband in the sheet footnote prints the order.

Each 72×66px box is one plate appearance, filed under the half-inning it started in:
- **Diamond** (38px, centred at the top, 1px teal base lines): the batter's trip around the bases pencilled from home (2.4px graphite, round caps) to the last base he reached; shaded graphite at 30% when he scored. The trip is followed with Bend's own play codes (`code`: r3 r2 r1 batter, `-` stays, `X` out, `R` scores, `1–3` the base reached), the same moves Bend's `step` makes.
- **Play** pencilled in the diamond (Caveat 700 16px): K, a mirrored K for a called third strike, 1B…HR, BB, HBP, F8, L7, P4, 6-3, 3U, FC, E6, SF9; two-part plays (4-6-3 DP, SAC 1-4) on two lines at 11.5px.
- **Out**: the out this batter made, circled top-left (18px, 1.5px graphite, rotated −6°; filled on the third), even when it came on a later play as a runner. Outs on one play are numbered lead runner first.
- **Runs**: a 5px graphite dot bottom-left for each run scored on the play.
- **Win numbers** bottom-right: Bend's home-win number after the play pencilled (Caveat 700 15px), MLB's printed beside it (Archivo Narrow 10px teal); a decided game is written 100. A play that moved Bend's number 8 points or more has it circled in pencil, the scorer's mark for a turning point. Each venue's price, the batter and the play are in the box's `title` and screen-reader text; the markets per play are in Figure 1.
- "×N" (10px teal, top-right) when the order bats around and two appearances share a box; the box shows the later one.

The latest play carries the red pencil rectangle; when it moves to a new box (`.drawn`) the rectangle draws itself over 900ms with `cubic-bezier(0.16, 1, 0.3, 1)`, disabled under `prefers-reduced-motion`.

### Keeper's Margin
A stacked aside under a 1px teal rule (14px gaps): the actions row; a 12px teal uppercase `h2`; the tally (Caveat 500 23px with the 44px 700 Bend number on its own line, a 12px soft-graphite Archivo sub-line for MLB and Δ, and a market reference line with each venue linked); then the "Now" note. Figure 1 sits outside the margin, full width below the spread.

### Figure 1
The Pele xychart of the home team's win probability after each play. The lines are told apart by mark, not hue (The Three Marks Rule): Bend (graphite, 2px, filled points), MLB (teal, 2px, open points: stock fill, 1.5px teal ring) and each market venue that priced the game (1.5px, butt caps, no points: Kalshi long-dashed `8 3` soft graphite, Polymarket dash-dot `8 3 1.5 3` teal, Polymarket US round dots `0 4` at 2px soft graphite). The marks live twice, in the `#chart` CSS and in `SERIES` / `VENUES`, from which the legend draws; change both together. The y-axis is named for the home team ("Brewers win %"), the x-axis "play, in order". Pele's own legend is hidden because it cannot show the dash patterns; a printed legend sits between the heading and the chart, one item per drawn line: a 30px sample stroked exactly as the line (with a filled or open point where the line has points), the name (Archivo Narrow 700 12px uppercase, graphite) and its source in 12px soft graphite ("65,536 simulated games a play", "official win probability", "market price"). The caption (12px soft graphite, 90ch) says what is plotted and which way favours whom, where each line's numbers come from, the mean gap between Bend and MLB, how a missing price or MLB value is carried, and that markets are a reference.

### Pele diagrams
Themed via `.pele` custom properties: stock background and surface, teal foreground/line/border/muted, 9% tint alt surface, graphite accent and series 1, teal series 2, red critical/error, Archivo Narrow at 700 for titles and headings, mono stack for code, radius 0. Pencilled nodes (what Bend computes or what the proof gate lets through) are stock with a 1.6px graphite stroke. Wrapped in `figure.diagram` (14px top margin) with a 12px soft-graphite caption that says which way to read the diagram and what each mark means.

## Do's and Don'ts

### Do:
- **Do** set every printed structural label in Archivo Narrow 700 uppercase with 0.06–0.1em tracking in teal (`print`).
- **Do** use Caveat only for values a scorekeeper writes during the game, in graphite, at 14px or larger (The Keeper's Hand Rule).
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
