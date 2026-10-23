#!/usr/bin/env python3
"""Bend vs MLB live win probability.

The host shell around ./wp (main.bend): fetches MLB Stats API data, encodes
every completed play as a 4-char code, runs Bend on the whole play list,
and prints Bend's home win probability next to MLB's. Bend owns the
scorebook and the simulation; this file owns HTTP, JSON, CSV and the chart.

  python3 live.py                       # live, World Series Game 1
  python3 live.py --pk 849809 --replay  # rehearse a finished game
"""

import argparse
import csv
import functools
import json
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://statsapi.mlb.com/api"
URLS = {
    "status": API + "/v1.1/game/{pk}/feed/live?fields=metaData,wait,gameData,status,"
    "abstractGameState,detailedState,teams,away,home,id,abbreviation",
    "plays": API + "/v1/game/{pk}/playByPlay?fields=allPlays,result,eventType,awayScore,"
    "homeScore,about,atBatIndex,inning,isTopInning,isComplete,count,outs,runners,movement,"
    "originBase,start,end,isOut,details,runner,matchup,postOnFirst,postOnSecond,postOnThird,id",
    "wp": API + "/v1/game/{pk}/winProbability?fields=atBatIndex,homeTeamWinProbability",
    "box": API + "/v1/game/{pk}/boxscore?fields=teams,away,home,teamStats,batting,fielding,"
    "atBats,baseOnBalls,hitByPitch,sacBunts,sacFlies,catchersInterference,runs,putOuts",
    "linescore": API + "/v1/game/{pk}/linescore?fields=teams,home,away,runs,leftOnBase",
    "teamstats": API + "/v1/teams/{id}/stats?stats=season&group=hitting,pitching&season=2026",
}

# 2025 MLB per-plate-appearance rates (Baseball-Reference league totals, PA 182,926).
LEAGUE = {"K": .2222, "O": .4638, "W": .0946, "S": .1428, "D": .0423, "T": .0034, "H": .0309}
ORDER = "KOWSDTH"
DEFAULT_MODE = "gpu"  # RTX 4070 Ti: 2^20 games 0.09 s (gpu) vs 0.15 s (24 threads)
CSV_HEADER = ["wall_time", "at_bat_index", "inning", "half", "outs", "bases", "away_runs",
              "home_runs", "bend_home_wp", "mlb_home_wp", "delta", "sims", "unfinished",
              "seconds", "mode", "state_check"]


class BendError(Exception):
    pass


# HTTP / fixtures
# ---------------

def fetch(url):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as e:  # network, HTTP or JSON failure: retry
            last = e
            if attempt < 2:
                time.sleep(2)
    raise RuntimeError(f"fetch failed: {url}: {last}")


class Source:
    """Replay reads fixtures/<pk>/<name>.json, fetching and saving any missing one."""

    def __init__(self, pk, cache):
        self.pk = pk
        self.dir = ROOT / "fixtures" / str(pk) if cache else None

    def get(self, name, **kw):
        url = URLS[name.split("_")[0]].format(pk=self.pk, **kw)
        if self.dir is None:
            return fetch(url)
        path = self.dir / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text())
        data = fetch(url)
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1))
        return data


# Plays
# -----

def encode_play(play):
    """One completed play as slots r3 r2 r1 batter: - X R 1 2 3.

    A runner's movements are grouped by runner id: `originBase` is per event,
    so a runner who steals second and then scores on a single shows origins
    1B and 2B. The runner's base at the start of the play is the head of the
    chain (a start that is no other segment's end); the batter starts at None.
    """
    i = play["about"]["atBatIndex"]
    by_runner = {}
    for r in play.get("runners", []):
        rid = r.get("details", {}).get("runner", {}).get("id")
        if rid is None:
            raise ValueError(f"runner without id at atBatIndex {i}")
        by_runner.setdefault(rid, []).append(r["movement"])
    slots = {}
    for rid, segs in by_runner.items():
        starts = [s.get("start") for s in segs]
        ends = [s.get("end") for s in segs if s.get("end") is not None]
        heads = {s for s in starts if s is None or s not in ends}
        if len(heads) != 1:
            raise ValueError(f"runner {rid}: no single start {sorted(map(str, heads))} at atBatIndex {i}")
        origin = heads.pop()
        if origin not in ("3B", "2B", "1B", None):
            raise ValueError(f"unknown origin {origin!r} at atBatIndex {i}")
        if origin in slots:
            raise ValueError(f"two runners from {origin or 'the batter'} at atBatIndex {i}")
        if any(s.get("isOut") for s in segs):
            slots[origin] = "X"
        elif any(s.get("end") == "score" for s in segs):
            slots[origin] = "R"
        else:
            tails = {e for e in ends if e not in starts}
            if len(tails) != 1 or not tails <= {"1B", "2B", "3B"}:
                raise ValueError(f"runner {rid}: unknown end {sorted(tails)} at atBatIndex {i}")
            slots[origin] = tails.pop()[0]
    return "".join(slots.get(origin, "-") for origin in ("3B", "2B", "1B", None))


def complete_plays(pbp):
    return [p for p in pbp.get("allPlays", []) if p.get("about", {}).get("isComplete")]


def check_state(b, play):
    """Field names where Bend's state after `play` differs from MLB's."""
    bad = []
    res, about, outs = play["result"], play["about"], play["count"]["outs"]
    if b["away_runs"] != res["awayScore"]:
        bad.append("away_runs")
    if b["home_runs"] != res["homeScore"]:
        bad.append("home_runs")
    top = about["isTopInning"]
    if outs == 3:
        want = (about["inning"] + (0 if top else 1), not top, 0, "---")
    else:
        mu = play.get("matchup", {})
        bases = ("1" if "postOnFirst" in mu else "-") + ("2" if "postOnSecond" in mu else "-") \
            + ("3" if "postOnThird" in mu else "-")
        want = (about["inning"], top, outs, bases)
    got = (b["inning"], b["top"], b["outs"], b["bases"])
    for name, w, g in zip(("inning", "half", "outs", "bases"), want, got):
        if w != g:
            bad.append(name)
    if b["rejected"] > 0:
        bad.append("rejected")
    return bad


# Rates
# -----

def side_rates(stat, pa_key, hbp_key):
    pa = stat[pa_key]
    k, w = stat["strikeOuts"], stat["baseOnBalls"] + stat[hbp_key]
    d, t, h = stat["doubles"], stat["triples"], stat["homeRuns"]
    s = stat["hits"] - d - t - h
    o = pa - (k + w + s + d + t + h)
    return {"K": k / pa, "O": o / pa, "W": w / pa, "S": s / pa, "D": d / pa, "T": t / pa, "H": h / pa}


def team_stat(ts, group):
    for st in ts["stats"]:
        if st["group"]["displayName"] == group:
            return st["splits"][0]["stat"]
    raise ValueError(f"no {group} stats")


def matchup(bat, pit):
    """Generalized log5 against the league."""
    w = {e: bat[e] * pit[e] / LEAGUE[e] for e in ORDER}
    tot = sum(w.values())
    return {e: w[e] / tot for e in ORDER}


def cumulative(p):
    acc, out = 0.0, []
    for e in ORDER:
        acc += p[e]
        out.append(round(10000 * acc))
    out[-1] = 10000
    return out


def game_rates(src, teams):
    """(awayCum, homeCum): each side's batting against the other's pitching."""
    away_ts = src.get(f"teamstats_{teams['away']['id']}", id=teams["away"]["id"])
    home_ts = src.get(f"teamstats_{teams['home']['id']}", id=teams["home"]["id"])
    bat = {s: side_rates(team_stat(ts, "hitting"), "plateAppearances", "hitByPitch")
           for s, ts in (("away", away_ts), ("home", home_ts))}
    pit = {s: side_rates(team_stat(ts, "pitching"), "battersFaced", "hitBatsmen")
           for s, ts in (("away", away_ts), ("home", home_ts))}
    return cumulative(matchup(bat["away"], pit["home"])), cumulative(matchup(bat["home"], pit["away"]))


# Bend
# ----

def run_bend(depth, seed, away_cum, home_cum, codes, mode):
    arg = "|".join([str(depth), str(seed), ",".join(map(str, away_cum)),
                    ",".join(map(str, home_cum)), ";".join(codes), mode])
    rts = ["--threads", "24"] if mode == "cpu" else ["--gpu", "4GB"]
    t0 = time.monotonic()
    try:
        p = subprocess.run([str(ROOT / "wp"), arg, "+RTS", *rts], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise BendError("timeout after 120 s")
    secs = time.monotonic() - t0
    lines = {ln.split(" ", 1)[0]: ln.split()[1:] for ln in p.stdout.splitlines() if ln.strip()}
    if "ERROR" in lines:
        raise BendError(" ".join(["ERROR", *lines["ERROR"]]))
    if p.returncode != 0 or not all(k in lines for k in ("STATE", "LINE", "SIM")):
        first = (p.stdout + p.stderr).strip().splitlines()
        raise BendError(f"exit {p.returncode}: {first[0] if first else 'no output'}")
    st, line, sim = lines["STATE"], list(map(int, lines["LINE"])), list(map(int, lines["SIM"]))
    return {
        "inning": int(st[0]), "top": st[1] == "T", "outs": int(st[2]), "bases": st[3],
        "away_runs": int(st[4]), "home_runs": int(st[5]), "rejected": int(st[6]),
        "line": line, "home_wins": sim[0], "away_wins": sim[1], "unfinished": sim[2],
        "seconds": secs,
    }


def seed_for(n_plays):
    return (2654435761 * (n_plays + 1)) % 2 ** 32


# Rows, ticker, CSV
# -----------------

class Book:
    """Rows keyed by at_bat_index (-1: pregame), rewritten to runs/<pk>.csv."""

    def __init__(self, pk, away, home, depth, mode):
        self.pk, self.away, self.home, self.depth, self.mode = pk, away, home, depth, mode
        self.rows = {}
        self.mismatches = 0
        runs = ROOT / "runs"
        runs.mkdir(exist_ok=True)
        self.csv = runs / f"{pk}.csv"
        (runs / f"{pk}-meta.json").write_text(json.dumps({"pk": pk, "away": away, "home": home}))

    def add(self, idx, b, play, mlb):
        bad = check_state(b, play) if play is not None else []
        if b["rejected"] > 0 and "rejected" not in bad:
            bad.append("rejected")
        self.mismatches += bool(bad)
        decided = b["home_wins"] + b["away_wins"]
        bend = 100.0 * b["home_wins"] / decided if decided else None
        check = "ok" if not bad else "MISMATCH(" + ",".join(bad) + ")"
        self.rows[idx] = {
            "wall_time": time.strftime("%Y-%m-%dT%H:%M:%S"), "at_bat_index": idx,
            "inning": b["inning"], "half": "T" if b["top"] else "B", "outs": b["outs"],
            "bases": b["bases"], "away_runs": b["away_runs"], "home_runs": b["home_runs"],
            "bend_home_wp": "" if bend is None else round(bend, 2),
            "mlb_home_wp": "" if mlb is None else round(mlb, 2), "delta": "",
            "sims": 2 ** self.depth, "unfinished": b["unfinished"],
            "seconds": round(b["seconds"], 3), "mode": self.mode, "state_check": check,
        }
        self.fill_delta(idx)
        self.print_row(idx)

    def fill_delta(self, idx):
        r = self.rows[idx]
        r["delta"] = "" if r["bend_home_wp"] == "" or r["mlb_home_wp"] == "" \
            else round(r["bend_home_wp"] - r["mlb_home_wp"], 2)

    def backfill(self, wp):
        for idx, r in self.rows.items():
            if r["mlb_home_wp"] == "" and idx in wp:
                r["mlb_home_wp"] = round(wp[idx], 2)
                self.fill_delta(idx)

    def print_row(self, idx):
        r = self.rows[idx]
        tag = "pre" if idx < 0 else str(idx)
        bend = "--" if r["bend_home_wp"] == "" else f"{r['bend_home_wp']:.1f}%"
        mlb = "--" if r["mlb_home_wp"] == "" else f"{r['mlb_home_wp']:.1f}%"
        delta = "--" if r["delta"] == "" else f"{r['delta']:+.1f}"
        print(f"#{tag} {r['half']}{r['inning']} {r['outs']}o [{r['bases']}] "
              f"{self.away} {r['away_runs']} {self.home} {r['home_runs']} | "
              f"Bend {self.home} {bend} | MLB {self.home} {mlb} | Δ {delta} | "
              f"{r['sims']:,} sims {r['seconds']:.2f}s {r['mode']} | state {r['state_check']}",
              flush=True)

    def write(self):
        tmp = self.csv.with_suffix(".tmp")
        with tmp.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADER)
            w.writeheader()
            for idx in sorted(self.rows):
                w.writerow(self.rows[idx])
        tmp.replace(self.csv)

    def final(self, home_won):
        last = max(self.rows)
        r = self.rows[last]
        r["bend_home_wp"], r["sims"] = (100.0 if home_won else 0.0), 0
        self.fill_delta(last)

    def summary(self):
        deltas = [abs(r["delta"]) for r in self.rows.values() if r["delta"] != ""]
        mean = sum(deltas) / len(deltas) if deltas else float("nan")
        print(f"SUMMARY rows {len(self.rows)} mean |Δ| {mean:.2f} over {len(deltas)} "
              f"mismatches {self.mismatches}", flush=True)
        return mean


def wp_map(wp):
    return {e["atBatIndex"]: e["homeTeamWinProbability"] for e in wp
            if "homeTeamWinProbability" in e}


def box_check(box, ls, b):
    """OBR 9.03(c) on the official box score, and Bend's scorebook against it."""
    ok = True
    for side, opp, at in (("away", "home", 0), ("home", "away", 4)):
        bat = box["teams"][side]["teamStats"]["batting"]
        supply = (bat["atBats"] + bat["baseOnBalls"] + bat["hitByPitch"] + bat["sacBunts"]
                  + bat["sacFlies"] + bat.get("catchersInterference", 0))
        runs, lob = ls["teams"][side]["runs"], ls["teams"][side]["leftOnBase"]
        po = box["teams"][opp]["teamStats"]["fielding"]["putOuts"]
        b_bat, b_runs, b_outs, b_lob = b["line"][at:at + 4]
        batting_now = b["top"] == (side == "away")
        b_lob += (3 - b["bases"].count("-")) if batting_now else 0
        good = (supply == runs + lob + po and (b_bat, b_runs, b_lob, b_outs) == (supply, runs, lob, po))
        ok &= good
        print(f"BOX {side} official {supply}={runs}+{lob}+{po} "
              f"bend {b_bat}={b_runs}+{b_lob}+{b_outs} {'OK' if good else 'FAIL'}", flush=True)
    return ok


# Modes
# -----

def teams_of(status):
    t = status["gameData"]["teams"]
    return {s: {"id": t[s]["id"], "abbr": t[s]["abbreviation"]} for s in ("away", "home")}


def replay(args):
    src = Source(args.pk, cache=True)
    status = src.get("status")
    teams = teams_of(status)
    away_cum, home_cum = game_rates(src, teams)
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / f"{args.pk}-rates.json").write_text(json.dumps({"away": away_cum, "home": home_cum}))
    plays = complete_plays(src.get("plays"))
    wp = wp_map(src.get("wp"))
    codes = [encode_play(p) for p in plays]
    book = Book(args.pk, teams["away"]["abbr"], teams["home"]["abbr"], args.depth, args.mode)
    print(f"{teams['away']['abbr']} @ {teams['home']['abbr']}  awayCum {away_cum}  homeCum {home_cum}")
    errors = 0
    b = None
    for k in range(len(plays) + 1):
        try:
            b = run_bend(args.depth, seed_for(k), away_cum, home_cum, codes[:k], args.mode)
        except BendError as e:
            errors += 1
            print(f"#{plays[k - 1]['about']['atBatIndex'] if k else 'pre'} bend error: {e}", flush=True)
            continue
        if k == 0:
            book.add(-1, b, None, None)
        else:
            idx = plays[k - 1]["about"]["atBatIndex"]
            book.add(idx, b, plays[k - 1], wp.get(idx))
    final = status["gameData"]["status"]["abstractGameState"] == "Final"
    box_ok = True
    if final and b is not None:
        book.final(b["home_runs"] > b["away_runs"])
        box_ok = box_check(src.get("box"), src.get("linescore"), b)
    book.write()
    book.summary()
    return 0 if errors == 0 and book.mismatches == 0 and box_ok else 1


def serve(port):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


def live(args):
    src = Source(args.pk, cache=False)
    if not args.no_serve:
        serve(args.port)
        print(f"chart: http://127.0.0.1:{args.port}/web/?pk={args.pk}", flush=True)
    status = src.get("status")
    teams = teams_of(status)
    rates_path = ROOT / "runs" / f"{args.pk}-rates.json"
    (ROOT / "runs").mkdir(exist_ok=True)
    if rates_path.exists():
        r = json.loads(rates_path.read_text())
        away_cum, home_cum = r["away"], r["home"]
    else:
        away_cum, home_cum = game_rates(src, teams)
        rates_path.write_text(json.dumps({"away": away_cum, "home": home_cum}))
    away, home = teams["away"]["abbr"], teams["home"]["abbr"]
    print(f"{away} @ {home}  awayCum {away_cum}  homeCum {home_cum}  depth {args.depth}  {args.mode}",
          flush=True)
    book = Book(args.pk, away, home, args.depth, args.mode)
    done = []  # codes already turned into rows
    last_wait = 0.0
    try:
        while True:
            try:
                status = src.get("status")
            except RuntimeError as e:
                print(f"poll failed: {e}", flush=True)
                time.sleep(10)
                continue
            state = status["gameData"]["status"]["abstractGameState"]
            detailed = status["gameData"]["status"]["detailedState"]
            wait = max(10, status.get("metaData", {}).get("wait", 10))
            if -1 not in book.rows:
                try:
                    book.add(-1, run_bend(args.depth, seed_for(0), away_cum, home_cum, [], args.mode),
                             None, None)
                    book.write()
                except BendError as e:
                    print(f"#pre bend error: {e}", flush=True)
            if state == "Preview":
                if time.time() - last_wait >= 60:
                    print(f"waiting: {detailed}", flush=True)
                    last_wait = time.time()
                time.sleep(wait)
                continue
            try:
                plays = complete_plays(src.get("plays"))
                codes = [encode_play(p) for p in plays]
                wp = wp_map(src.get("wp"))
            except (RuntimeError, ValueError) as e:
                print(f"poll failed: {e}", flush=True)
                time.sleep(wait)
                continue
            if codes != done:
                same = 0
                while same < min(len(codes), len(done)) and codes[same] == done[same]:
                    same += 1
                for k in range(same + 1, len(codes) + 1):
                    idx = plays[k - 1]["about"]["atBatIndex"]
                    try:
                        b = run_bend(args.depth, seed_for(k), away_cum, home_cum, codes[:k], args.mode)
                    except BendError as e:
                        print(f"#{idx} bend error: {e}", flush=True)
                        continue
                    book.add(idx, b, plays[k - 1], wp.get(idx))
                done = codes
            book.backfill(wp)
            book.write()
            if state == "Final":
                b = run_bend(args.depth, seed_for(len(codes)), away_cum, home_cum, codes, args.mode)
                book.final(b["home_runs"] > b["away_runs"])
                box_check(src.get("box"), src.get("linescore"), b)
                book.backfill(wp_map(src.get("wp")))
                book.write()
                book.summary()
                return 0
            time.sleep(wait)
    except KeyboardInterrupt:
        book.write()
        print("stopped; csv written", flush=True)
        return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pk", type=int, default=849805, help="MLB gamePk (default: WS Game 1)")
    ap.add_argument("--replay", action="store_true", help="replay a finished game from fixtures")
    ap.add_argument("--depth", type=int, help="2^depth simulated games (default 20 live, 16 replay)")
    ap.add_argument("--mode", choices=("cpu", "gpu"), default=DEFAULT_MODE)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-serve", action="store_true", help="live: do not start the chart server")
    args = ap.parse_args()
    if args.depth is None:
        args.depth = 16 if args.replay else 20
    sys.exit(replay(args) if args.replay else live(args))


if __name__ == "__main__":
    main()
