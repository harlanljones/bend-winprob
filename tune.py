#!/usr/bin/env python3
"""Model development on games the benchmark never scores.

The development set is every Final 2026 regular-season game except the benchmark's
test sample (fixtures-bench/pks.json) and bench.DEV_GAMES. Its fixtures are cached in
fixtures-bench/dev-cache/ (not committed). Every setting in live.py's rate model and
sim.bend's runner advancement was chosen here; the test games were scored once, after.

Win probabilities come from an exact dynamic program over the game sim.bend plays (same
outcome draws, advancement chances, automatic runner and endings), so a variant scores
all development plays in seconds instead of GPU hours. `check` replays games through Bend
and compares.

    python3 tune.py fetch          # download the development fixtures (resumable)
    python3 tune.py advancement    # runner-advancement chances measured on their plays
    python3 tune.py variants       # the shipped model and the alternatives it was chosen over
    python3 tune.py check          # Bend against the dynamic program on extra-inning games
"""
from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import numpy as np

import bench
import live

DEV = live.ROOT / "fixtures-bench" / "dev-cache"
PLAYERS = DEV / "players"
TEAM_BAT = live.API + ("/v1/teams/{id}/stats?stats=byDateRange&group=hitting&season={season}"
                       "&startDate={season}-01-01&endDate={end}&gameType=R")
BULK = live.API + ("/v1/stats?stats=byDateRange&group={group}&season=2026&startDate=2026-01-01&endDate={end}"
                   "&gameType=R&playerPool=ALL&limit=5000&sportId=1")
LAST = live.API + "/v1/stats?stats=season&group={group}&season=2025&gameType=R&playerPool=ALL&limit=5000&sportId=1"
KEEP = ("plateAppearances", "battersFaced", "strikeOuts", "baseOnBalls", "hitByPitch", "hitBatsmen", "hits",
        "doubles", "triples", "homeRuns", "gamesStarted")
# sim.bend's advancement chances (adv_* there, out of 10000).
ADVANCE = {"dp": .2101, "o3": .6108, "o2": .4913, "o1": .2082, "s2": .6117, "s13": .3541, "d1": .3805}
NORM = live.norms(2026)   # the development games are 2026's
LEAGUE = NORM["league"]
BASES = list(itertools.product([False, True], repeat=3))   # (on 1st, on 2nd, on 3rd)
BI = {b: i for i, b in enumerate(BASES)}
GHOST = BI[(False, True, False)]
MAXR = 25
R = MAXR + 1
OFF = 40


# Development set
# ---------------

def dev_pks():
    test = set(json.loads((bench.BENCH / "pks.json").read_text())["pks"])
    sched = live.fetch(bench.SCHEDULE.format(season=2026))
    seen, out = set(), []
    for d in sched["dates"]:
        for g in d["games"]:
            pk = g["gamePk"]
            if g["status"]["detailedState"] == "Final" and pk not in seen:
                seen.add(pk)
                if pk not in test and pk not in bench.DEV_GAMES:
                    out.append(pk)
    return out


def season_end(src):
    official = live.scheduled(src)["officialDate"]
    return official[:4], (date.fromisoformat(official) - timedelta(days=1)).isoformat()


def cached(path, url):
    if not path.exists():
        path.write_text(json.dumps(live.fetch(url)))
    return json.loads(path.read_text())


def compact(data):
    return {str(s["player"]["id"]): {k: s["stat"][k] for k in KEEP if k in s["stat"]}
            for s in data["stats"][0]["splits"]}


def fetch_game(pk):
    src = live.Source(pk, cache=True, allow_fetch=True, root=DEV)
    teams = live.teams_of(src.get("status"))
    for name in ("plays", "wp", "linescore", "box"):
        src.get(name)
    live.game_rates(src, teams)
    season, end = season_end(src)
    for side in ("away", "home"):
        tid = teams[side]["id"]
        cached(DEV / str(pk) / f"bat_{tid}.json", TEAM_BAT.format(id=tid, season=season, end=end))
    return end


def fetch(jobs):
    pks = dev_pks()
    PLAYERS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(jobs) as pool:
        futures = [(pk, pool.submit(fetch_game, pk)) for pk in pks]
        failed = [pk for pk, f in futures if f.exception()]
        ends = {f.result() for _, f in futures if not f.exception()}

        def bulk(group, end):
            path = PLAYERS / f"{group}_{end}.json"
            if not path.exists():
                path.write_text(json.dumps(compact(live.fetch(
                    LAST.format(group=group) if end == "2025" else BULK.format(group=group, end=end)))))
        list(pool.map(lambda a: bulk(*a), [(g, e) for e in ends | {"2025"} for g in ("hitting", "pitching")]))
    print(f"{len(pks) - len(failed)} of {len(pks)} development games cached; failed: {failed}")


def load_game(pk):
    """MLB's state after each play (the last, deciding play excluded), MLB's number, the result."""
    src = live.Source(pk, cache=True, allow_fetch=False, root=DEV)
    teams = live.teams_of(src.get("status"))
    plays = live.complete_plays(src.get("plays"))
    wp = live.wp_map(src.get("wp"))
    ls = src.get("linescore")
    ghost = live.automatic_runner(src)
    recs = [{"inning": 1, "top": True, "outs": 0, "bi": 0, "diff": 0, "mlb": None, "pre": True}]
    for p in plays[:-1]:
        ab, m = p["about"], p.get("matchup", {})
        inn, top, outs = ab["inning"], ab["isTopInning"], p["count"]["outs"]
        bases = ("postOnFirst" in m, "postOnSecond" in m, "postOnThird" in m)
        if outs >= 3:
            inn, top = (inn, False) if top else (inn + 1, True)
            outs, bases = 0, (False, ghost and inn >= 10, False)
        x = wp.get(ab["atBatIndex"])
        recs.append({"inning": inn, "top": top, "outs": outs, "bi": BI[bases], "pre": False,
                     "diff": p["result"]["homeScore"] - p["result"]["awayScore"],
                     "mlb": None if x is None else x / 100})
    return {"pk": pk, "src": src, "teams": teams, "plays": plays, "recs": recs, "ghost": ghost,
            "y": int(ls["teams"]["home"]["runs"] > ls["teams"]["away"]["runs"])}


# The game sim.bend plays, solved exactly
# ---------------------------------------

def transitions(b, o, e, adv):
    """[(chance, bases, outs, runs)] after outcome e from bases b with o outs. `adv` None is the
    original simulator (sacrifice fly always, hits move runners exactly as many bases)."""
    b1, b2, b3 = b
    if e == "K":
        return [(1.0, b, o + 1, 0)]
    if e == "W":
        return [(1.0, (True, b2 or b1, b3 or (b1 and b2)), o, int(b1 and b2 and b3))]
    if e == "T":
        return [(1.0, (False, False, True), o, b1 + b2 + b3)]
    if e == "H":
        return [(1.0, (False, False, False), o, b1 + b2 + b3 + 1)]
    if adv is None:
        if e == "O":
            r = int(b3 and o < 2)
            return [(1.0, (b1, b2, b3 and not r), o + 1, r)]
        if e == "S":
            return [(1.0, (True, b1, False), o, b3 + b2)]
        return [(1.0, (False, True, b1), o, b3 + b2)]
    out = []
    if e == "O":
        dp = adv["dp"] if (b1 and o < 2) else 0.0
        if dp:
            go = o == 0
            out.append((dp, (False, False, b2 and go), o + 2, int(b3 and go)))
        if o >= 2:
            return out + [(1.0 - dp, b, o + 1, 0)]
        for s3, s2, s1 in itertools.product((0, 1), repeat=3):
            p = 1.0 - dp
            for on, moves, k in ((b3, s3, "o3"), (b2, s2, "o2"), (b1, s1, "o1")):
                p *= (adv[k] if moves else 1 - adv[k]) if on else float(not moves)
            if p:
                n3 = b3 and not s3
                m2 = s2 and not n3
                n2 = (b2 and not m2)
                m1 = s1 and not n2
                out.append((p, (b1 and not m1, n2 or m1, n3 or m2), o + 1, s3))
        return out
    if e == "S":
        for sc2, go3 in itertools.product((0, 1), repeat=2):
            p = (adv["s2"] if sc2 else 1 - adv["s2"]) if b2 else float(not sc2)
            free = not (b2 and not sc2)
            p *= (adv["s13"] if go3 else 1 - adv["s13"]) if (b1 and free) else float(not go3)
            if p:
                out.append((p, (True, b1 and not go3, (b2 and not sc2) or (b1 and go3)), o, b3 + (b2 and sc2)))
        return out
    return [(p, (False, True, b1 and not sc), o, b3 + b2 + (b1 and sc))
            for sc, p in ((1, adv["d1"] if b1 else 0.0), (0, 1 - adv["d1"] if b1 else 1.0)) if p]


def half_tables(p, adv):
    """D[o, b, r]: chance of r more runs this half from o outs and bases b."""
    T = [(o, BI[b], p[e] * pr, no, BI[nb] if no < 3 else 0, r)
         for o in range(3) for b in BASES for e in live.ORDER for pr, nb, no, r in transitions(b, o, e, adv)]
    D = np.zeros((3, 8, R))
    for _ in range(80):
        N = np.zeros((3, 8, R))
        for o, bi, w, no, nbi, r in T:
            if no >= 3:
                N[o, bi, min(r, MAXR)] += w
            else:
                N[o, bi, r:] += w * D[no, nbi, :R - r]
        D = N
    return D


def _gt(dist, x):
    return dist[max(x + 1, 0):].sum()


def _at(v, d):
    return v[min(max(d + OFF, 0), 2 * OFF)]


class Game:
    """P(home wins) from any state, for fixed away and home rates (sim.bend's endings)."""

    def __init__(self, pa, ph, adv, ghost):
        self.Da, self.Dh = half_tables(pa, adv), half_tables(ph, adv)
        A, H = self.Da[0, 0], self.Dh[0, 0]
        Ax, Hx = (self.Da[0, GHOST], self.Dh[0, GHOST]) if ghost else (A, H)
        diffs = range(-OFF, OFF + 1)

        def bottom(d, dist, w0):   # ninth inning or later: a tie goes on
            return 1.0 if d > 0 else _gt(dist, -d) + (dist[-d] if -d < R else 0.0) * w0

        def top(d, adist, hdist, w0):
            return sum(adist[r] * (1.0 if d - r > 0 else bottom(d - r, hdist, w0)) for r in range(R))

        a = top(0, Ax, Hx, 0.0)
        self.W0 = a / (1 - (top(0, Ax, Hx, 1.0) - a))      # tied entering an extra inning
        self.WT = {(9, False): np.array([bottom(d, H, self.W0) for d in diffs]),
                   (9, True): np.array([top(d, A, H, self.W0) for d in diffs]),
                   (10, False): np.array([bottom(d, Hx, self.W0) for d in diffs])}
        for i in range(8, 0, -1):
            nxt = self.WT[(i + 1, True)]
            self.WT[(i, False)] = np.array([sum(H[r] * _at(nxt, d + r) for r in range(R)) for d in diffs])
            bot = self.WT[(i, False)]
            self.WT[(i, True)] = np.array([sum(A[r] * _at(bot, d - r) for r in range(R)) for d in diffs])

    def wp(self, inning, top, outs, bi, diff):
        if top:
            dist = self.Da[outs, bi]
            if inning >= 9:
                bot = self.WT[(min(inning, 10), False)]
                return sum(dist[r] * (1.0 if diff - r > 0 else _at(bot, diff - r)) for r in range(R))
            return sum(dist[r] * _at(self.WT[(inning, False)], diff - r) for r in range(R))
        dist = self.Dh[outs, bi]
        if inning >= 9:
            return 1.0 if diff > 0 else _gt(dist, -diff) + (dist[-diff] if -diff < R else 0.0) * self.W0
        return sum(dist[r] * _at(self.WT[(inning + 1, True)], diff + r) for r in range(R))


def from_cum(c):
    return {e: (x - p) / 10000 for e, x, p in zip(live.ORDER, c, [0, *c])}


# Rate models
# -----------

SLOT_PA = (4.65, 4.55, 4.45, 4.35, 4.25, 4.15, 4.05, 3.95, 3.85)   # plate appearances by lineup slot


def counts(stat, pa_key, hbp_key):
    if stat is None:
        return 0, dict.fromkeys(live.ORDER, 0)
    d, t, h = stat["doubles"], stat["triples"], stat["homeRuns"]
    n = {"K": stat["strikeOuts"], "W": stat["baseOnBalls"] + stat[hbp_key], "S": stat["hits"] - d - t - h,
         "D": d, "T": t, "H": h}
    n["O"] = stat[pa_key] - sum(n.values())
    return stat[pa_key], n


def rates_of(stats, prior, toward, pa_key="plateAppearances", hbp_key="hitByPitch", weights=(1.0,)):
    """Rates from counts (several seasons, each weighted) plus `prior` plate appearances of `toward`."""
    pa, n = 0.0, dict.fromkeys(live.ORDER, 0.0)
    for stat, w in zip(stats, weights):
        p, c = counts(stat, pa_key, hbp_key)
        pa += w * p
        for e in live.ORDER:
            n[e] += w * c[e]
    return {e: (n[e] + prior * toward[e]) / (pa + prior) for e in live.ORDER}


def matchup(bat, pit):
    """Generalized log5 against the league (the original model's combination)."""
    w = {e: bat[e] * pit[e] / LEAGUE[e] for e in live.ORDER}
    tot = sum(w.values())
    return {e: w[e] / tot for e in live.ORDER}


def players(group, end, _cache={}):
    if (group, end) not in _cache:
        _cache[(group, end)] = json.loads((PLAYERS / f"{group}_{end}.json").read_text())
    return _cache[(group, end)]


class Variant:
    """`team`: team batting and pitching combined by log5 (prior in plate appearances);
    `lineup`: the starting nine's batting, this season plus 0.7 x last, shrunk by 600;
    otherwise the shipped live.game_rates."""

    def __init__(self, kind="shipped", prior=1000):
        self.kind, self.prior = kind, prior

    def __call__(self, g):
        if self.kind == "shipped":
            return tuple(from_cum(c) for c in live.game_rates(g["src"], g["teams"]))
        season, end = season_end(g["src"])
        bat, pit = {}, {}
        for s in ("away", "home"):
            tid = g["teams"][s]["id"]
            hit = live.team_stat(json.loads((DEV / str(g["pk"]) / f"bat_{tid}.json").read_text()), "hitting")
            asof = g["src"].get(f"asof_{tid}", id=tid, season=season, end=end)
            bat[s] = rates_of([hit], self.prior, LEAGUE)
            pit[s] = rates_of([live.team_stat(asof, "pitching")], self.prior, LEAGUE, "battersFaced", "hitBatsmen")
        if self.kind == "lineup":
            away, home = (from_cum(c) for c in live.game_rates(g["src"], g["teams"]))
            out = {}
            for s, opp_rates in (("away", away), ("home", home)):
                order = g["src"].get("box")["teams"][s].get("battingOrder") or []
                if len(order) != 9:
                    out[s] = opp_rates
                    continue
                now, last = players("hitting", end), players("hitting", "2025")
                each = [rates_of([now.get(str(i)), last.get(str(i))], 600, LEAGUE, weights=(1.0, 0.7))
                        for i in order]
                lineup = {e: sum(w * r[e] for w, r in zip(SLOT_PA, each)) / sum(SLOT_PA) for e in live.ORDER}
                out[s] = matchup(lineup, opp_rates)
            return out["away"], out["home"]
        return (live.venue(matchup(bat["away"], pit["home"]), NORM["away"]),
                live.venue(matchup(bat["home"], pit["away"]), NORM["home"]))


# Scoring on the development set
# ------------------------------

_GAMES: list = []


def predict(args):
    i, rates, adv, ghost = args
    g = _GAMES[i]
    m = Game(*rates(g), adv, ghost and g["ghost"])
    return [min(max(m.wp(r["inning"], r["top"], r["outs"], r["bi"], r["diff"]), 0.0), 1.0) for r in g["recs"]]


def predict_all(games, rates, adv, ghost=True, procs=22):
    _GAMES[:] = games
    with mp.get_context("fork").Pool(procs) as pool:
        return pool.map(predict, [(i, rates, adv, ghost) for i in range(len(games))], chunksize=8)


def plays_of(games, preds):
    return [{"pk": g["pk"], "pre": r["pre"], "inning": r["inning"], "margin": abs(r["diff"]), "y": g["y"],
             "p": {"bend": float(p), "mlb": r["mlb"], "kalshi": None, "polymarket": None, "polymarket_us": None}}
            for g, ps in zip(games, preds) for r, p in zip(g["recs"], ps)]


def against(games, a, b):
    """Bend Brier of predictions `a` minus `b` on the plays MLB priced, game-bootstrap interval."""
    per = []
    for g, pa, pb in zip(games, a, b):
        d = [(x - g["y"]) ** 2 - (z - g["y"]) ** 2 for r, x, z in zip(g["recs"], pa, pb) if r["mlb"] is not None]
        if d:
            per.append((sum(d), len(d)))
    return bench.bootstrap_delta(per, b=2000)


# Measured advancement
# --------------------

NOT_IN_PLAY = {"strikeout", "strikeout_double_play", "walk", "intent_walk", "hit_by_pitch", "single", "double",
               "triple", "home_run", "catcher_interf"}
RUNNER_EVENTS = ("caught_stealing", "pickoff", "wild_pitch", "passed_ball", "stolen_base", "other_out", "balk")


def advancement(games):
    """Chances measured on plays whose runners all moved on the batted ball (one playIndex). Each half
    starts from empty bases, so an extra half's first play (the automatic runner) is not counted."""
    n = {k: [0, 0] for k in ADVANCE}
    for g in games:
        before, half = (False, False, False), None
        for p in g["plays"]:
            ab = p["about"]
            if (ab["inning"], ab["isTopInning"]) != half:
                half = (ab["inning"], ab["isTopInning"])
                before = (False, False, False)
            runners = p.get("runners", [])
            m = p.get("matchup", {})
            if len({r["details"].get("playIndex") for r in runners}) <= 1:
                end = {r["movement"].get("originBase"): "out" if r["movement"].get("isOut") else r["movement"].get("end")
                       for r in runners}
                outs = sum(1 for r in runners if r["movement"].get("isOut"))
                outs_before = min(p["count"]["outs"], 3) - outs
                b1, b2, b3 = before
                e1, e2, e3 = end.get("1B", "1B"), end.get("2B", "2B"), end.get("3B", "3B")
                ev = p["result"].get("eventType", "")
                if ev == "single":
                    if b2:
                        n["s2"][1] += 1; n["s2"][0] += e2 == "score"
                    if b1 and (not b2 or e2 == "score"):
                        n["s13"][1] += 1; n["s13"][0] += e1 in ("3B", "score")
                elif ev == "double":
                    if b1:
                        n["d1"][1] += 1; n["d1"][0] += e1 == "score"
                elif ev not in NOT_IN_PLAY and not ev.startswith(RUNNER_EVENTS) and outs_before < 2:
                    if b1:
                        n["dp"][1] += 1; n["dp"][0] += outs >= 2
                    if outs < 2:
                        if b3:
                            n["o3"][1] += 1; n["o3"][0] += e3 == "score"
                        if b2 and not b3:
                            n["o2"][1] += 1; n["o2"][0] += e2 in ("3B", "score")
                        if b1 and not b2:
                            n["o1"][1] += 1; n["o1"][0] += e1 in ("2B", "3B", "score")
            before = ("postOnFirst" in m, "postOnSecond" in m, "postOnThird" in m)
            if p["count"]["outs"] >= 3:
                before = (False, False, False)
    return {k: (a / b if b else 0.0, b) for k, (a, b) in n.items()}


def check(games, depth=18):
    """Replay extra-inning development games through Bend; compare with the dynamic program."""
    from sim_engine import ReplayEngine
    diffs = []
    for g in [g for g in games if any(p["about"]["inning"] >= 10 for p in g["plays"])][:3]:
        eng = ReplayEngine(g["pk"], depth=depth, mode=live.DEFAULT_MODE, fixtures=DEV)
        eng.seek(len(eng.plays))
        eng.finalize()
        m = Game(from_cum(eng.away_cum), from_cum(eng.home_cum), ADVANCE, eng.ghost)
        for r in eng.book.rows.values():
            if r["sims"] and r["bend_home_wp"] != "":
                b = r["bases"]
                w = m.wp(r["inning"], r["half"] == "T", r["outs"], BI[(b[0] == "1", b[1] == "2", b[2] == "3")],
                         r["home_runs"] - r["away_runs"])
                diffs.append(100 * w - r["bend_home_wp"])
        print(f"{g['pk']}: {len(eng.book.rows)} rows, {eng.book.mismatch_count()} mismatches, box {eng.box_ok}")
    d = np.array(diffs)
    sd = 50 / np.sqrt(2 ** depth)
    print(f"Bend - program over {len(d)} rows: mean {d.mean():+.3f} pp, rms {np.sqrt((d ** 2).mean()):.3f} pp "
          f"(Monte Carlo sd at most {sd:.3f} pp)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("fetch", "advancement", "variants", "check"))
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        fetch(args.jobs)
        return 0
    games = [load_game(pk) for pk in dev_pks()]
    print(f"{len(games)} development games, {sum(len(g['recs']) for g in games)} plays")
    if args.cmd == "advancement":
        for k, (rate, n) in advancement(games).items():
            print(f"{k:<4} {rate:.4f}  (n={n})")
    elif args.cmd == "check":
        check(games)
    else:
        rows = [("original: team batting and pitching (1000), original simulator", Variant("team", 1000), None, False),
                ("+ measured advancement, automatic runner", Variant("team", 1000), ADVANCE, True),
                ("+ heavier shrinkage (4000)", Variant("team", 4000), ADVANCE, True),
                ("shipped: pitching only, probable starter", Variant(), ADVANCE, True),
                ("shipped + starting nine's batting", Variant("lineup"), ADVANCE, True)]
        preds = {}
        for label, rates, adv, ghost in rows:
            preds[label] = predict_all(games, rates, adv, ghost)
            s = bench.paired(plays_of(games, preds[label]), "mlb")
            print(f"{label:<64} Brier {s['bend_brier']:.5f} vs MLB {s['other_brier']:.5f}  Δ {s['d_brier']:+.5f} "
                  f"[{s['d_brier_ci'][0]:+.5f}, {s['d_brier_ci'][1]:+.5f}]", flush=True)
        ship = preds[rows[3][0]]
        for label, *_ in rows[:3] + rows[4:]:
            d, lo, hi, _ = against(games, ship, preds[label])
            print(f"shipped minus {label!r}: {d:+.5f} [{lo:+.5f}, {hi:+.5f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
