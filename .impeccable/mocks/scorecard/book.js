// Shared by the three scorecard mockups: the bundled World Series Game 1 replay (web/demo/849805.csv)
// turned into plate appearances, half-innings and batting lines, the way the page does it.
window.Book = (() => {
  const HIT = new Set(["1B", "2B", "3B", "HR"]);
  const VENUES = ["kalshi", "polymarket", "polymarket_us"];
  const num = v => (v === "" || v == null ? null : Number(v));
  const median = xs => {
    if (!xs.length) return null;
    const s = [...xs].sort((a, b) => a - b), m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  // Bend's play code, slots r3 r2 r1 batter: "-" stays, X out, R scores, 1-3 the base reached.
  function advance(half, p) {
    const code = p.code;
    if (!code || code.length !== 4) return;
    const next = [null, null, null];
    const move = (who, c, from) => {
      if (c === "-") { if (from) next[from - 1] = who; return; }
      if (c === "X") { who.outNo = ++half.outs; return; }
      if (c === "R") { who.reached = 4; return; }
      who.reached = Math.max(who.reached, Number(c));
      next[Number(c) - 1] = who;
    };
    [3, 2, 1].forEach((from, i) => { if (half.on[from - 1]) move(half.on[from - 1], code[i], from); });
    move(p, code[3], 0);
    half.on = next;
  }

  function build(rows) {
    const plays = [], halves = [], count = { away: 0, home: 0 };
    let prev = rows[0], half = null;
    for (const r of rows.slice(1)) {   // rows[0] is the pregame row
      const side = prev.half === "T" ? "away" : "home", inning = Number(prev.inning);
      const key = `${side}/${inning}`;
      if (!half || half.key !== key) {
        half = { key, side, inning, on: [null, null, null], outs: 0, plays: [], r: 0, h: 0, lob: null };
        halves.push(half);
      }
      const runs = Math.max(0, Number(r[`${side}_runs`]) - Number(prev[`${side}_runs`]));
      const bend = num(r.bend_home_wp), before = num(prev.bend_home_wp);
      const mkt = VENUES.map(v => num(r[`${v}_home_wp`])).filter(x => x !== null);
      const p = {
        idx: Number(r.at_bat_index), side, inning, half, slot: (count[side]++ % 9) + 1,
        batter: r.batter, play: r.play, code: r.code, reached: 0, outNo: 0, runs,
        bend, mlb: num(r.mlb_home_wp), mk: median(mkt), mkt,
        // Bend's swing for the batting team: what this plate appearance did to their chances.
        swing: bend !== null && before !== null ? (side === "home" ? bend - before : before - bend) : null,
        basesAfter: r.bases, outsAfter: Number(r.outs), pa: r.code && r.code[3] !== "-",
      };
      advance(half, p);
      half.plays.push(p);
      half.r += runs;
      if (HIT.has(p.play)) half.h++;
      if (half.outs >= 3 && half.lob === null) half.lob = half.on.filter(Boolean).length;
      plays.push(p);
      prev = r;
    }
    for (const h of halves) Object.assign(h, (({ bend, mlb, mk }) => ({ bend, mlb, mk }))(h.plays[h.plays.length - 1]));

    // Batting lines per slot: AB R H RBI BB K and Bend's swing, the way a box score adds them up.
    const lines = { away: new Map(), home: new Map() };
    for (const p of plays) {
      const line = lines[p.side].get(p.slot) || { names: [], pa: 0, ab: 0, r: 0, h: 0, rbi: 0, bb: 0, k: 0, swing: 0 };
      if (p.batter && !line.names.includes(p.batter)) line.names.push(p.batter);
      if (p.pa) {
        line.pa++;
        if (!/^(BB|IBB|HBP|CI)$/.test(p.play) && !/^(SAC|SF)/.test(p.play)) line.ab++;
        if (HIT.has(p.play)) line.h++;
        if (/^(BB|IBB)$/.test(p.play)) line.bb++;
        if (/^Kc?( DP)?$/.test(p.play)) line.k++;
        if (!/DP/.test(p.play) && !/^E/.test(p.play)) line.rbi += p.runs;
        line.swing += p.swing ?? 0;
      }
      lines[p.side].set(p.slot, line);
    }
    for (const p of plays) if (p.reached === 4) lines[p.side].get(p.slot).r++;
    return { rows, plays, halves, lines, final: rows[rows.length - 1] };
  }

  async function load(path = "/web/demo/849805.csv") {
    const text = await (await fetch(path)).text();
    const [head, ...body] = text.trim().split("\n");
    const cols = head.split(",");
    return build(body.map(l => Object.fromEntries(l.split(",").map((v, i) => [cols[i], v]))));
  }

  // The box's diamond: printed base lines, the batter's path pencilled from home, shaded if he scored.
  const CORNERS = [[22, 42], [42, 22], [22, 2], [2, 22], [22, 42]];
  function diamond(reached, cls = "dia") {
    const path = reached ? "M" + CORNERS.slice(0, reached + 1).map(c => c.join(" ")).join(" L") : "";
    return `<svg class="${cls}" viewBox="0 0 44 44" aria-hidden="true">`
      + (reached === 4 ? `<path class="run" d="M22 42 L42 22 L22 2 L2 22 Z"/>` : "")
      + `<path class="line" d="M22 42 L42 22 L22 2 L2 22 Z"/>`
      + (path ? `<path class="path" d="${path}"/>` : "") + `</svg>`;
  }
  // The situation after a play, broadcast-style: occupied bases filled.
  function bases(b, cls = "sit") {
    const sq = (x, y, on) => `<rect x="${x - 5}" y="${y - 5}" width="10" height="10" transform="rotate(45 ${x} ${y})" class="${on ? "on" : ""}"/>`;
    return `<svg class="${cls}" viewBox="0 0 44 30" aria-hidden="true">${sq(33, 17, b[0] !== "-")}${sq(22, 7, b[1] !== "-")}${sq(11, 17, b[2] !== "-")}</svg>`;
  }
  const playHtml = play => {
    const [first, ...rest] = String(play || "").split(" ");
    const word = w => (w === "Kc" ? `<span class="kc">K</span>` : esc(w));
    return rest.length ? `${word(first)}<br>${esc(rest.join(" "))}` : word(first);
  };
  const playClass = play => (String(play).includes(" ") ? " two" : String(play).length > 4 ? " long" : "");
  const f1 = v => (v === null || v === undefined ? "–" : v.toFixed(1));
  const signed = v => (v === null ? "–" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(1));
  return { load, diamond, bases, playHtml, playClass, f1, signed, esc, HIT };
})();
