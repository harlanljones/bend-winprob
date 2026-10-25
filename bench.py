#!/usr/bin/env python3
"""Win-probability benchmark: replay a seeded random sample of finished games at high depth.

Scores Bend's play-by-play home win probabilities against how each game ended,
beside MLB's own winProbability field and the prediction-market prices recorded
for the same plays. Every metric is pooled over plays; head-to-head differences
carry 95% intervals from resampling whole games. Results land in runs/bench/,
and with --web in web/bench/data.json for the benchmark page.

    python3 bench.py --draw 100 --seed 2026   # write fixtures-bench/pks.json
    python3 bench.py --web                    # run the manifest, publish the page data
    python3 bench.py --draw 9999 --season 2025 --manifest fixtures-bench/pks-2025.json
    python3 bench.py --manifest fixtures-bench/pks-2025.json --label 2025 --no-markets \\
        --sim-jobs 4 --web web/bench/data-2025.json   # every 2025 game, untouched by tuning
    python3 bench.py --pks 823244 824550 --depth 12 --label smoke
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from math import comb

import live
import markets
from live import ROOT
from sim_engine import ReplayEngine

BENCH = ROOT / "fixtures-bench"
CACHE = BENCH / "cache"
OUT = ROOT / "runs" / "bench"
WEB = ROOT / "web" / "bench" / "data.json"
SOURCES = ("bend", "mlb", *markets.KEYS)
NAMES = {"bend": "Bend", "mlb": "MLB official", "kalshi": "Kalshi", "polymarket": "Polymarket",
         "polymarket_us": "Polymarket US"}
# Inspected while developing the model; never in the test sample.
DEV_GAMES = (823244, 822828, 822908, 824925, 824187, 825072, 822882, 824247, 825049, 823585,
             824550, 823164)
SCHEDULE = (live.API + "/v1/schedule?sportId=1&season={season}&gameType=R&startDate={season}-01-01"
            "&endDate={season}-12-31&fields=dates,games,gamePk,officialDate,status,detailedState")
B = 10000
SEED = 2026
FIELDS = ["gamePk", "at_bat_index", "inning", "half", "outs", "bases", "away_runs", "home_runs",
          *(f"{s}_home_wp" for s in SOURCES), "sims", "unfinished", "seconds", "state_check"]
INNINGS = ("pregame", "1–3", "4–6", "7–9", "10+")
MARGINS = ("tied", "1", "2–3", "4+")


# Sample
# ------

def stratified_sample(games, n, seed, excluded):
    """(pks, strata): n Final games drawn by month, quotas by largest remainder."""
    skip, seen, months = set(excluded), set(), {}
    for g in games:
        pk = g["gamePk"]
        if g["status"]["detailedState"] != "Final" or pk in skip or pk in seen:
            continue
        seen.add(pk)
        months.setdefault(g["officialDate"][:7], []).append((g["officialDate"], pk))
    total = sum(len(v) for v in months.values())
    order = sorted(months)
    exact = {m: n * len(months[m]) / total for m in order}
    quota = {m: int(exact[m]) for m in order}
    left = n - sum(quota.values())
    for m in sorted(order, key=lambda m: (-(exact[m] - quota[m]), order.index(m)))[:left]:
        quota[m] += 1
    rng = random.Random(seed)
    picked = []
    for m in order:
        picked += rng.sample(sorted(months[m], key=lambda x: x[1]), quota[m])
    return [pk for _, pk in sorted(picked)], quota


def draw(n, seed, season, path):
    """Write a manifest of n games drawn from the season's Final regular-season games (all of them
    when n is at least the population). 2026 excludes DEV_GAMES."""
    sched = live.fetch(SCHEDULE.format(season=season))
    games = [g for d in sched["dates"] for g in d["games"]]
    excluded = DEV_GAMES if season == 2026 else ()
    population = len({g["gamePk"] for g in games if g["status"]["detailedState"] == "Final"} - set(excluded))
    n = min(n, population)
    pks, strata = stratified_sample(games, n, seed, excluded)
    manifest = {"season": season, "seed": seed, "n": n, "population": population,
                "excluded": list(excluded), "strata": strata, "pks": pks}
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"drew {len(pks)} of {population} games, seed {seed}: {strata} -> {path}")
    return 0


# Metrics
# -------

def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)


def logloss(ps, ys, eps=1e-4):
    tot = 0.0
    for p, y in zip(ps, ys):
        p = min(max(p, eps), 1 - eps)
        tot -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return tot / len(ps)


def _bins(ps, ys):
    bins = [[] for _ in range(10)]
    for p, y in zip(ps, ys):
        bins[min(int(100 * p // 10), 9)].append((p, y))
    return bins


def calibration(ps, ys):
    out = []
    for k, b in enumerate(_bins(ps, ys)):
        n = len(b)
        out.append({"lo": 10 * k, "hi": 10 * k + 10, "n": n,
                    "forecast": round(100 * sum(p for p, _ in b) / n, 3) if n else None,
                    "observed": round(100 * sum(y for _, y in b) / n, 3) if n else None})
    return out


def decompose(ps, ys):
    """Murphy's reliability, resolution and uncertainty over the 10 bins, and ECE in pp."""
    N, o = len(ps), sum(ys) / len(ys)
    rel = res = ece = 0.0
    for b in _bins(ps, ys):
        if b:
            n = len(b)
            f, ob = sum(p for p, _ in b) / n, sum(y for _, y in b) / n
            rel += n * (f - ob) ** 2
            res += n * (ob - o) ** 2
            ece += n * abs(f - ob)
    return {"rel": rel / N, "res": res / N, "unc": o * (1 - o), "ece_pp": 100 * ece / N}


def accuracy(ps, ys):
    """Share of plays on the right side of 50%; a forecast of exactly 50% counts half."""
    return sum(.5 if p == .5 else float((p > .5) == (y == 1)) for p, y in zip(ps, ys)) / len(ps)


def bootstrap_delta(games, seed=SEED, b=B):
    """(point, lo, hi, p_better) for a pooled mean difference, resampling whole games."""
    point = sum(s for s, _ in games) / sum(n for _, n in games)
    rng, d = random.Random(seed), []
    for _ in range(b):
        draws = rng.choices(games, k=len(games))
        n = sum(x[1] for x in draws)
        if n:
            d.append(sum(x[0] for x in draws) / n)
    d.sort()
    return point, d[int(.025 * len(d))], d[min(len(d) - 1, int(.975 * len(d)))], \
        sum(x < 0 for x in d) / len(d)


def verdict(lo, hi):
    return "clear win" if hi < 0 else "clear loss" if lo > 0 else "no clear difference"


def sign_test(better, worse):
    """Exact two-sided binomial p for better vs worse games."""
    better, worse = int(better), int(worse)
    n = better + worse
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, k) for k in range(min(better, worse) + 1)) / 2 ** n)


def _r(x, d=5):
    return None if x is None else round(x, d)


def source_score(plays, s):
    have = [r for r in plays if r["p"][s] is not None]
    if not have:
        return None
    ps, ys = [r["p"][s] for r in have], [r["y"] for r in have]
    dec, b = decompose(ps, ys), brier(ps, ys)
    return {"plays": len(have), "games": len({r["pk"] for r in have}), "brier": _r(b),
            "logloss": _r(logloss(ps, ys)),
            "bss": _r(1 - b / dec["unc"]) if dec["unc"] else None,
            "accuracy": round(100 * accuracy(ps, ys), 3),
            "rel": _r(dec["rel"]), "res": _r(dec["res"]), "unc": _r(dec["unc"]),
            "ece_pp": round(dec["ece_pp"], 3), "calibration": calibration(ps, ys)}


def per_game_diffs(plays, other, loss):
    """[(sum of Bend-minus-other losses, n)] per game, games in first-seen order."""
    acc = {}
    for r in plays:
        s, n = acc.get(r["pk"], (0.0, 0))
        acc[r["pk"]] = (s + loss(r["p"]["bend"], r["y"]) - loss(r["p"][other], r["y"]), n + 1)
    return list(acc.values())


def se(p, y):
    return (p - y) ** 2


def ll(p, y):
    return logloss([p], [y])


def paired(plays, other):
    both = [r for r in plays if r["p"]["bend"] is not None and r["p"][other] is not None]
    if not both:
        return None
    ys = [r["y"] for r in both]
    bend = [r["p"]["bend"] for r in both]
    them = [r["p"][other] for r in both]
    gb = per_game_diffs(both, other, se)
    d, lo, hi, pb = bootstrap_delta(gb)
    dl, llo, lhi, _ = bootstrap_delta(per_game_diffs(both, other, ll))
    sb, so = [se(p, y) for p, y in zip(bend, ys)], [se(p, y) for p, y in zip(them, ys)]
    better = sum(s < 0 for s, _ in gb)
    worse = sum(s > 0 for s, _ in gb)
    return {"plays": len(both), "games": len(gb), "bend_brier": _r(brier(bend, ys)),
            "other_brier": _r(brier(them, ys)), "d_brier": _r(d), "d_brier_ci": [_r(lo), _r(hi)],
            "p_better": _r(pb), "d_logloss": _r(dl), "d_logloss_ci": [_r(llo), _r(lhi)],
            "plays_closer": round(100 * sum(a < b for a, b in zip(sb, so)) / len(both), 3),
            "plays_tied": round(100 * sum(a == b for a, b in zip(sb, so)) / len(both), 3),
            "games_better": better, "games_worse": worse,
            "sign_p": _r(sign_test(better, worse)), "verdict": verdict(lo, hi)}


def inning_key(r):
    if r["pre"]:
        return "pregame"
    i = r["inning"]
    return "1–3" if i <= 3 else "4–6" if i <= 6 else "7–9" if i <= 9 else "10+"


def margin_key(r):
    m = r["margin"]
    return "tied" if m == 0 else "1" if m == 1 else "2–3" if m <= 3 else "4+"


def segments(plays):
    both = [r for r in plays if r["p"]["bend"] is not None and r["p"]["mlb"] is not None]
    out = []
    for group, keyf, keys in (("inning", inning_key, INNINGS), ("margin", margin_key, MARGINS)):
        for key in keys:
            seg = [r for r in both if keyf(r) == key]
            if not seg:
                continue
            ys = [r["y"] for r in seg]
            d, lo, hi, _ = bootstrap_delta(per_game_diffs(seg, "mlb", se))
            out.append({"group": group, "key": key, "plays": len(seg),
                        "bend_brier": _r(brier([r["p"]["bend"] for r in seg], ys)),
                        "mlb_brier": _r(brier([r["p"]["mlb"] for r in seg], ys)),
                        "d_brier": _r(d), "d_brier_ci": [_r(lo), _r(hi)], "verdict": verdict(lo, hi)})
    return out


# Run
# ---

def play_record(pk, r, y):
    return {"pk": pk, "pre": r["at_bat_index"] == -1, "inning": r["inning"],
            "margin": abs(r["home_runs"] - r["away_runs"]), "y": y,
            "p": {s: None if r[f"{s}_home_wp"] == "" else r[f"{s}_home_wp"] / 100 for s in SOURCES}}


def engine_for(pk, args):
    """The game's replay engine, downloading any fixture it still lacks."""
    engine = ReplayEngine(pk, depth=args.depth, mode=args.mode, publisher=None, fetch=True,
                          verbose=False, fixtures=CACHE, with_markets=args.markets)
    for name in ("box", "linescore", "schedule"):
        engine.source.get(name)
    return engine


def simulate(engine):
    """Every row after a full replay (the decided final row has sims == 0)."""
    engine.reset()
    engine.pregame()
    while engine.cursor < len(engine.plays):
        if engine.step() is None:
            break
    engine.finalize()
    return [engine.book.rows[i] for i in sorted(engine.book.rows)]


def run_game(pk, args):
    """Replay one game; its rows, scored play records and per-game line."""
    engine = engine_for(pk, args)
    rows = simulate(engine)
    ls = engine.source.get("linescore")
    away_runs, home_runs = ls["teams"]["away"]["runs"], ls["teams"]["home"]["runs"]
    if home_runs == away_runs:
        raise RuntimeError(f"tie final {away_runs}-{home_runs}")
    y = 1 if home_runs > away_runs else 0
    scored = [r for r in rows if r["state_check"] == "ok" and r["sims"] > 0 and r["bend_home_wp"] != ""]
    bad = sum(r["state_check"] != "ok" for r in rows)
    recs = [play_record(pk, r, y) for r in scored]
    pair = [r for r in recs if r["p"]["mlb"] is not None]
    ys = [r["y"] for r in pair]
    bb = brier([r["p"]["bend"] for r in pair], ys) if pair else None
    mb = brier([r["p"]["mlb"] for r in pair], ys) if pair else None
    game = {"gamePk": pk, "date": live.scheduled(engine.source)["officialDate"],
            "away": engine.teams["away"]["abbr"], "home": engine.teams["home"]["abbr"],
            "final": f"{away_runs}-{home_runs}", "home_won": bool(y), "scored": len(scored),
            "unscored": bad, "bend_brier": _r(bb), "mlb_brier": _r(mb), "d_brier": _r(bb - mb) if pair else None}
    return {"rows": rows, "recs": recs, "game": game, "secs": [r["seconds"] for r in scored]}


def version(cmd):
    try:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pks", type=int, nargs="*", help="gamePk list instead of the manifest")
    ap.add_argument("--manifest", type=Path, default=BENCH / "pks.json", help="default fixtures-bench/pks.json")
    ap.add_argument("--depth", type=int, default=20, help="2^depth sims per play (default 20 = 1,048,576)")
    ap.add_argument("--mode", choices=("cpu", "gpu"), default="gpu")
    ap.add_argument("--label", default="season")
    ap.add_argument("--draw", type=int, metavar="N", help="draw N games (all, if N is at least the season's "
                    "Final games) into --manifest and exit")
    ap.add_argument("--season", type=int, default=2026, help="season to draw from (default 2026)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--web", nargs="?", type=Path, const=WEB, help="also write the page data (default web/bench/data.json)")
    ap.add_argument("--jobs", type=int, default=4, help="parallel fixture downloads")
    ap.add_argument("--sim-jobs", type=int, default=1, help="games simulated at once (the GPU overlaps ~4)")
    ap.add_argument("--no-markets", dest="markets", action="store_false", help="skip the market recordings")
    args = ap.parse_args(argv)
    if args.draw:
        return draw(args.draw, args.seed, args.season, args.manifest)

    if args.pks:
        pk_list, sample = args.pks, None
    else:
        manifest = json.loads(args.manifest.read_text())
        pk_list, sample = manifest["pks"], {k: v for k, v in manifest.items() if k != "pks"}
    OUT.mkdir(parents=True, exist_ok=True)
    rows_path, summary_path = OUT / f"{args.label}-rows.csv", OUT / f"{args.label}-summary.json"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"bench {stamp}: {len(pk_list)} games, depth={args.depth} "
          f"(2^{args.depth} = {2 ** args.depth} sims/play), mode={args.mode}"
          + ("" if args.markets else ", no markets"), flush=True)

    failed = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:   # every fixture first, in parallel
        futures = {pk: pool.submit(engine_for, pk, args) for pk in pk_list}
        for pk, fut in futures.items():
            if fut.exception():
                failed[pk] = f"{type(fut.exception()).__name__}: {fut.exception()}"
                print(f"pk {pk} fetch FAILED: {failed[pk]}", flush=True)

    done = {}
    with ThreadPoolExecutor(max_workers=args.sim_jobs) as pool:
        futures = {pool.submit(run_game, pk, args): pk for pk in pk_list if pk not in failed}
        for fut in as_completed(futures):
            pk = futures[fut]
            try:
                done[pk] = fut.result()
            except Exception as e:
                failed[pk] = f"{type(e).__name__}: {e}"
                print(f"[{len(done) + len(failed)}/{len(pk_list)}] pk {pk} FAILED: {failed[pk]}", flush=True)
                continue
            g = done[pk]["game"]
            print(f"[{len(done) + len(failed)}/{len(pk_list)}] pk {pk} {g['final']} paired Brier "
                  f"bend={g['bend_brier']} mlb={g['mlb_brier']} ({g['scored']} scored, {g['unscored']} unscored)",
                  flush=True)

    plays, per_game, secs = [], [], []
    with rows_path.open("w") as rows_file:
        rows_file.write(",".join(FIELDS) + "\n")
        for pk in pk_list:
            if pk in done:
                for r in done[pk]["rows"]:
                    rows_file.write(",".join(str(pk if k == "gamePk" else r.get(k, "")) for k in FIELDS) + "\n")
                plays += done[pk]["recs"]
                per_game.append(done[pk]["game"])
                secs += done[pk]["secs"]

    per_game.sort(key=lambda g: (g["date"], g["gamePk"]))
    summary = {
        "when": stamp, "commit": version(["git", "describe", "--always", "--dirty"]),
        "bend": version(["bend", "version"]), "depth": args.depth, "sims_per_play": 2 ** args.depth,
        "mode": args.mode, "avg_sec_per_play": round(sum(secs) / len(secs), 4) if secs else None,
        "sample": sample,
        "games": {"requested": len(pk_list), "scored": len(per_game),
                  "failed": [{"gamePk": pk, "error": failed[pk]} for pk in pk_list if pk in failed]},
        "scored_plays": len(plays), "unscored_plays": sum(g["unscored"] for g in per_game),
        "games_with_unscored": sum(g["unscored"] > 0 for g in per_game),
        "home_win_rate": round(100 * sum(r["y"] for r in plays) / len(plays), 3) if plays else None,
        "names": NAMES,
        "sources": {s: source_score(plays, s) for s in SOURCES},
        "paired": {o: paired(plays, o) for o in SOURCES[1:]},
        "segments": segments(plays),
        "per_game": per_game,
    }
    text = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    summary_path.write_text(text)
    if args.web:
        args.web.parent.mkdir(parents=True, exist_ok=True)
        args.web.write_text(text)
    print("paired (Bend minus other, Brier, 95% CI over games):")
    for o, p in summary["paired"].items():
        if p:
            print(f"  {NAMES[o]:<14} {p['plays']:>6} plays {p['games']:>3} games  bend {p['bend_brier']:.5f} "
                  f"vs {p['other_brier']:.5f}  Δ {p['d_brier']:+.5f} [{p['d_brier_ci'][0]:+.5f}, "
                  f"{p['d_brier_ci'][1]:+.5f}]  {p['verdict']}")
    print(f"rows: {rows_path}\nsummary: {summary_path}" + (f"\nweb: {args.web}" if args.web else ""), flush=True)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
