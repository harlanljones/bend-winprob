# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three confirmed audiences, in order:

1. Bend / programming-language people: want to see a machine-proven, GPU-parallel Bend program doing real work. The engineering is the point.
2. Baseball-analytics readers: want to know whether the win-probability model holds up against MLB's official number. The benchmark is the point.
3. Recruiters and portfolio viewers: want evidence of taste, rigor, and shipping. The whole artifact is the point.

Situation: arriving from a link (GitHub README, Bend community, a shared URL), usually once, on desktop or phone, with no account and no prior context.

## Product Purpose

A proof of concept: an MLB win-probability engine written in Bend. One proven scorebook (`game.bend`), 2^d Monte Carlo games per play forked across the GPU (`sim.bend`), invariants stated in `LAWS.bend` and proven in `PROOF.bend`, driven against real games by `live.py` and benchmarked by `bench.py`. The hosted page is the public face: a live (or replayed) game with Bend's number beside MLB's, the method, the benchmark, and how to reproduce it.

Success: a visitor from any audience leaves believing the three claims below are true and can verify them from the page alone.

## Positioning

What a neighbouring project could not truthfully copy:

- The scorebook's invariants are theorems, not tests. `bend PROOF.bend` prints `ALL PROOFS CHECK`; the four laws (tree plays and counts exactly 2^d games; never three outs; OBR 9.03(c) box-score balance; a play never removes a run) are proven by induction and case analysis.
- Every one of the 2^20 simulated games per play is played by that same proven `step`. Integer draws only; no floating point in the engine. `tree!` runs the identical program on the GPU.
- It tracks a production model on real data: over every 2025 regular-season game (no 2025 game used to choose any setting), Brier 0.1538 vs MLB's 0.1549 on 180,558 paired plays (Δ −0.0011, 95% CI −0.0022 to −0.0001: a clear win, Bend better in 1,415 of 2,424 games). On the 100-game 2026 sample, 0.1640 vs 0.1642 (no clear difference).

## Operating Context

- `live.py --publish` POSTs each new per-play CSV to a Cloudflare Worker with one Durable Object; the page polls `/runs/<gamePk>.csv` and `/runs/<gamePk>-meta.json` every 5 s and falls back to the bundled replay in `web/demo/` when nothing is published. `?pk=<gamePk>` selects a game.
- Per-play CSV columns used by the page: `at_bat_index, inning, half, bases, outs, code, batter, play, away_runs, home_runs, bend_home_wp, mlb_home_wp, kalshi_home_wp, polymarket_home_wp, polymarket_us_home_wp, delta, sims, seconds, mode, state_check, wall_time`. `code` is Bend's 4-character play code (the page follows each batter around the bases with it), `batter` the batter's surname and `play` the scorer's notation (K, Kc for a called third strike, 6-3, F8, 1B, BB, 4-6-3 DP), from MLB's play-by-play. The three market columns are optional and may be empty: each venue's home-win price in percent (bid/ask midpoint; Kalshi's two team markets normalised to 100), read within 60 s after the play ended; shown as a reference line, the market median in each scorecard box, and the readout only when present; `delta` stays Bend − MLB.
- Meta JSON: `pk, away, home` plus optional `away_name, home_name, away_logo, home_logo`, and `markets`: `[{key, name, url, id}]` for venues listing the game (`key` ∈ `kalshi, polymarket, polymarket_us`; the page links the venue name to `url`).
- The pages are static HTML (`web/index.html`, `web/bench/index.html` rendered from `web/bench/data.json`) sharing `web/book.css`, served by the Worker; no build step, no framework.
- Offline reproduction: `bend PROOF.bend`, `python3 sim_engine.py --pk 849805`, `python3 bench.py --web`, `python3 -m unittest discover -s tests -v`; model development: `python3 tune.py fetch|advancement|variants|check`.

## Capabilities and Constraints

- Confirmed: all page diagrams, including the live win-probability curve, are rendered with Pele (pele.run; Mermaid syntax → themeable SVG). The live curve is a Mermaid `xychart` re-rendered on each poll.
- Confirmed: factual numbers are binding; prose may be tightened or re-sequenced but no claim may be added or changed.
- Function to preserve: 5 s polling, live-then-replay fallback, `?pk=` selection, dark/light theme with persisted choice, feed-freshness indicator, links to the raw CSV and meta.
- Terminology: gamePk, half-inning (Top/Bottom), bases string `12-` style, outs, Brier score, log loss, pp (percentage points), sims, depth 2^d.
- Not a betting tool. The comparison is a benchmark, not a claim of superiority over MLB's model.

## Brand Commitments

- Name: "Bend vs MLB". Repository `harlanljones/bend-winprob`.
- Voice (from README and current page): declarative, specific, no hype; laws and numbers stated plainly.
- Pinned tooling: Pele for every diagram on the page.

## Evidence on Hand

- 2025 season run of 2026-10-24 (README.md, web/bench/data-2025.json, /bench/?run=2025): all 2,425 Final 2025 regular-season games, 2,424 scored (777680: feed not encodable), 182,982 plays, 47 rows unscored in 2 games; box proof holds in 2,420 games. Played against 2024 league rates and home/away factors; no markets recorded. Bend vs MLB: 0.1538 vs 0.1549, Δ −0.00115 [−0.00221, −0.00010], log loss Δ −0.0026 [−0.0053, +0.0002], closer on 68.4% of plays, calibration error 1.31 vs 2.56 pp; innings 1–3 Δ −0.0024 (clear win), later innings no clear difference.
- Benchmark run of 2026-10-24 (README.md, web/bench/data.json, /bench/): 100 games drawn at random from the 2026 regular season (seed 2026, stratified by month, 12 first-model development games excluded), depth 2^20 on GPU, 0.103 s per play. All 100 scored, 7,467 plays, none unscored; all 200 box checks OK. Paired Brier, Bend vs: MLB 0.1640 vs 0.1642 (Δ −0.0002 [−0.0053, +0.0049]), Kalshi 0.1620 vs 0.1621, Polymarket 0.1647 vs 0.1684, Polymarket US 0.1751 vs 0.1815; every verdict "no clear difference". Bend better than MLB in 60 of 100 games, closer on 67.2% of plays.
- Model chosen on the other 2,315 Final 2026 games (tune.py): pitching to date (team, probable starter) against league batting, measured runner advancement, automatic runner in regular-season extras. Second model scored on the test games; on the 93 the first completed: first 0.1653 vs MLB 0.1670, this one 0.1662 vs 0.1671.
- Bundled replay `web/demo/849805.csv` + `849805-meta.json` (World Series Game 1, TB @ MIL): 69 plays, mean |Δ| to MLB 8.36 pp (2.04 pp to Kalshi), box score matches official under OBR 9.03(c), zero mismatches.
- Code snippets in the page are verbatim from `game.bend`, `sim.bend`, and `live.py` output.
- Team logos arrive via `meta.away_logo` / `home_logo` when published; none bundled.
- No testimonials, press, or customer logos exist; none may be invented.

## Product Principles

1. Prove, then show: every claim on the page is reproducible by a command on the page.
2. The live game is the demonstration; the numbers beside it are the argument.
3. State limits as plainly as results.
4. One file, one Worker, one binary: keep the artifact as simple as the thing it describes.
