// Figure 1's Mermaid xychart source from the per-play rows. Pure: no DOM.
import { esc } from "./common.js";
import { num, halfArrow, venueCol, venuesIn } from "./scorebook.js";

// boxWidth is the chart's container width in px; home is the home team's display name.
export function chartSource(rows, { boxWidth, home }) {
  const venues = venuesIn(rows);
  const xs = [], bend = [], mlb = [], starts = [];
  const mk = venues.map(() => []), lastMk = venues.map(() => null);
  let carried = 0, lastMlb = null, prev = null;
  for (const r of rows) {
    // a row carries the state after its play, so the play belongs to the previous row's half-inning
    const before = prev || r;
    prev = r;
    const b = num(r.bend_home_wp);
    if (b === null) continue;
    venues.forEach((v, i) => { const x = num(r[venueCol(v)]); if (x !== null) lastMk[i] = x; });
    let m = num(r.mlb_home_wp);
    if (m === null) {
      if (lastMlb === null) continue;   // no official number yet: nothing to compare
      m = lastMlb; carried++;
    }
    lastMlb = m;
    const last = starts[starts.length - 1];
    if (!last || last.half !== before.half || last.inning !== before.inning) starts.push({ at: xs.length, half: before.half, inning: before.inning });
    xs.push(`"${xs.length + 1}"`);
    bend.push(b.toFixed(2));
    mlb.push(m.toFixed(2));
    venues.forEach((_, i) => mk[i].push(lastMk[i]));
  }
  // A Mermaid line cannot start mid-chart, so a venue is drawn only when it has a price at the
  // first plotted play (the pregame row reads first pitch, so a listed venue normally does);
  // later gaps carry the previous price, as MLB's line does.
  const drawn = venues.map((v, i) => ({ v, data: mk[i] }))
    .filter(d => d.data[0] !== null && d.data[0] !== undefined)
    .map(d => ({ v: d.v, data: d.data.map(x => x.toFixed(2)) }));
  const names = ["Bend", "MLB official", ...drawn.map(d => d.v.name)];
  // Innings printed along the top, each mark at the first play of its half-inning (▲ top, ▼ bottom);
  // where the halves are too close to letter, only each inning's number, at its first play.
  const width = Math.max(280, boxWidth);
  const perPlay = (width - 80) / Math.max(xs.length, 1);
  const halves = starts.every((s, k) => !k || (s.at - starts[k - 1].at) * perPlay >= 24);
  const marks = xs.map(() => "");
  let markedAt = -Infinity;
  for (const s of starts) {
    if (!halves && s.half !== "T") continue;
    if ((s.at - markedAt) * perPlay < 16) continue;   // never print two marks over each other
    marks[s.at] = halves ? `${halfArrow(s.half)}${s.inning}` : `${s.inning}`;
    markedAt = s.at;
  }
  const src = `---
config:
  xyChart:
    width: ${width}
    height: ${boxWidth < 640 ? 250 : 320}
    showLegend: false
---
xychart
  accTitle: ${esc(home)} win probability after each completed play
  accDescr: ${names.length === 2 ? "Two" : names.length === 3 ? "Three" : names.length === 4 ? "Four" : "Five"} lines over ${xs.length} plays: ${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}. A rule marks 50%; innings are marked along the top.
  x-axis "play, in order (innings along the top)" [${xs.join(",")}]
  y-axis "${esc(home)} win %" 0 --> 100
  line "50%" [${xs.map(() => 50).join(",")}]
  line "innings" [${marks.map(t => (t ? `100 "${t}"` : "100")).join(",")}]
  line "Bend" [${bend.join(",")}]
  line "MLB" [${mlb.join(",")}]` + drawn.map(d => `
  line "${d.v.name}" [${d.data.join(",")}]`).join("");
  return { src, carried, n: xs.length, drawn, halves };
}
