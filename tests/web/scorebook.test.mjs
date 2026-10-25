import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseCsv, book, median } from "../../web/js/scorebook.js";

// A feed row carries the state after its play.
const row = (idx, inning, half, code, play, batter, extra = {}) => ({
  at_bat_index: String(idx), inning: String(inning), half, code, play, batter,
  away_runs: "0", home_runs: "0", bend_home_wp: "50", mlb_home_wp: "50", ...extra,
});
const pregame = row(-1, 1, "T", "", "", "");

test("parseCsv keeps quoted commas and quotes, CRLF endings, and skips blank lines", () => {
  const rows = parseCsv('play,batter\r\n"4-6-3, DP","O""Neil"\r\n\r\nK,Díaz');
  assert.deepEqual(rows, [{ play: "4-6-3, DP", batter: 'O"Neil' }, { play: "K", batter: "Díaz" }]);
});

test("the bundled replay's line score adds up to the final score", () => {
  const rows = parseCsv(readFileSync(new URL("../../web/demo/849805.csv", import.meta.url), "utf8"));
  const bk = book(rows);
  const total = side => [...bk.runsBy[side].values()].reduce((a, b) => a + b, 0);
  assert.equal(total("away"), Number(bk.last.away_runs));
  assert.equal(total("home"), Number(bk.last.home_runs));
  for (const side of ["away", "home"]) {
    const hits = [...bk.lines[side].values()].reduce((a, l) => a + l.h, 0);
    const halfHits = [...bk.halves].filter(([k]) => k.startsWith(side)).reduce((a, [, h]) => a + h.h, 0);
    assert.equal(hits, halfHits, `${side}: batters' hits match the half-inning tallies`);
  }
});

test("a play the batter did not finish takes no slot and is written in the runner's box", () => {
  const bk = book([
    pregame,
    row(0, 1, "T", "---X", "K", "Arozarena"),
    row(1, 1, "T", "---1", "1B", "Diaz"),
    row(2, 1, "T", "--X-", "CS", "Lowe"),
    row(3, 1, "B", "---X", "6-3", "Lowe"),   // the third out: the row already shows the bottom half
  ]);
  const [k, single, cs, out] = bk.plays;
  assert.deepEqual(bk.plays.map(p => p.slot), [1, 2, null, 3]);
  assert.equal(cs.runner, single);
  assert.equal(single.note, "CS");
  assert.equal(single.outNo, 2);
  assert.deepEqual([k.outNo, out.outNo], [1, 3]);
  assert.deepEqual([out.side, out.inning, out.half], ["away", 1, "T"], "filed under the half it started in");
  assert.equal(bk.halves.get("away/1").lob, 0);
});

test("outs on one play are numbered lead runner first, and a double play earns no RBI", () => {
  const bk = book([
    pregame,
    row(0, 1, "T", "---3", "3B", "Arozarena"),
    row(1, 1, "T", "---1", "BB", "Diaz"),
    row(2, 1, "T", "R-XX", "6-4-3 DP", "Lowe", { away_runs: "1" }),
  ]);
  const [triple, walk, dp] = bk.plays;
  assert.equal(triple.reached, 4);
  assert.deepEqual([walk.outNo, dp.outNo], [1, 2]);
  assert.equal(dp.runs, 1);
  assert.deepEqual(bk.lines.away.get(3), { names: ["Lowe"], ab: 1, h: 0, rbi: 0 });
  assert.deepEqual(bk.lines.away.get(2), { names: ["Diaz"], ab: 0, h: 0, rbi: 0 }, "a walk is no at-bat");
  assert.equal(bk.halves.get("away/1").r, 1);
});

test("the market median of an even count is the mean of the middle two", () => {
  assert.equal(median([]), null);
  assert.equal(median([62, 60, 70]), 62);
  assert.equal(median([70, 60, 64, 62]), 63);
});
