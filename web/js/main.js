// The scorebook page (web/index.html): polls the published feed (or the bundled replay) every 5 s
// and draws the line score, the scorecard sheet, the keeper's margin, Figure 1 and the back of the card.
import { $, esc, signed, ciTo, verdictSentence, legendItem } from "./common.js";
import { SERIES, VENUES, inkLines } from "./series.js";
import { SLOTS, SWING, num, halfArrow, venueCol, venuesIn, latest, lastSim, book, parseCsv } from "./scorebook.js";
import { chartSource } from "./chart.js";
import { DIAGRAMS } from "./diagrams.js";

// World Series Game 3, published live by live.py; ?pk=849805 opens Game 1's bundled replay.
const pk = new URLSearchParams(location.search).get("pk") || "849804";
let meta = { away: "AWAY", home: "HOME" };
let metaLoaded = false;
let lastRows = [];
let lastFetchMs = null;
let feedMissing = false;   // every source for this gamePk answered 404
let source = "live";
let lastNowKey = null;
let chart = null;

$("f-game").textContent = `gamePk ${pk}`;
$("csvlink").href = `/runs/${pk}.csv`;
$("metalink").href = `/runs/${pk}-meta.json`;
inkLines("#chart", [SERIES.bend, SERIES.mlb, ...VENUES]);

const fmt = v => (v === null ? "–" : v.toFixed(1) + "%");
// A win number written in a box: one decimal, except a decided game, written 100 (or 0).
const wp = v => (v === null ? "–" : v >= 99.95 ? "100" : v.toFixed(1));
const fmtDelta = v => (v === null ? "–" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(1) + " pp");
const teamName = side => meta[`${side}_name`] || meta[side];
const venueUrl = v => (Array.isArray(meta.markets) ? meta.markets.find(m => m && m.key === v.key && /^https:\/\//.test(m.url || "")) : null)?.url || null;

// The box's diamond: printed base lines, the batter's path penciled from home, shaded if he scored.
const CORNERS = [[22, 42], [42, 22], [22, 2], [2, 22], [22, 42]];   // home, 1st, 2nd, 3rd, home
function diamondSvg(reached) {
  const path = reached ? "M" + CORNERS.slice(0, reached + 1).map(c => c.join(" ")).join(" L") : "";
  return `<svg class="dia" viewBox="0 0 44 44" aria-hidden="true">`
    + (reached === 4 ? `<path class="run" d="M22 42 L42 22 L22 2 L2 22 Z"/>` : "")
    + `<path class="line" d="M22 42 L42 22 L22 2 L2 22 Z"/>`
    + (path ? `<path class="path" d="${path}"/>` : "")
    + `</svg>`;
}

const REACHED = ["", "reached first", "reached second", "reached third", "scored"];
// A two-part play (4-6-3 DP, SAC 1-4) is written on two lines inside the diamond.
const playHtml = play => {
  const [first, ...rest] = play.split(" ");
  const word = w => w === "Kc" ? `<span class="kc">K</span>` : esc(w);
  return rest.length ? `${word(first)}<br>${esc(rest.join(" "))}` : word(first);
};
const playClass = play => play.includes(" ") ? " two" : play.length > 4 ? " long" : "";
const playWords = play => play === "Kc" ? "K looking" : play;

function basesText(b) {
  const names = ["1st", "2nd", "3rd"].filter((_, i) => b[i] !== "-");
  return names.length ? "runners on " + names.join(" and ") : "bases empty";
}

function renderLinescore(bk) {
  const head = $("ls-head");
  head.replaceChildren(head.firstElementChild);
  for (let i = 1; i <= bk.innings; i++) {
    const th = document.createElement("th"); th.scope = "col"; th.textContent = i; head.append(th);
  }
  const r = document.createElement("th"); r.scope = "col"; r.textContent = "R"; head.append(r);
  const last = bk.last || {};
  for (const side of ["away", "home"]) {
    const tr = $(`ls-${side}`);
    tr.replaceChildren(tr.firstElementChild);
    const half = side === "away" ? "T" : "B";
    for (let i = 1; i <= bk.innings; i++) {
      const td = document.createElement("td");
      const v = bk.runsBy[side].get(i);
      const isLive = last.half === half && Number(last.inning) === i;
      td.textContent = v === undefined ? (isLive ? "0" : "") : v;
      if (isLive) td.className = "live";
      tr.append(td);
    }
    const tot = document.createElement("td");
    tot.className = "r";
    tot.textContent = last[`${side}_runs`] ?? 0;
    tr.append(tot);
  }
}

function renderSheet(bk) {
  const head = $("grid-head");
  head.replaceChildren(head.firstElementChild);
  for (let i = 1; i <= bk.innings; i++) {
    const th = document.createElement("th"); th.scope = "col"; th.textContent = i; head.append(th);
  }
  head.insertAdjacentHTML("beforeend", `<th scope="col" class="tot">H–AB</th>`);
  const cells = new Map();   // "side/slot/inning" -> plays
  for (const p of bk.plays) {
    if (!p.slot) continue;   // no plate appearance: written in the runner's box instead
    const key = `${p.side}/${p.slot}/${p.inning}`;
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(p);
  }
  // The red pencil marks the newest play's box, or the runner's when the play had no batter.
  const newest = bk.plays[bk.plays.length - 1];
  const nowPlay = newest && (newest.slot ? newest : newest.runner);
  const last = bk.last || {};
  const body = $("grid-body");
  body.replaceChildren();
  for (const side of ["away", "home"]) {
    // The team's name across the sheet, then its nine slots, then the half-inning strip.
    const team = document.createElement("tr"); team.className = "team";
    const logo = meta[`${side}_logo`] ? `<img src="${esc(meta[`${side}_logo`])}" alt="">` : "";
    team.innerHTML = `<th scope="rowgroup" colspan="${bk.innings + 2}"><span>${logo}${esc(teamName(side))}`
      + `<small>${side === "away" ? "visitors" : "home"} · ${last[`${side}_runs`] ?? 0} R</small></span></th>`;
    body.append(team);
    for (let s = 1; s <= SLOTS; s++) {
      const line = bk.lines[side].get(s) || { names: [], ab: 0, h: 0, rbi: 0 };
      const tr = document.createElement("tr");
      const th = document.createElement("th"); th.scope = "row"; th.className = "slot";
      th.innerHTML = `<span class="no">${s}</span><span class="who">${esc(line.names[0] || "")}</span>`
        + line.names.slice(1).map(n => `<span class="sub">${esc(n)}</span>`).join("");
      tr.append(th);
      for (let i = 1; i <= bk.innings; i++) {
        const td = document.createElement("td");
        const ps = cells.get(`${side}/${s}/${i}`);
        if (ps) td.append(boxCell(ps, s, nowPlay));
        tr.append(td);
      }
      tr.insertAdjacentHTML("beforeend", line.names.length
        ? `<td class="tot">${line.h}–${line.ab}<small>${line.rbi ? `${line.rbi} RBI` : ""}</small></td>` : `<td class="tot"></td>`);
      body.append(tr);
    }
    // After the half: one printed row per number, each as it stood when the half ended.
    const strip = [
      ["tallies", "After the half<br>R · H · LOB", (h, i) => `<td><span class="tally" aria-hidden="true">${h.r} · ${h.h} · ${h.lob ?? "–"}</span>`
        + `<span class="sr">${side === "away" ? "Top" : "Bottom"} ${i}: ${h.r} runs, ${h.h} hits, ${h.lob ?? "no"} left on base</span></td>`],
      ["bend", "Bend", h => `<td class="b">${wp(h.bend)}</td>`],
      ["mlb", "MLB", h => `<td>${wp(h.mlb)}</td>`],
    ];
    if (bk.priced) strip.push(["mkt", "Mkt median", h => `<td>${wp(h.mk)}</td>`]);
    strip.forEach(([name, label, cell], j) => {
      const tr = document.createElement("tr");
      tr.className = `half ${name}` + (j === strip.length - 1 ? " end" : "");
      let html = `<th scope="row">${label}</th>`;
      for (let i = 1; i <= bk.innings; i++) {
        const h = bk.halves.get(`${side}/${i}`);
        html += h ? cell(h, i) : "<td></td>";
      }
      tr.innerHTML = html + `<td class="tot"></td>`;
      body.append(tr);
    });
  }
}

// One plate appearance as a scorer keeps it; when the order bats around, the later one, marked ×N.
function boxCell(ps, s, nowPlay) {
  const p = ps[ps.length - 1];
  const isNow = nowPlay && p === nowPlay;
  const big = p.swing !== null && Math.abs(p.swing) >= SWING;
  const cell = document.createElement("div");
  cell.className = "cell" + (isNow ? " now" : "");
  cell.title = [p.batter, playWords(p.play), ...[["Bend", p.bend], ["MLB", p.mlb], ...p.mkt.map(([v, x]) => [v.name, x])]
    .map(([k, x]) => `${k} ${fmt(x)}`)].filter(Boolean).join(" · ");
  const said = [p.batter || `slot ${s}`, playWords(p.play), REACHED[p.reached], p.note ? `then ${p.note}` : "",
    p.outNo ? `out ${p.outNo}` : "", p.runs ? `${p.runs} run${p.runs > 1 ? "s" : ""} scored` : ""].filter(Boolean).join(", ");
  cell.innerHTML = diamondSvg(p.reached)
    + (p.play ? `<span class="play${playClass(p.play)}">${playHtml(p.play)}</span>` : "")
    + (p.outNo ? `<span class="out${p.outNo === 3 ? " three" : ""}">${p.outNo}</span>` : "")
    + (p.runs ? `<span class="dots">${"<i></i>".repeat(Math.min(p.runs, 4))}</span>` : "")
    + (ps.length > 1 ? `<span class="more">×${ps.length}</span>` : "")
    + (p.note ? `<span class="note">${esc(p.note)}</span>` : "")
    + `<span class="nums"><b${big ? ' class="swing"' : ""}>${wp(p.bend)}</b><span>${wp(p.mlb)}</span></span>`
    + `<span class="sr">${halfArrow(p.half)}${p.inning}: ${esc(said)}. Bend ${fmt(p.bend)}${big ? `, a swing of ${Math.abs(p.swing).toFixed(1)} points` : ""}, MLB ${fmt(p.mlb)}${p.mkt.length ? `, market median ${fmt(p.mk)} (${p.mkt.map(([v, x]) => `${v.name} ${fmt(x)}`).join(", ")})` : ""}.</span>`
    + (isNow ? `<svg class="pen" aria-hidden="true"><rect x="1" y="1" width="calc(100% - 2px)" height="calc(100% - 2px)" pathLength="1"/></svg>` : "");
  return cell;
}

function renderChart(rows) {
  const { src, carried, n, drawn, halves } = chartSource(rows, { boxWidth: $("chart").clientWidth, home: teamName("home") });
  if (!n) { $("chart").textContent = "No plays yet."; $("legend").replaceChildren(); chart = null; return; }
  if (chart) chart.update(src); else chart = pele.mount($("chart"), src, { zoom: false, fontSize: 14 });
  const sim = lastSim(rows);
  $("legend").innerHTML = legendItem("Bend", sim ? `${Number(sim.sims).toLocaleString()} simulated games a play` : "simulated games",
      SERIES.bend)
    + legendItem("MLB", "official win probability", SERIES.mlb)
    + drawn.map(d => legendItem(esc(d.v.name), d.v.note, d.v)).join("");
  const home = teamName("home"), away = teamName("away");
  const gaps = rows.map(r => num(r.delta)).filter(x => x !== null).map(Math.abs);
  $("chart-cap").textContent = `How likely the ${home} were to win, from 0 to 100%, after each of the ${n} completed plays, `
    + `left to right from the first; up favors the ${home}, down the ${away}, and a rule marks 50%. `
    + `Innings are marked along the top${halves ? ", ▲ for the top half and ▼ for the bottom" : ""}. Bend's line is the share of its simulated games `
    + `the ${home} won from the position after the play; MLB's is its official win probability for the same moment`
    + (gaps.length ? `, on average ${(gaps.reduce((a, b) => a + b, 0) / gaps.length).toFixed(2)} pp from Bend's.` : ".")
    + (drawn.length ? ` Each market line is that venue's price, read within a minute after the play; a play with no price carries `
      + `the last one. Markets are shown as a reference, not as ground truth.` : "")
    + (carried ? ` ${carried} play${carried > 1 ? "s" : ""} without an MLB value carried the previous one.` : "");
}

// A successful CSV response is a heartbeat from the publisher, not only a new play.
function updateFreshness() {
  const node = $("f-feed");
  if (lastFetchMs === null) {
    node.textContent = feedMissing ? `nothing published for ${pk}` : "waiting";
    node.className = feedMissing ? "stale" : "";
    return;
  }
  const seconds = Math.max(0, Math.floor((Date.now() - lastFetchMs) / 1000));
  const label = source === "live" ? "live" : "replay";
  node.textContent = `${label} · ${seconds}s ago`;
  node.className = seconds < 30 ? "" : seconds < 90 ? "stale" : "dead";
}
setInterval(updateFreshness, 1000);

function updateTeams() {
  for (const side of ["away", "home"]) {
    $(`${side}-name`).textContent = meta[side];
    const url = meta[`${side}_logo`];
    const slot = $(`${side}-logo`);
    slot.replaceChildren();
    if (url) {
      const image = new Image();
      image.src = url; image.alt = `${teamName(side)} logo`; image.width = 20; image.height = 20;
      slot.append(image);
    }
  }
  document.title = `${teamName("away")} @ ${teamName("home")} — Bend vs MLB`;
}

async function loadMeta() {
  for (const base of ["/runs/", "/demo/"]) {
    try {
      const res = await fetch(base + pk + "-meta.json", { cache: "no-store" });
      if (!res.ok) continue;
      meta = await res.json();
      metaLoaded = true;
      updateTeams();
      return;
    } catch (e) {}
  }
}

async function loadRows() {
  try {
    source = "live";
    const res = await fetch(`/runs/${pk}.csv`, { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    return parseCsv(await res.text());
  } catch (e) {}
  source = "replay";
  const res = await fetch(`/demo/${pk}.csv`, { cache: "no-store" });
  if (!res.ok) throw new Error(`no feed for ${pk}`);
  return parseCsv(await res.text());
}

// One render per poll: masthead, line score, the open page, the margin, the chart.
function render(rows) {
  const bk = book(rows);
  const last = bk.last || {};
  const halfKey = `${last.inning}/${last.half}`;

  const sim = lastSim(rows);
  $("f-date").textContent = last.wall_time ? last.wall_time.slice(0, 10) : "–";
  $("f-sims").textContent = sim ? `${Number(sim.sims).toLocaleString()} · ${sim.mode}` : "–";

  renderLinescore(bk);
  renderSheet(bk);

  const bend = latest(rows, "bend_home_wp");
  const mlb = latest(rows, "mlb_home_wp");
  const delta = latest(rows, "delta") ?? (bend !== null && mlb !== null ? bend - mlb : null);
  $("bend-val").textContent = fmt(bend);
  $("bend-hint").textContent = bend === null ? "waiting for the feed"
    : sim ? `${Number(sim.sims).toLocaleString()} games in ${sim.seconds} s on ${sim.mode}` : "";
  $("mlb-val").textContent = fmt(mlb);
  const d = $("delta-val");
  d.textContent = fmtDelta(delta);
  d.className = "delta " + (delta === null ? "" : delta > 0 ? "up" : delta < 0 ? "down" : "");
  // Market reference prices from the latest play that has any (a play's price is read a minute
  // after it ends), so a venue whose book has gone blank shows "–" rather than an old price.
  const mkLine = $("mkt-line");
  const quoted = venuesIn(rows);
  const mkRow = [...rows].reverse().find(r => quoted.some(v => num(r[venueCol(v)]) !== null)) || {};
  mkLine.replaceChildren();
  mkLine.hidden = !quoted.length;
  quoted.forEach((v, i) => {
    const url = venueUrl(v);
    const label = url ? Object.assign(document.createElement("a"), { href: url, target: "_blank", rel: "noopener", textContent: v.name }) : v.name;
    mkLine.append(i ? " · " : "Market reference: ", label, ` ${fmt(num(mkRow[venueCol(v)]))}`);
  });

  const inningLabel = last.half === "T" ? "Top" : last.half === "B" ? "Bottom" : "";
  const nowKey = `${last.at_bat_index}/${halfKey}`;
  const finished = rows.length > 1 && Number(last.sims) === 0;
  $("now-line").textContent = !last.inning ? "–"
    : finished ? `Final after ${last.inning}. ${meta.away} ${last.away_runs || 0}, ${meta.home} ${last.home_runs || 0}.`
    : `${inningLabel} ${last.inning}, ${basesText(last.bases || "---")}, ${last.outs || 0} out. ${meta.away} ${last.away_runs || 0}, ${meta.home} ${last.home_runs || 0}.`;
  $("now-check").textContent = last.state_check
    ? `Scorebook check after this play: ${last.state_check}. ${source === "live" ? "Published feed" : "Bundled replay"}, polled every 5 s.`
    : "";

  // The red pencil draws once per new play, not on every poll.
  const nowCell = document.querySelector(".cell.now");
  if (nowCell && nowKey !== lastNowKey) {
    nowCell.classList.add("drawn");
    const td = nowCell.parentElement, box = td.closest(".grid-scroll");
    const right = td.offsetLeft + td.offsetWidth;
    if (right > box.scrollLeft + box.clientWidth || td.offsetLeft < box.scrollLeft) {
      box.scrollLeft = Math.max(0, right - box.clientWidth + 8);
    }
  }
  lastNowKey = nowKey;

  renderChart(rows);
}

async function tick() {
  if (!metaLoaded) await loadMeta();
  try {
    const rows = await loadRows();
    lastRows = rows;
    lastFetchMs = Date.now();
    render(rows);
  } catch (e) {
    $("now-check").textContent = "Feed unavailable.";
    feedMissing = !lastRows.length;
  } finally {
    updateFreshness();
    setTimeout(tick, 5000);
  }
}

// On a narrow screen a diagram keeps its smallest label at 10px and scrolls inside its figure:
// the least width at which the SVG, scaled to fit, still sets that label at 10px. Pele lays a
// diagram out again when its box resizes, so the width is measured again on every new drawing;
// a top-to-bottom diagram opens scrolled to its middle, where its root is.
function keepLegible(node) {
  const svg = node.querySelector(":scope > svg");
  const sizes = svg ? [...svg.querySelectorAll("text")].map(t => parseFloat(getComputedStyle(t).fontSize)).filter(x => x > 0) : [];
  if (!sizes.length) return;
  node.style.setProperty("--legible-w", `${Math.ceil(svg.viewBox.baseVal.width * 10 / Math.min(...sizes))}px`);
  if (/^flowchart TB/.test(DIAGRAMS[node.dataset.diagram])) node.scrollLeft = (node.scrollWidth - node.clientWidth) / 2;
}
for (const node of document.querySelectorAll(".pele-src")) {
  pele.mount(node, DIAGRAMS[node.dataset.diagram], { zoom: false, fontSize: 12.5 });
  keepLegible(node);
  new MutationObserver(() => keepLegible(node)).observe(node, { childList: true });
}

// The season benchmark, from the benchmark page's data: standings in the keeper's margin and the
// comparison table on the back of the card.
function loadSeason() {
  const load = file => fetch(file, { cache: "no-store" }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
  const runs = [
    { file: "/bench/data-2025.json", href: "/bench/?run=2025", year: "2025", label: () => "2025, every game",
      intro: d => `Every Final game of the 2025 regular season, which no setting was chosen on: ${d.games.scored.toLocaleString()} of ${d.games.requested.toLocaleString()} replayed and scored.` },
    { file: "/bench/data.json", href: "/bench/", year: "2026", label: d => `2026, ${d.games.requested} at random`,
      intro: d => `Of ${d.games.requested} games drawn at random from the 2026 regular season, ${d.games.scored} replayed and scored.` },
  ];
  Promise.allSettled(runs.map(r => load(r.file))).then(results => {
    const got = runs.map((r, i) => ({ ...r, d: results[i].value })).filter(r => r.d?.paired?.mlb);
    if (!got.length) return;   // the printed fallback points to the benchmark page
    const season = got.find(r => r.year === "2025");
    if (season) $("season-hand").innerHTML = `${season.d.games.scored.toLocaleString()} games · ${season.d.scored_plays.toLocaleString()} plays · 2<sup>${esc(season.d.depth)}</sup> sims a play`;
    $("season-intro").textContent = got.map(r => r.intro(r.d)).join(" ");
    $("stand-body").innerHTML = got.map(({ d, href, year }) => {
      const m = d.paired.mlb;
      return `<tr><th scope="row"><a href="${href}">${year}</a><small>${d.games.scored.toLocaleString()} games</small></th>`
        + `<td>${m.bend_brier.toFixed(4)}</td><td>${m.other_brier.toFixed(4)}</td><td>${signed(m.d_brier)}<small>${ciTo(m.d_brier_ci)}</small></td></tr>`
        + `<tr class="verdict${m.verdict === "clear win" ? " win" : ""}"><td colspan="4">${esc(verdictSentence(m.verdict))}.</td></tr>`;
    }).join("");
    $("season-body").innerHTML = got.map(({ d, href, label }) => {
      const m = d.paired.mlb;
      return `<tr><td><a href="${href}">${esc(label(d))}</a></td><td class="num">${m.plays.toLocaleString()}</td>`
        + `<td class="num">${m.bend_brier.toFixed(4)}</td><td class="num">${m.other_brier.toFixed(4)}</td>`
        + `<td class="num">${signed(m.d_brier)} (${ciTo(m.d_brier_ci)})</td><td class="num">${m.plays_closer.toFixed(1)}%</td>`
        + `<td class="num">${m.games_better.toLocaleString()} of ${m.games.toLocaleString()}</td><td>${esc(verdictSentence(m.verdict))}</td></tr>`;
    }).join("");
    $("season-wrap").hidden = false;
  });
}
loadSeason();

render([]);
tick();
