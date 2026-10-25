// The scorebook from the per-play CSV: parsing, and each plate appearance filed in its batter's box.
// Pure: no DOM, so tests/web can run it under node --test.
import { VENUES } from "./series.js";

export const SLOTS = 9;
export const HIT = new Set(["1B", "2B", "3B", "HR"]);
export const SWING = 8;   // points of Bend's home-win number; a play that moves it this far is circled

export function parseCsv(text) {
  const records = [];
  let record = [], field = "", quoted = false;
  const endRecord = () => {
    record.push(field);
    field = "";
    if (record.some(v => v !== "")) records.push(record);
    record = [];
  };
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else quoted = false;
      } else field += c;
    } else if (c === '"' && field === "") quoted = true;
    else if (c === ",") { record.push(field); field = ""; }
    else if (c === "\r" || c === "\n") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      endRecord();
    } else field += c;
  }
  if (field !== "" || record.length) endRecord();
  const head = records.shift() || [];
  return records.map(cells => Object.fromEntries(head.map((h, i) => [h, cells[i]])));
}

export const num = v => (v === "" || v === undefined ? null : Number(v));
export const halfArrow = h => (h === "T" ? "▲" : h === "B" ? "▼" : "");

export const venueCol = v => `${v.key}_home_wp`;
// Venues with at least one price in the feed; none when the columns are absent.
export const venuesIn = rows => VENUES.filter(v => rows.some(r => num(r[venueCol(v)]) !== null));

export function latest(rows, key) {
  for (let i = rows.length - 1; i >= 0; i--) if (num(rows[i][key]) !== null) return num(rows[i][key]);
  return null;
}

// The final row of a finished game carries sims = 0; report the run that produced the curve.
export function lastSim(rows) {
  for (let i = rows.length - 1; i >= 0; i--) if (Number(rows[i].sims) > 0) return rows[i];
  return null;
}

// The market line in a cell: the median of the venues that priced the play.
export function median(xs) {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// Turn the per-play rows into the scorebook: each plate appearance in its batter's box,
// filed under the half-inning it started in (the previous row's state; a row carries the
// state after its play, so the third out already shows the next half), with the batter's
// trip around the bases, plus runs, hits and runners left per half-inning.
export function book(rows) {
  const plays = [];
  const count = { away: 0, home: 0 };
  const runsBy = { away: new Map(), home: new Map() };
  const halves = new Map();   // "side/inning" -> { r, h, lob, bend, mlb, mk } at the end of the half
  const lines = { away: new Map(), home: new Map() };   // slot -> { names, ab, h, rbi }
  let prev = { inning: "1", half: "T", away_runs: "0", home_runs: "0" }, innings = 9, half = null;
  for (const r of rows) {
    const idx = Number(r.at_bat_index);
    if (Number(r.inning) > innings) innings = Number(r.inning);
    if (!(idx >= 0)) { prev = r; continue; }
    const side = prev.half === "T" ? "away" : "home", inning = Number(prev.inning);
    const key = `${side}/${inning}`;
    if (!half || half.key !== key) half = { key, on: [null, null, null], outs: 0 };
    const runs = Math.max(0, Number(r[`${side}_runs`]) - Number(prev[`${side}_runs`]));
    const mkt = VENUES.map(v => [v, num(r[venueCol(v)])]).filter(([, x]) => x !== null);
    const bend = num(r.bend_home_wp), before = num(prev.bend_home_wp);
    // A play the batter never finished (caught stealing, pickoff, steal) takes no slot and no box:
    // he bats again next time; the play is written in the runner's box.
    const pa = !r.code || r.code[3] !== "-";
    const p = { r, idx, side, slot: pa ? (count[side]++ % SLOTS) + 1 : null, inning, half: prev.half, runs,
      play: r.play || "", batter: r.batter || "", reached: 0, outNo: 0, note: "", runner: null,
      bend, mlb: num(r.mlb_home_wp), mkt, mk: median(mkt.map(([, x]) => x)),
      swing: bend !== null && before !== null ? bend - before : null };
    advance(half, p, r.code);
    const tot = halves.get(key) || { r: 0, h: 0, lob: null };
    tot.r += runs;
    if (HIT.has(p.play)) tot.h++;
    if (half.outs >= 3 && tot.lob === null) tot.lob = half.on.filter(Boolean).length;
    Object.assign(tot, { bend: p.bend, mlb: p.mlb, mk: p.mk });
    halves.set(key, tot);
    if (pa) {
      const line = lines[side].get(p.slot) || { names: [], ab: 0, h: 0, rbi: 0 };
      if (p.batter && !line.names.includes(p.batter)) line.names.push(p.batter);
      if (!/^(BB|IBB|HBP|CI)$/.test(p.play) && !/^(SAC|SF)/.test(p.play)) line.ab++;
      if (HIT.has(p.play)) line.h++;
      if (!/DP/.test(p.play) && !/^E/.test(p.play)) line.rbi += runs;   // no RBI on a double play or an error
      lines[side].set(p.slot, line);
    }
    plays.push(p);
    runsBy[side].set(inning, (runsBy[side].get(inning) || 0) + runs);
    prev = r;
  }
  return { plays, innings, runsBy, halves, lines, last: rows[rows.length - 1] || null, priced: venuesIn(rows).length > 0 };
}

// Follow each batter around the bases with Bend's play code (slots r3 r2 r1 batter:
// "-" stays, X out, R scores, 1-3 the base reached), the same moves Bend's step makes.
// Outs on one play are numbered lead runner first.
export function advance(half, p, code) {
  if (!code || code.length !== 4) return;
  const next = [null, null, null];
  const move = (who, c, from) => {
    if (c === "-") { if (from) next[from - 1] = who; return; }   // stays; a batter "-" did not bat
    if (!p.slot && from) { who.note = p.play; p.runner = p.runner || who; }   // CS, PO, SB: the runner's box
    if (c === "X") { who.outNo = ++half.outs; return; }
    if (c === "R") { who.reached = 4; return; }
    who.reached = Math.max(who.reached, Number(c));
    next[Number(c) - 1] = who;
  };
  [3, 2, 1].forEach((from, i) => { if (half.on[from - 1]) move(half.on[from - 1], code[i], from); });
  move(p, code[3], 0);
  half.on = next;
}
