# Bend vs MLB

An MLB win-probability engine written in [Bend](https://bend-lang.org): one
machine-proven scorebook, 2^20 Monte Carlo games per play forked across the GPU,
scored play-by-play against MLB's official `homeTeamWinProbability` and, as a
reference, the prices of the game-winner markets on Kalshi, Polymarket and
Polymarket US.

Live page: <https://bend-winprob.harlanljones.workers.dev>

## What is being proven

- **The scorebook is one function, and its invariants are theorems.** `game.bend`
  holds the state of a game and the single `step` that applies one completed play
  (every runner is taken off its origin, then placed — so exchanges and force plays
  need no special cases; an illegal play returns `None` and is counted as rejected).
  `LAWS.bend` states what must hold for every input; `PROOF.bend` proves each one by
  induction and case analysis. `bend PROOF.bend` must print `ALL PROOFS CHECK` before
  any commit:
  - the simulation tree plays and counts exactly 2^d games, however the work splits;
  - the scorebook never shows three or more outs;
  - each team's batters balance its runs, putouts, and runners left and on base
    (OBR 9.03(c), "How to Prove a Box Score");
  - a play never takes a run off the board.
- **Every simulated game is played by that same `step`.** `sim.bend` forks 2^d games
  from the current state (`tree!` runs the identical program on the GPU); plate
  appearances are integer draws against cumulative thresholds — no floating point in
  the engine.
- **It tracks a production model on real data.** See the benchmark below.

## Headline numbers

**Every 2025 regular-season game** (`bench.py --manifest fixtures-bench/pks-2025.json`;
page at `/bench/?run=2025`): no 2025 game was used to choose any setting, and 2025 games
are played against 2024's league rates and home/away factors. 2,424 of 2,425 games
scored (one feed the encoder could not read: two runners from second, gamePk 777680),
182,982 plays, 47 rows unscored after a refused play in 2 games. The box-score proof
holds in 2,420 games; it fails in those 2 and in 2 where Bend counts one batter more
than the official box. Against MLB's official number on 180,558 paired plays:

| Against | Bend Brier | MLB Brier | Δ Brier (95% CI) | Δ log loss (95% CI) | Bend better (games) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MLB official | 0.1538 | 0.1549 | −0.0011 [−0.0022, −0.0001] | −0.0026 [−0.0053, +0.0002] | 1,415–1,009 | clear win |

Bend is lower in 98.3% of the 10,000 game resamples, closer to the result on 68.4% of
plays, and better calibrated (error 1.31 pp vs 2.56 pp). The edge is in the first three
innings (Δ −0.0024, a clear win on its own); later innings and every run margin show no
clear difference. Markets were not recorded for 2025.

**The 2026 sample** (`python3 bench.py --web`; page at `/bench/`):
100 games drawn at random from the 2026 regular season (seed 2026, stratified by
month, the 12 games inspected while developing the first model excluded), depth
2^20 (1,048,576 sims/play) on the GPU, 0.103 s per play. All 100 replayed and were
scored: 7,467 plays, none unscored, every box score proven (OBR 9.03(c), with the
automatic runner in extra innings).

Head to head on paired plays. Δ is Bend minus the other source; the 95% interval
resamples whole games (10,000 resamples):

| Against | Paired plays | Bend Brier | Their Brier | Δ Brier (95% CI) | Bend better (games) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MLB official | 7,367 | 0.1640 | 0.1642 | −0.0002 [−0.0053, +0.0049] | 60–40 | no clear difference |
| Kalshi | 7,107 | 0.1620 | 0.1621 | −0.0001 [−0.0054, +0.0053] | 49–50 | no clear difference |
| Polymarket | 6,980 | 0.1647 | 0.1684 | −0.0037 [−0.0141, +0.0043] | 51–49 | no clear difference |
| Polymarket US | 6,727 | 0.1751 | 0.1815 | −0.0065 [−0.0252, +0.0059] | 46–54 | no clear difference |

Bend's Brier is lower than every other source's on its paired plays, and no
interval excludes zero: 100 games are too few to settle differences this small.
Bend is closer than MLB to the result on 67.2% of plays. Calibration, Bend vs MLB
by inning and run margin, and every game are on the benchmark page, from
`web/bench/data.json`.

The model was chosen on the other 2,315 Final 2026 games (`tune.py`), never on these
100: there Bend's Brier is 0.1554 against MLB's 0.1571 (Δ −0.0017, 95% CI −0.0028 to
−0.0006), against −0.0003 for the first model. It is the second model scored on the
test games; on the 93 the first one completed, the first scored 0.1653 vs MLB's
0.1670 and this one 0.1662 vs 0.1671, so the gain seen on the development games
does not show on these 93.

On the bundled replay of World Series Game 1 (TB @ MIL) the mean absolute difference
to MLB is 8.36 pp over 69 plays (2.04 pp to Kalshi), Bend's box score matches the
official one exactly under OBR 9.03(c), and the per-play scorebook check reports zero
mismatches.

## The model

- **Rates.** Each side bats at the previous season's league rates against the other
  side's pitching through the day before the game: the team's, shrunk toward the league
  by 2,000 batters faced, blended with the probable starter's (shrunk toward his
  team's by 600) by the share of batters he is expected to face; the previous season's
  home/away factors on top (`live.NORMS`). Team batting to date, and the starting
  nine's batting, did not predict results on the development games and are left out.
- **Simulated plays.** Runner advancement is measured on the development games'
  play-by-play: double plays (21% of outs in play with a runner on first and fewer
  than two outs), runners scoring or moving up on outs in play, from second on
  singles, first-to-third, and from first on doubles. Regular-season extra innings
  start with the automatic runner on second, placed by Bend in both the simulated
  games and the real game's scorebook.
- **Checked.** `tune.py` solves the same game exactly; `python3 tune.py check`
  replays extra-inning games through Bend and agrees within Monte Carlo noise.

## Prediction markets

`markets.py` puts three exchanges' game-winner prices beside Bend and MLB, one CSV
column each (`kalshi_home_wp`, `polymarket_home_wp`, `polymarket_us_home_wp`, home
win %, empty when unknown). All three publish market data without credentials.

| Venue | Market | Found by | Price |
| --- | --- | --- | --- |
| Kalshi | `KXMLBGAME-<ET date+time><away><home>`, one market per team | scheduled first pitch (ET) and MLB abbreviations | bid/ask midpoints of both team markets, normalised to 100 |
| Polymarket | `mlb-<away>-<home>-<date>` moneyline | official date, Polymarket abbreviations (`ari`, `oak`) | the home token's price |
| Polymarket US | `aec-mlb-<away>-<home>-<date>` | official date and MLB abbreviations | bid/ask midpoint of the long side, turned to the home team |

Polymarket and Polymarket US are separate exchanges with separate books: Polymarket
is the international, crypto-based one; Polymarket US is a CFTC-regulated exchange
for US residents that trades in US dollars
([Polymarket US docs](https://docs.polymarket.us/getting-started/what-is-polymarket-us)).

A play's price is read 60 s after it ended (minute bars need that long to be sure
the play is priced in), or when the next play ended if that came first, and only
from an observation taken after the play ended: a play followed too quickly by the
next, before any bar closes, has no price. The pregame row reads at first pitch. A
book that is one-sided or wider than 10¢ gives no price, and neither does an
observation more than 5 minutes old. Live,
each venue is refreshed in a background thread (a quote every poll, minute history
every 5 minutes, so a restart backfills earlier plays), and a venue outage is
logged, never fatal. Replays read `fixtures/<pk>/markets.json`, recorded once with
`--fetch` and then frozen like every other fixture; the bundled game is recorded,
and benchmark games are cached in `fixtures-bench/cache/` (not committed). Not
included: Novig (API keys; its read-only GraphQL is being retired), ProphetX and
Betfair (credentials), Smarkets (its API refuses non-browser clients), Manifold
(no per-game markets).

## Layout

| Path | What it is |
| --- | --- |
| `game.bend` | the scorebook: state + the one `step` that applies a play |
| `sim.bend` | Monte Carlo: 2^d games as a balanced fork tree (CPU or GPU); runner advancement and the automatic runner |
| `LAWS.bend` | the invariants that must hold for every input |
| `PROOF.bend` | their proofs; `bend PROOF.bend` prints `ALL PROOFS CHECK` |
| `main.bend` | the program `live.py` runs once per play (`bend main.bend -o wp`) |
| `live.py` | MLB Stats API feed → plays, rates, CSVs, Cloudflare publisher |
| `markets.py` | Kalshi, Polymarket, Polymarket US: find the game's market, price history and quotes |
| `sim_engine.py` | offline replay engine over a cached fixture (no network) |
| `bench.py` | benchmark: seeded random draw (`--draw`), replay at depth 20, pooled Brier / log loss / calibration, game-bootstrap intervals vs MLB and the markets |
| `tune.py` | model development on the 2,315 non-test games: an exact solver of the simulated game, measured advancement, rate-model variants, a Bend agreement check |
| `tests/` | Python unit tests for the replay engine, CSV encoding and market pricing; `tests/web/` runs the pages' scorebook, chart and formatting modules under `node --test` |
| `web/` | the hosted pages: the scorebook (`index.html`, styles `scorebook.css`, script `js/main.js`) and the benchmark (`bench/index.html`, styles `bench/bench.css`, script `bench/bench.js`, data in `bench/data.json`) sharing `book.css` and the ES modules in `web/js/` (`common.js` formatting and verdicts, `series.js` line marks and venues, which also ink the charts, `scorebook.js` and `chart.js` pure logic tested by `tests/web/`, `diagrams.js`), no build step; self-hosted fonts in `web/fonts/`, a bundled replay of World Series Game 1 in `web/demo/`; diagrams and charts are Mermaid rendered by [Pele](https://pele.run) |
| `cloudflare/` | Worker + Durable Object serving the page and the feed |

## Quick start

```sh
bend PROOF.bend                            # ALL PROOFS CHECK
python3 sim_engine.py --pk 849805          # replay World Series Game 1, 65,536 sims/play
python3 bench.py --web                     # the 100-game 2026 benchmark (GPU, depth 20)
python3 bench.py --draw 9999 --season 2025 --manifest fixtures-bench/pks-2025.json
python3 bench.py --manifest fixtures-bench/pks-2025.json --label 2025 --no-markets \
  --sim-jobs 4 --web web/bench/data-2025.json   # every 2025 game, ~3 h
python3 -m unittest discover -s tests -v
node --test tests/web/                     # the pages' scorebook, chart and format logic
```

Fixtures are cached under `fixtures/`; nothing is fetched unless `--fetch` (or
`fetch=True`) is supplied. Per-play output lands in `runs/<gamePk>.csv`.

## Hosting

The page and its feed are one Cloudflare Worker with a single Durable Object
(`cloudflare/`). `python3 live.py --publish` POSTs each new CSV
(`WP_PUSH_URL`, `WP_PUSH_TOKEN` in `.env`); the page polls
`/runs/<gamePk>.csv` every 5 s and falls back to the bundled replay in `web/demo/`
when nothing is published. `bash run_live.sh` supervises a live game with 5–60 s
backoff and logs every run to `logs/`. `--no-markets` leaves the market columns
empty.

## Limits

- Pitching to date only: plate appearances are i.i.d. draws at the previous season's
  league batting rates against each side's pitching (team plus probable starter), with
  the previous season's home/away adjustment — no lineup, platoon, park, umpire,
  weather, leverage or bullpen state.
- A four-slot play encoding (r3, r2, r1, batter); a play it cannot carry is refused
  and counted — 47 rows in 2 of 2,424 scored 2025 games, none in the 2026 sample or
  the bundled replay; one 2025 game's feed could not be encoded.
- Sample: every 2025 game settles Bend vs MLB; the markets were compared only on the
  100-game 2026 sample, where no comparison is settled.
- MLB's win probability is a production model with far more information than this
  proof of concept uses; the comparison is a benchmark, not a claim of superiority.
- Market prices are a reference, not ground truth: minute bars, read up to a minute
  after the play (they can include the next batter's first pitches), with the
  bid/ask spread and fees left in.
- Not a betting tool.
