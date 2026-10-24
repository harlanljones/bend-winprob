#!/usr/bin/env python3
"""Batch win-probability benchmark: replay many finished games at high depth.

Scores Bend's play-by-play home win probabilities against the observed game
outcomes (Brier score, log loss, MAE-vs-outcome) and against MLB's own
winProbability field for the same plays. Results land in runs/bench/.

    python3 bench.py                 # games from fixtures-bench/pks.json
    python3 bench.py --pks 849809 849805 --depth 20
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

from live import Source, ROOT
from sim_engine import ReplayEngine

BENCH = ROOT / "fixtures-bench"
OUT = ROOT / "runs" / "bench"


def brier(home_wp, home_won):
    p = home_wp / 100.0
    return (p - (1.0 if home_won else 0.0)) ** 2


def logloss(home_wp, home_won, eps=1e-4):
    p = min(max(home_wp / 100.0, eps), 1.0 - eps)
    y = 1.0 if home_won else 0.0
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def final_scores(src):
    """(away_runs, home_runs) from the finalized linescore fixture."""
    ls = src.get("linescore")
    return ls["teams"]["away"]["runs"], ls["teams"]["home"]["runs"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pks", type=int, nargs="*", help="gamePk list; default fixtures-bench/pks.json")
    ap.add_argument("--depth", type=int, default=20, help="2^depth sims per play (default 20 = 1,048,576)")
    ap.add_argument("--mode", choices=("cpu", "gpu"), default="gpu")
    ap.add_argument("--label", default="bench")
    args = ap.parse_args(argv)

    pk_list = args.pks or json.loads((BENCH / "pks.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    rows_path = OUT / f"{args.label}-rows.csv"
    summary_path = OUT / f"{args.label}-summary.json"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"bench {stamp}: {len(pk_list)} games, depth={args.depth} "
          f"(2^{args.depth} = {2 ** args.depth} sims/play), mode={args.mode}", flush=True)

    fieldnames = ["gamePk", "at_bat_index", "inning", "half", "outs", "bases",
                  "away_runs", "home_runs", "bend_home_wp", "mlb_home_wp",
                  "sims", "unfinished", "seconds", "state_check"]
    rows_file = rows_path.open("w")
    rows_file.write(",".join(fieldnames) + "\n")

    # Per-game scoring: bend and mlb against the true home win (1) / loss (0).
    # MLB is scored only where its WP field exists at or before each play.
    games = []
    start = time.monotonic()
    for n, pk in enumerate(pk_list, 1):
        try:
            src = Source(pk, cache=True, allow_fetch=True)   # fetch+persist fixture
            engine = ReplayEngine(pk, depth=args.depth, mode=args.mode,
                                  publisher=None, fetch=True, verbose=False)
            engine.reset()
            rows = []
            row = engine.pregame()
            rows.append(row)
            while engine.cursor < len(engine.plays):
                row = engine.step()
                if row is None:
                    break
                rows.append(row)
            engine.finalize()
            away_runs, home_runs = final_scores(src)
            if home_runs == away_runs:
                raise RuntimeError(f"pk {pk}: tie final {away_runs}-{home_runs}")
            home_won = home_runs > away_runs

            played = [r for r in rows if r["state_check"] == "ok" and r["bend_home_wp"] != ""]
            got_mlb = [r for r in played if r["mlb_home_wp"] != ""]
            gb = sum(brier(r["bend_home_wp"], home_won) for r in played) / len(played)
            gm = sum(brier(r["mlb_home_wp"], home_won) for r in got_mlb) / len(got_mlb)
            lb = sum(logloss(r["bend_home_wp"], home_won) for r in played) / len(played)
            lm = sum(logloss(r["mlb_home_wp"], home_won) for r in got_mlb) / len(got_mlb)
            ab = sum(abs(r["bend_home_wp"] - (100.0 if home_won else 0.0)) for r in played) / len(played)
            am = sum(abs(r["mlb_home_wp"] - (100.0 if home_won else 0.0)) for r in got_mlb) / len(got_mlb)
            bad = [r for r in rows if r["state_check"] != "ok"]
            secs = sum(r["seconds"] for r in played) / max(len(played), 1)
            rec = {"gamePk": pk, "plays_compared": len(played),
                   "plays_with_mlb": len(got_mlb), "home_won": home_won,
                   "final": f"{away_runs}-{home_runs}",
                   "bend_brier": round(gb, 5), "mlb_brier": round(gm, 5),
                   "bend_logloss": round(lb, 5), "mlb_logloss": round(lm, 5),
                   "bend_mae_outcome": round(ab, 3), "mlb_mae_outcome": round(am, 3),
                   "state_mismatches": len(bad), "avg_sec_per_play": round(secs, 4),
                   "sims": 2 ** args.depth}
            games.append(rec)
            print(f"[{n}/{len(pk_list)}] pk {pk} {rec['final']} "
                  f"bend Brier={rec['bend_brier']} mlb={rec['mlb_brier'] } "
                  f"({len(played)} plays, {len(bad)} mism)", flush=True)
            for r in played:
                rows_file.write(",".join(str(r.get(k, "")) for k in fieldnames) + "\n")
        except Exception as e:
            print(f"[{n}/{len(pk_list)}] pk {pk} FAILED: {e}", flush=True)
            games.append({"gamePk": pk, "error": str(e)})
            continue
    rows_file.close()

    ok = [g for g in games if "error" not in g]
    tot_bplays = sum(g["plays_compared"] for g in ok)
    tot_mplays = sum(g["plays_with_mlb"] for g in ok)
    summary = {
        "label": args.label, "when": stamp, "depth": args.depth,
        "sims_per_play": 2 ** args.depth, "mode": args.mode,
        "games_requested": len(pk_list), "games_scored": len(ok),
        "games_failed": len(pk_list) - len(ok),
        "bend_plays_scored": tot_bplays, "mlb_plays_scored": tot_mplays,
        "bend_brier": round(sum(g["bend_brier"] for g in ok) / max(len(ok), 1), 5),
        "mlb_brier": round(sum(g["mlb_brier"] for g in ok) / max(len(ok), 1), 5),
        "bend_logloss": round(sum(g["bend_logloss"] for g in ok) / max(len(ok), 1), 5),
        "mlb_logloss": round(sum(g["mlb_logloss"] for g in ok) / max(len(ok), 1), 5),
        "bend_mae_outcome": round(sum(g["bend_mae_outcome"] for g in ok) / max(len(ok), 1), 3),
        "mlb_mae_outcome": round(sum(g["mlb_mae_outcome"] for g in ok) / max(len(ok), 1), 3),
        "state_mismatches": sum(g["state_mismatches"] for g in ok),
        "avg_sec_per_play": round(sum(g["avg_sec_per_play"] for g in ok) / max(len(ok), 1), 4),
        "games": games,
    }
    summary_path.write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "games"}, indent=2))
    print(f"rows: {rows_path}\nsummary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

