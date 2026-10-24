# Bend vs MLB

An MLB win-probability engine written in [Bend](https://bend-lang.org): one
machine-proven scorebook, 2^20 Monte Carlo games per play forked across the GPU,
scored play-by-play against MLB's official `homeTeamWinProbability`.

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

Benchmark run of 2026-10-23: 12 finished games, 871 plays scored (859 carrying an
MLB value), 0 failures, depth 2^20 (1,048,576 sims/play) on the GPU.

| Metric | Bend | MLB official | Bend better by |
| --- | --- | --- | --- |
| Brier score | 0.1245 | 0.1543 | 19.3% |
| Log loss | 0.3913 | 0.4565 | 14.3% |
| Mean abs. error vs outcome | 29.08 pp | 32.97 pp | 11.8% |
| Scorebook mismatches | 29 / 871 plays (3.3%) | — | — |
| Time per play | 0.099 s | — | ≈10.6M sims/s |

Bend's Brier is lower in 9 of the 12 games. A second run at depth 2^16 on a single
game (75 plays) gave Brier 0.031 against MLB's 0.048. On a bundled full-game replay
the mean absolute difference to MLB is 2.70 pp over 70 plays, Bend's box score
matches the official one exactly under OBR 9.03(c), and the per-play scorebook check
reports zero mismatches. Per-game results: `runs/bench/season-summary.json`.

## Layout

| Path | What it is |
| --- | --- |
| `game.bend` | the scorebook: state + the one `step` that applies a play |
| `sim.bend` | Monte Carlo: 2^d games as a balanced fork tree (CPU or GPU) |
| `LAWS.bend` | the invariants that must hold for every input |
| `PROOF.bend` | their proofs; `bend PROOF.bend` prints `ALL PROOFS CHECK` |
| `main.bend` | the program `live.py` runs once per play (`bend main.bend -o wp`) |
| `live.py` | MLB Stats API feed → plays, rates, CSVs, Cloudflare publisher |
| `sim_engine.py` | offline replay engine over a cached fixture (no network) |
| `bench.py` | batch benchmark: Brier / log loss / MAE vs MLB, per game |
| `tests/` | Python unit tests for the replay engine and CSV encoding |
| `web/` | the hosted page: one HTML file, self-hosted fonts in `web/fonts/`, a bundled replay in `web/demo/`; diagrams and the live chart are Mermaid rendered by [Pele](https://pele.run) |
| `cloudflare/` | Worker + Durable Object serving the page and the feed |

## Quick start

```sh
bend PROOF.bend                            # ALL PROOFS CHECK
python3 sim_engine.py --pk 849809          # replay a finished game, 65,536 sims/play
python3 bench.py                           # the 12-game benchmark (GPU, depth 20)
python3 -m unittest discover -s tests -v
```

Fixtures are cached under `fixtures/`; nothing is fetched unless `--fetch` (or
`fetch=True`) is supplied. Per-play output lands in `runs/<gamePk>.csv`.

## Hosting

The page and its feed are one Cloudflare Worker with a single Durable Object
(`cloudflare/`). `python3 live.py --publish` POSTs each new CSV
(`WP_PUSH_URL`, `WP_PUSH_TOKEN` in `.env`); the page polls
`/runs/<gamePk>.csv` every 5 s and falls back to the bundled replay in `web/demo/`
when nothing is published. `bash run_live.sh` supervises a live game with 5–60 s
backoff and logs every run to `logs/`.

## Limits

- Season-level team rates: plate appearances are i.i.d. draws from each team's
  season distribution — no batter, pitcher, platoon, park, umpire, weather,
  leverage or bullpen state.
- A four-slot play encoding (r3, r2, r1, batter). Pickoffs, caught stealings,
  wild pitches and passed balls do not fit and are refused — 29 of 871 plays in
  the benchmark, 0 in the bundled replay.
- Small sample: 12 games, 871 plays, per-game Brier from 0.03 to 0.30.
- MLB's win probability is a production model with far more information than this
  proof of concept uses; the comparison is a benchmark, not a claim of superiority.
- Not a betting tool.
