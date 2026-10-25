import { test } from "node:test";
import assert from "node:assert/strict";
import { chartSource } from "../../web/js/chart.js";

const row = (half, inning, bend, mlb, kalshi = "", polymarket = "") => ({
  half, inning: String(inning), bend_home_wp: String(bend), mlb_home_wp: String(mlb),
  kalshi_home_wp: String(kalshi), polymarket_home_wp: String(polymarket),
});
const line = (src, name) => src.match(new RegExp(`line "${name}" \\[([^\\]]*)\\]`))?.[1];

test("plays before MLB's first number are left off; later gaps carry the previous value", () => {
  const { src, n, carried } = chartSource([
    row("T", 1, 60, "", 61),
    row("T", 1, 62, 52, 61),
    row("T", 1, 59, "", 60),
    row("B", 1, 64, 55, 58),
  ], { boxWidth: 1000, home: "Brewers" });
  assert.equal(n, 3);
  assert.equal(carried, 1);
  assert.equal(line(src, "MLB"), "52.00,52.00,55.00");
  assert.equal(line(src, "Bend"), "62.00,59.00,64.00");
});

test("a venue is drawn only when it priced the first plotted play, and its gaps carry", () => {
  const { src, drawn } = chartSource([
    row("T", 1, 62, 52, 61, ""),
    row("T", 1, 59, 50, "", 58),
    row("B", 1, 64, 55, 63, 60),
  ], { boxWidth: 1000, home: "Brewers" });
  assert.deepEqual(drawn.map(d => d.v.key), ["kalshi"]);
  assert.equal(line(src, "Kalshi"), "61.00,61.00,63.00");
  assert.equal(line(src, "Polymarket"), undefined);
});

test("innings are marked at the first play of each half, by the half the play started in", () => {
  // a row carries the state after its play: the third out's row already reads B1
  const rows = [row("T", 1, 50, 50), row("T", 1, 51, 51), row("B", 1, 52, 52), row("B", 1, 53, 53), row("T", 2, 54, 54)];
  const wide = chartSource(rows, { boxWidth: 1200, home: "Brewers" });
  assert.equal(line(wide.src, "innings"), '100 "▲1",100,100,100 "▼1",100');
  // twenty plays in a narrow box: halves two plays apart are too close to letter, so only innings
  const many = Array.from({ length: 20 }, (_, i) => row(Math.floor(i / 2) % 2 ? "B" : "T", Math.floor(i / 4) + 1, 50, 50));
  const narrow = chartSource(many, { boxWidth: 200, home: "Brewers" });
  assert.equal(narrow.halves, false);
  assert.match(line(narrow.src, "innings"), /^100 "1"/);
  assert.doesNotMatch(narrow.src, /▼/);
});
