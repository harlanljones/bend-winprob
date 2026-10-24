#!/usr/bin/env python3
"""Batch win-probability benchmark: replay many finished games at high depth.

Scores Bend's play-by-play home win probabilities against the observed game
outcomes (Brier score, log loss, MAE-vs-outcome), beside MLB's own
winProbability field and the prediction-market prices recorded in
fixtures/<pk>/markets.json for the same plays. Each source is scored on the
plays where it has a value, and all of them together on the plays where every
source has one ("common"). Results land in runs/bench/.

    python3 bench.py                 # games from fixtures-bench/pks.json
    python3 bench.py --pks 823244 849805 --depth 20
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import markets
from live import Source, ROOT
from sim_engine import ReplayEngine

BENCH = ROOT / "fixtures-bench"
OUT = ROOT / "runs" / "bench"
SOURCES = ("bend", "mlb", *markets.KEYS)


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


def score(rows, home_won, sources):
    """Mean Brier, log loss and MAE-vs-outcome (pp) per source over `rows`."""
    out = {}
    for s in sources:
        ps = [r[f"{s}_home_wp"] for r in rows]
        if ps:
            out[s] = {"brier": sum(brier(p, home_won) for p in ps) / len(ps),
                      "logloss": sum(logloss(p, home_won) for p in ps) / len(ps),
                      "mae_outcome": sum(abs(p - (100.0 if home_won else 0.0)) for p in ps) / len(ps)}
    return out


def mean_of(games, field):
    vals = [g[field] for g in games if g.get(field) is not None]
    return sum(vals) / len(vals) if vals else None


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
                  "away_runs", "home_runs", *(f"{s}_home_wp" for s in SOURCES),
                  "sims", "unfinished", "seconds", "state_check"]
    rows_file = rows_path.open("w")
    rows_file.write(",".join(fieldnames) + "\n")

    # Per-game scoring against the true home win (1) / loss (0). Each source is
    # scored where it has a value; "common" scores every source on the same plays.
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
            have = {s: [r for r in played if r[f"{s}_home_wp"] != ""] for s in SOURCES}
            common = [r for r in played if all(r[f"{s}_home_wp"] != "" for s in SOURCES)]
            bad = [r for r in rows if r["state_check"] != "ok"]
            secs = sum(r["seconds"] for r in played) / max(len(played), 1)
            rec = {"gamePk": pk, "plays_compared": len(played),
                   "home_won": home_won, "final": f"{away_runs}-{home_runs}",
                   "markets": [m["id"] for m in engine.listings],
                   "state_mismatches": len(bad), "avg_sec_per_play": round(secs, 4),
                   "sims": 2 ** args.depth, "common_plays": len(common)}
            for s in SOURCES:
                rec[f"plays_with_{s}"] = len(have[s])
                own = score(have[s], home_won, [s]).get(s, {})
                both = score(common, home_won, [s]).get(s, {})
                for m in ("brier", "logloss", "mae_outcome"):
                    rec[f"{s}_{m}"] = round(own[m], 5) if m in own else None
                    rec[f"common_{s}_{m}"] = round(both[m], 5) if m in both else None
            games.append(rec)
            print(f"[{n}/{len(pk_list)}] pk {pk} {rec['final']} "
                  f"bend Brier={rec['bend_brier']} mlb={rec['mlb_brier']} "
                  + " ".join(f"{s}={rec[f'{s}_brier']}" for s in markets.KEYS)
                  + f" ({len(played)} plays, {len(common)} common, {len(bad)} mism)", flush=True)
            for r in played:
                rows_file.write(",".join(str(r.get(k, "")) for k in fieldnames) + "\n")
        except Exception as e:
            print(f"[{n}/{len(pk_list)}] pk {pk} FAILED: {e}", flush=True)
            games.append({"gamePk": pk, "error": str(e)})
            continue
    rows_file.close()

    ok = [g for g in games if "error" not in g]
    summary = {
        "label": args.label, "when": stamp, "depth": args.depth,
        "sims_per_play": 2 ** args.depth, "mode": args.mode,
        "games_requested": len(pk_list), "games_scored": len(ok),
        "games_failed": len(pk_list) - len(ok),
        "common_plays_scored": sum(g["common_plays"] for g in ok),
    }
    for s in SOURCES:
        summary[f"{s}_plays_scored"] = sum(g[f"plays_with_{s}"] for g in ok)
        summary[f"{s}_games_scored"] = sum(g[f"plays_with_{s}"] > 0 for g in ok)
    # Per-game means, averaged over the games where the source has plays.
    for prefix in ("", "common_"):
        for s in SOURCES:
            for m, digits in (("brier", 5), ("logloss", 5), ("mae_outcome", 3)):
                v = mean_of(ok, f"{prefix}{s}_{m}")
                summary[f"{prefix}{s}_{m}"] = None if v is None else round(v, digits)
    summary.update({
        "state_mismatches": sum(g["state_mismatches"] for g in ok),
        "avg_sec_per_play": round(sum(g["avg_sec_per_play"] for g in ok) / max(len(ok), 1), 4),
        "games": games,
    })
    summary_path.write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "games"}, indent=2))
    print(f"rows: {rows_path}\nsummary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

