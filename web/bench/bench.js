// The benchmark page (web/bench/index.html): renders one bench.py run (data.json, or data-<year>.json
// with ?run=<year>) as the head-to-head verdicts, scores, calibration, segments, games and method.
import { $, esc, f4, signed, pct, count, ciBracket, ciTo, verdictStamp, legendItem } from "../js/common.js";
import { SERIES, inkLines } from "../js/series.js";

const pval = p => p < 0.001 ? "< 0.001" : p.toFixed(3);
// The sources Bend is compared with, in bench.py's order (data.names): MLB, then each market venue.
const rivals = d => Object.keys(d.names).filter(k => k !== "bend");
const markets = d => rivals(d).filter(k => k !== "mlb");
const IDEAL = { id: "Ideal", stroke: "var(--print-rule)", dash: "6 4", width: 1.5 };
inkLines("#cal", [SERIES.bend, SERIES.mlb, IDEAL]);
const deltaClass = v => v === "clear win" ? "num up" : v === "clear loss" ? "num down" : "num";

function renderHead(d) {
  $("f-when").textContent = d.when;
  $("f-commit").textContent = d.commit;
  $("f-games").textContent = `${count(d.games.scored)} / ${count(d.games.requested)}`;
  $("f-plays").textContent = count(d.scored_plays);
  $("f-sims").innerHTML = `2<sup>${esc(d.depth)}</sup> = ${count(d.sims_per_play)}`;
}

function renderVerdict(d) {
  const items = [], rows = [];
  for (const o of rivals(d)) {
    const p = d.paired[o];
    if (!p) continue;
    const name = esc(d.names[o]);
    items.push(`<li>${verdictStamp(p.verdict)}<span>against ${name}: Bend's Brier lower in ${(100 * p.p_better).toFixed(1)}% of 10,000 resamples of the games.</span></li>`);
    rows.push(`<tr><td>${name}<span class="ph vm">${verdictStamp(p.verdict)}</span></td><td class="vcol">${verdictStamp(p.verdict)}</td>`
      + `<td class="${deltaClass(p.verdict)}">${signed(p.d_brier)} <span class="ci">${ciBracket(p.d_brier_ci)}</span></td>`
      + `<td class="num">${f4(p.bend_brier)}</td><td class="num">${f4(p.other_brier)}</td><td class="num">${count(p.plays)}</td>`
      + `<td class="num">${signed(p.d_logloss)} <span class="ci">${ciBracket(p.d_logloss_ci)}</span></td>`
      + `<td class="num">${pct(p.plays_closer)}</td><td class="num">${count(p.games_better)}–${count(p.games_worse)}, p ${pval(p.sign_p)}</td></tr>`);
  }
  $("verdicts").innerHTML = items.join("");
  $("paired").innerHTML = rows.join("");
  const m = d.paired.mlb;
  if (m) {
    $("result").innerHTML = `<span class="k">Against MLB</span> ${verdictStamp(m.verdict)} <span class="nw">Δ Brier ${signed(m.d_brier)}</span> <span class="nw">(95% CI ${ciTo(m.d_brier_ci)});</span> Bend better in ${count(m.games_better)} of ${count(m.games)} games.`;
    $("result").hidden = false;
  }
}

function renderScores(d) {
  const scored = Object.keys(d.names).filter(s => d.sources[s]).map(s => `${d.names[s]} ${count(d.sources[s].plays)}`).join(", ");
  $("scores-cap").textContent = `Not paired: each row scores one source on every play where it had a number (${scored} plays), so its Brier can differ from Head to head, which scores Bend and each source on the same plays. Base rate: the home side won on ${d.home_win_rate.toFixed(1)}% of scored plays; skill is the improvement in Brier over always forecasting that rate. Lower Brier, log loss and calibration error are better.`;
  $("sources").innerHTML = Object.keys(d.names).filter(s => d.sources[s]).map(s => {
    const x = d.sources[s];
    return `<tr><td>${esc(d.names[s])}</td><td class="num">${count(x.plays)}</td><td class="num">${count(x.games)}</td>`
      + `<td class="num">${f4(x.brier)}</td><td class="num">${f4(x.logloss)}</td>`
      + `<td class="num">${x.bss === null ? "—" : pct(100 * x.bss)}</td><td class="num">${x.ece_pp.toFixed(2)} pp</td>`
      + `<td class="num">${pct(x.accuracy)}</td></tr>`;
  }).join("");
}

const MIN_BIN = 20;
let calData = null, calChart = null;

function calSource(d) {
  const b = d.sources.bend.calibration, m = d.sources.mlb.calibration;
  const keep = b.map((_, k) => k).filter(k => b[k].n >= MIN_BIN && m[k].n >= MIN_BIN);
  const w = Math.max(280, Math.min(520, $("cal").clientWidth));   // near square, so a calibrated source runs at 45°
  const src = `---
config:
  xyChart:
    width: ${w}
    height: ${w}
---
xychart
  accTitle: Calibration
  accDescr: Observed home win rate against forecast bin for Bend and MLB, beside the ideal diagonal.
  x-axis "forecast home win %, bin" [${keep.map(k => `"${b[k].lo + 5}"`).join(",")}]
  y-axis "observed home win %" 0 --> 100
  line "Bend" [${keep.map(k => b[k].observed.toFixed(1)).join(",")}]
  line "MLB" [${keep.map(k => m[k].observed.toFixed(1)).join(",")}]
  line "Ideal" [${keep.map(k => b[k].lo + 5).join(",")}]`;
  return { src, n: keep.length };
}

function drawCal() {
  if (!calData || !window.pele) return;
  const { src, n } = calSource(calData);
  if (!n) { $("cal").textContent = "Too few plays per bin to plot."; return; }
  if (calChart) calChart.update(src); else calChart = pele.mount($("cal"), src, { zoom: false, fontSize: 14 });   // ticks at 0.875 × 14 = 12px
}

function renderCalibration(d) {
  $("cal-legend").innerHTML = legendItem("Bend", `${count(d.sims_per_play)} simulated games a play`, SERIES.bend)
    + legendItem("MLB", "official win probability", SERIES.mlb)
    + legendItem("Ideal", "said = won", IDEAL);
  $("cal-cap").textContent += ` Bins with fewer than ${MIN_BIN} plays from Bend or MLB are left off.`;
  calData = d;
  drawCal();
  $("decomp").innerHTML = Object.keys(d.names).filter(s => d.sources[s]).map(s => {
    const x = d.sources[s];
    return `<tr><td>${esc(d.names[s])}</td><td class="num">${x.rel.toFixed(5)}</td><td class="num">${x.res.toFixed(5)}</td>`
      + `<td class="num">${x.unc.toFixed(5)}</td><td class="num">${x.ece_pp.toFixed(2)}</td></tr>`;
  }).join("");
  const b = d.sources.bend.calibration, m = d.sources.mlb.calibration;
  $("bins").innerHTML = b.map((x, k) => `<tr><td>${x.lo}–${x.hi}%</td>`
    + `<td class="num">${count(x.n)}</td><td class="num">${pct(x.forecast)}</td><td class="num">${pct(x.observed)}</td>`
    + `<td class="num">${count(m[k].n)}</td><td class="num">${pct(m[k].forecast)}</td><td class="num">${pct(m[k].observed)}</td></tr>`).join("");
}

const SEGMENT = { pregame: "Pregame", "1–3": "Innings 1–3", "4–6": "Innings 4–6", "7–9": "Innings 7–9",
                  "10+": "Extra innings", tied: "Tied", "1": "1 run", "2–3": "2–3 runs", "4+": "4 or more runs" };
const GROUP = { inning: "By inning", margin: "By run margin after the play" };

function renderSegments(d) {
  const out = [];
  for (const g of Object.keys(GROUP)) {
    const segs = d.segments.filter(s => s.group === g);
    if (!segs.length) continue;
    out.push(`<tr class="group"><th scope="rowgroup" colspan="6"><span>${GROUP[g]}</span></th></tr>`);
    for (const s of segs) {
      out.push(`<tr><td>${esc(SEGMENT[s.key] || s.key)}<span class="ph vm">${verdictStamp(s.verdict)}</span></td><td class="vcol">${verdictStamp(s.verdict)}</td>`
        + `<td class="${deltaClass(s.verdict)}">${signed(s.d_brier)} <span class="ci">${ciBracket(s.d_brier_ci)}</span></td>`
        + `<td class="num">${f4(s.bend_brier)}</td><td class="num">${f4(s.mlb_brier)}</td><td class="num">${count(s.plays)}</td></tr>`);
    }
  }
  $("segs").innerHTML = out.join("");
}

const monthName = k => new Date(`${k}-01T12:00:00Z`).toLocaleString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });

// Every game: a summary from the run, then one fold per month whose table is built when first opened.
function renderGames(d) {
  $("games-hand").textContent = `${count(d.games.scored)} games`;
  const p = d.paired.mlb, sum = [];
  if (p) sum.push(`<li>Bend's Brier was lower than MLB's in ${count(p.games_better)} of ${count(p.games)} games and higher in ${count(p.games_worse)}. In each game's table, Δ is Bend minus MLB on that game's paired plays; negative means Bend was closer.</li>`);
  const priced = d.per_game.filter(g => typeof g.d_brier === "number");
  if (priced.length) {
    const best = priced.reduce((a, g) => g.d_brier < a.d_brier ? g : a), worst = priced.reduce((a, g) => g.d_brier > a.d_brier ? g : a);
    const game = g => `<span class="nw">${esc(g.away)} @ ${esc(g.home)}</span>, ${esc(g.date)} <span class="nw">(Δ ${signed(g.d_brier)})</span>`;
    sum.push(`<li>Bend furthest ahead of MLB: ${game(best)}. Furthest behind: ${game(worst)}.</li>`);
  }
  const failed = d.games.failed;
  if (failed.length) {
    sum.push(`<li>${count(failed.length)} game${failed.length > 1 ? "s" : ""} failed to replay and ${failed.length > 1 ? "are" : "is"} reported, not replaced: `
      + failed.map(f => `${esc(f.gamePk)} (<code>${esc(f.error)}</code>)`).join("; ") + `.</li>`);
  }
  $("games-sum").innerHTML = sum.join("");

  const unscored = d.per_game.some(g => g.unscored > 0);   // the column only earns its place when a game has unscored rows
  const months = new Map();
  for (const g of d.per_game) {
    const k = String(g.date).slice(0, 7);
    if (!months.has(k)) months.set(k, []);
    months.get(k).push(g);
  }
  const head = `<thead><tr><th scope="col">Game</th><th scope="col">Date</th><th scope="col" class="num">Δ</th><th scope="col" class="num">Bend Brier</th>`
    + `<th scope="col" class="num">MLB Brier</th><th scope="col">Final</th><th scope="col" class="num">Scored</th>`
    + (unscored ? `<th scope="col" class="num">Unscored</th>` : "") + `</tr></thead>`;
  const row = g => {
    const cls = typeof g.d_brier !== "number" ? "num" : g.d_brier < 0 ? "num up" : g.d_brier > 0 ? "num down" : "num";
    return `<tr><td class="nw">${esc(g.away)} @ ${esc(g.home)}</td><td class="nw">${esc(g.date)}</td><td class="${cls}">${signed(g.d_brier)}</td>`
      + `<td class="num">${f4(g.bend_brier)}</td><td class="num">${f4(g.mlb_brier)}</td><td class="nw">${esc(g.final)}</td><td class="num">${count(g.scored)}</td>`
      + (unscored ? `<td class="num">${count(g.unscored)}</td>` : "") + `</tr>`;
  };
  const keys = [...months.keys()].sort();
  $("months").innerHTML = keys.map(k => `<details class="month" data-month="${esc(k)}"><summary>${monthName(k)}`
    + `<span class="n">${count(months.get(k).length)} games</span></summary></details>`).join("");
  for (const el of $("months").querySelectorAll("details")) {
    el.addEventListener("toggle", () => {
      if (!el.open || el.querySelector("table")) return;
      const k = el.dataset.month;
      el.insertAdjacentHTML("beforeend", `<div class="tablewrap"><table class="bench"><caption class="sr">Games in ${monthName(k)}</caption>`
        + `${head}<tbody>${months.get(k).map(row).join("")}</tbody></table></div>`);
      cue(el.querySelector(".tablewrap"));
    });
  }
}

// A table wider than its column says so beneath it, and counts the columns still out of view.
const cues = [];
function cue(wrap) {
  const p = document.createElement("p");
  p.className = "scroll-cue";
  p.setAttribute("aria-hidden", "true");
  wrap.after(p);
  const update = () => {
    const over = wrap.scrollWidth - wrap.clientWidth > 1;
    p.hidden = !over;
    if (!over) return;
    const edge = wrap.getBoundingClientRect().right + 1;
    const n = [...wrap.querySelector("thead tr").cells].filter(c => c.getBoundingClientRect().right > edge).length;
    p.textContent = n ? `Swipe the table for ${n} more column${n > 1 ? "s" : ""}` : "End of the table";
  };
  wrap.addEventListener("scroll", update, { passive: true });
  cues.push(update);
  update();
}

function renderMethod(d) {
  const s = d.sample;
  if (s) {
    const strata = Object.entries(s.strata).map(([m, n]) => `${m}: ${n}`).join(", ");
    const which = s.n >= s.population ? `All ${count(s.population)} Final ${s.season} regular-season games`
      : `${s.n} games drawn with seed ${s.seed} from the ${count(s.population)} Final ${s.season} regular-season games`;
    $("m-draw").textContent = `${which}, ${s.n >= s.population ? "by" : "stratified by"} month (${strata})`
      + (s.excluded.length ? `; ${s.excluded.length} development games excluded.` : ".");
    if (s.season !== 2026) {
      $("m-chosen").textContent = `Every setting above was chosen on 2026 games (tune.py); no ${s.season} game was used, and a ${s.season} game is played against ${s.season - 1}'s league rates and home/away factors. Each game was scored once.`;
    }
  }
  if (!markets(d).some(k => d.sources[k])) $("m-markets").hidden = true;
  $("m-unscored").textContent = `${count(d.unscored_plays)} rows in ${d.games_with_unscored} of ${d.games.scored} games`;
}

function renderRun(d) {
  const s = d.sample, priced = markets(d).filter(k => d.paired[k]).length;
  $("lede-who").textContent = "MLB's official win probability"
    + (priced ? ` and ${["one", "two", "three", "four", "five"][priced - 1] || count(priced)} prediction market${priced > 1 ? "s" : ""}` : "");
  if (s) {
    $("lede-games").textContent = s.n >= s.population ? `Every Final game of the ${s.season} regular season (${count(s.n)})`
      : `${count(s.n)} games drawn at random from the ${s.season} regular season`;
    document.title = `Benchmark ${s.season} · Bend vs MLB`;
  }
  for (const a of $("f-runs").querySelectorAll("a")) {
    if (new URL(a.href).search === location.search) a.setAttribute("aria-current", "page");
  }
}

function render(d) {
  renderHead(d);
  renderRun(d);
  renderVerdict(d);
  renderScores(d);
  renderCalibration(d);
  renderSegments(d);
  renderGames(d);
  renderMethod(d);
  for (const wrap of document.querySelectorAll(".tablewrap")) cue(wrap);
}

// No run to show: say which, point to the runs on file, and drop the sections that would sit empty.
function unavailable(err) {
  const runs = [...$("f-runs").querySelectorAll("a")].map(a => `<a href="${esc(a.getAttribute("href"))}">${esc(a.textContent)}</a> (${esc(a.title)})`);
  $("lede").innerHTML = (err.message === "404" && RUN ? `There is no ${esc(RUN)} benchmark run.` : "The benchmark data did not load.")
    + ` Runs on file: ${runs.join(" and ")}.`;
  for (const id of ["verdict", "scores", "calibration", "segments", "games"]) $(id).hidden = true;
  for (const a of document.querySelectorAll('.mast nav a[href^="#"]')) a.hidden = $(a.hash.slice(1)).hidden;
}

const RUN = new URLSearchParams(location.search).get("run");
const FILE = /^\d{4}$/.test(RUN || "") ? `data-${RUN}.json` : "data.json";
fetch(FILE, { cache: "no-store" })
  .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
  .then(render, unavailable);

let resizeTimer = null;
addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { drawCal(); for (const update of cues) update(); }, 150);
});
// toggle does not bubble: catch it on the way down, so a table in a fold measures once it opens
document.addEventListener("toggle", () => { for (const update of cues) update(); }, true);
