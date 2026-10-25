#!/usr/bin/env python3
"""Bend vs MLB live win probability.

The host shell around ./wp (main.bend): fetches MLB Stats API data, encodes
every completed play as a 4-char code, runs Bend on the whole play list,
and prints Bend's home win probability next to MLB's. Bend owns the
scorebook and the simulation; this file owns HTTP, JSON, CSV and the chart.
Prediction-market prices (markets.py: Kalshi, Polymarket, Polymarket US)
are read beside both, per play.

  python3 live.py                       # live, World Series Game 1
  python3 live.py --publish             # ... and push every update to the hosted page
  python3 live.py --pk 849805 --replay  # rehearse a finished game
  python3 live.py --no-markets          # Bend and MLB only

--publish reads WP_PUSH_URL and WP_PUSH_TOKEN from the environment or ./.env.
"""

import argparse
import csv
import functools
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import markets

ROOT = Path(__file__).resolve().parent
API = "https://statsapi.mlb.com/api"
URLS = {
    "status": API + "/v1.1/game/{pk}/feed/live?fields=metaData,wait,gameData,status,"
    "abstractGameState,detailedState,teams,away,home,id,abbreviation,teamName",
    "plays": API + "/v1/game/{pk}/playByPlay?fields=allPlays,result,eventType,awayScore,"
    "homeScore,about,atBatIndex,inning,isTopInning,isComplete,count,outs,runners,movement,"
    "originBase,start,end,isOut,details,runner,matchup,postOnFirst,postOnSecond,postOnThird,id",
    "wp": API + "/v1/game/{pk}/winProbability?fields=atBatIndex,homeTeamWinProbability",
    "box": API + "/v1/game/{pk}/boxscore?fields=teams,away,home,teamStats,batting,fielding,"
    "atBats,baseOnBalls,hitByPitch,sacBunts,sacFlies,catchersInterference,runs,putOuts",
    "linescore": API + "/v1/game/{pk}/linescore?fields=teams,home,away,runs,leftOnBase",
    "asof": API + "/v1/teams/{id}/stats?stats=byDateRange&group=pitching&season={season}"
    "&startDate={season}-01-01&endDate={end}&gameType=R",
    "starter": API + "/v1/people/{id}/stats?stats=byDateRange&group=pitching&season={season}"
    "&startDate={season}-01-01&endDate={end}&gameType=R",
    "schedule": API + "/v1/schedule?gamePk={pk}&hydrate=probablePitcher&fields=dates,games,gamePk,"
    "gameDate,officialDate,gameType,teams,away,home,probablePitcher,id",
    "scoring": API + "/v1/game/{pk}/playByPlay?fields=allPlays,about,atBatIndex,startTime,endTime,"
    "isComplete,result,event,eventType,description,matchup,batter,id,fullName,runners,details,"
    "runner,credits,position,code,credit",
}

TEAM_NAMES = {
    119: "Los Angeles Dodgers",
    139: "Tampa Bay Rays",
    158: "Milwaukee Brewers",
}

# A game is played against the previous season's norms: the league's per-plate-appearance rates,
# and each outcome's home or away rate over its overall rate (Stats API teams/stats, season totals
# and statSplits sitCodes=h,a, regular season).
NORMS = {
    # 2025: 182,926 PA; 89,470 home, 93,456 away
    2025: {"league": {"K": .2222, "O": .4638, "W": .0946, "S": .1428, "D": .0423, "T": .0034, "H": .0309},
           "home": {"K": .976, "O": 1.0015, "W": 1.0277, "S": 1.0072, "D": 1.0121, "T": 1.0874, "H": 1.006},
           "away": {"K": 1.023, "O": .9986, "W": .9735, "S": .9931, "D": .9884, "T": .9163, "H": .9943}},
    # 2024: 182,449 PA; 89,100 home, 93,349 away
    2024: {"league": {"K": .2258, "O": .463, "W": .0929, "S": .142, "D": .0426, "T": .0038, "H": .0299},
           "home": {"K": .9821, "O": 1.0021, "W": 1.0289, "S": .9929, "D": 1.0111, "T": 1.0312, "H": 1.0274},
           "away": {"K": 1.0171, "O": .998, "W": .9725, "S": 1.0067, "D": .9894, "T": .9702, "H": .9738}},
}
# Chosen on the development games (tune.py), never on the benchmark's test games: a team's
# pitching to date, shrunk toward the league by PITCH_PRIOR batters faced; the probable
# starter's to date, shrunk toward his team's by STARTER_PRIOR, weighted by the batters he is
# expected to face (his batters per start to date, shrunk toward STARTER_BF by STARTER_STARTS
# starts) out of PA_GAME. Team batting to date did not predict results there, so a side bats
# at the league's rates against the other side's pitching.
PITCH_PRIOR = 2000
STARTER_PRIOR = 600
STARTER_BF, STARTER_STARTS, PA_GAME = 22.0, 5, 38.0
ORDER = "KOWSDTH"
DEFAULT_MODE = "gpu"  # RTX 4070 Ti: 2^20 games 0.09 s (gpu) vs 0.15 s (24 threads)
CSV_HEADER = ["wall_time", "at_bat_index", "inning", "half", "outs", "bases", "code", "batter",
              "play", "away_runs", "home_runs", "bend_home_wp", "mlb_home_wp", *markets.COLUMNS,
              "delta", "sims", "unfinished", "seconds", "mode", "state_check"]


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

    def __init__(self, pk, cache, allow_fetch=True, root=None):
        self.pk = pk
        self.allow_fetch = allow_fetch
        self.dir = (root or ROOT / "fixtures") / str(pk) if cache else None

    def get(self, name, **kw):
        url = URLS[name.split("_")[0]].format(pk=self.pk, **kw)
        if self.dir is None:
            return fetch(url)
        path = self.dir / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text())
        if not self.allow_fetch:
            raise FileNotFoundError(f"missing fixture {path}; rerun with --fetch to download it")
        data = fetch(url)
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1))
        return data

    def optional(self, name, **kw):
        """Like get, but None when the fixture is missing and fetching is off."""
        try:
            return self.get(name, **kw)
        except FileNotFoundError:
            return None


# Plays
# -----

def _layout(before, slots):
    """Return the first origin/destination collision, or None when valid."""
    remaining = set(before)
    for origin, code in slots.items():
        if code != "-" and origin is not None:
            if origin not in remaining:
                return "origin", origin
            remaining.remove(origin)
    for origin in (3, 2, 1, None):
        code = slots.get(origin, "-")
        if code in "123":
            destination = int(code)
            if destination in remaining:
                return "destination", destination
            remaining.add(destination)
    return None


def _repair_forced(before, slots):
    """Recover omitted forced advancements using the preceding base state.

    MLB sometimes omits a runner who was forced to advance, especially on an
    inning-ending force. Only a landing collision can trigger this repair:
    an unmoved runner blocking first or second is shifted to the next base,
    then the layout is checked again. Other invalid layouts are left alone so
    Bend reports them instead of hiding a data problem.
    """
    slots = dict(slots)
    for _ in range(3):
        problem = _layout(before, slots)
        if problem is None:
            break
        kind, base = problem
        if kind != "destination" or base not in (1, 2) or base not in before:
            break
        if slots.get(base, "-") != "-":
            break
        slots[base] = str(base + 1)
    return slots


def encode_play(play, before=()):
    """Encode one completed play as slots r3 r2 r1 batter: - X R 1 2 3.

    Runner segments are grouped by runner id and ordered by playIndex. The
    first segment's start is the runner's origin and the last segment's end
    is the destination; out and score retain precedence. `before` is the
    preceding play's occupied bases and enables forced-runner recovery.
    """
    i = play["about"]["atBatIndex"]
    by_runner = {}
    for position, runner in enumerate(play.get("runners", [])):
        rid = runner.get("details", {}).get("runner", {}).get("id")
        if rid is None:
            raise ValueError(f"runner without id at atBatIndex {i}")
        details = runner.get("details", {})
        by_runner.setdefault(rid, []).append(
            (details.get("playIndex", position), position, runner["movement"]))
    slots = {}
    for rid, entries in by_runner.items():
        entries.sort(key=lambda entry: (entry[0] is None, entry[0], entry[1]))
        segs = [entry[2] for entry in entries]
        origin = segs[0].get("start")
        if origin is None and segs[0].get("originBase") is not None:
            origin = segs[0]["originBase"]
        if origin not in ("3B", "2B", "1B", None):
            raise ValueError(f"unknown origin {origin!r} at atBatIndex {i}")
        if origin in slots:
            raise ValueError(f"two runners from {origin or 'the batter'} at atBatIndex {i}")
        if any(s.get("isOut") for s in segs):
            slots[origin] = "X"
        elif any(s.get("end") == "score" for s in segs):
            slots[origin] = "R"
        else:
            end = segs[-1].get("end")
            if end not in ("1B", "2B", "3B"):
                raise ValueError(f"runner {rid}: unknown end {end!r} at atBatIndex {i}")
            slots[origin] = end[0]
    numeric_slots = {(None if origin is None else int(origin[0])): code
                     for origin, code in slots.items()}
    slots = _repair_forced(before, numeric_slots)
    return "".join(slots.get(origin, "-") for origin in (3, 2, 1, None))


def bases_after(play):
    """The bases occupied after a completed play, for the next encoding."""
    if play.get("count", {}).get("outs") == 3:
        return set()
    matchup = play.get("matchup", {})
    return {base for base, key in ((1, "postOnFirst"), (2, "postOnSecond"), (3, "postOnThird"))
            if key in matchup}


def encode_plays(plays, ghost=False):
    """Encode a complete play list, carrying base state between plays (with `ghost`, each
    half from the tenth inning on starts with the automatic runner on second)."""
    codes, before, half = [], set(), None
    for play in plays:
        about = play["about"]
        if (about.get("inning"), about.get("isTopInning")) != half:
            half = (about.get("inning"), about.get("isTopInning"))
            before = {2} if ghost and (about.get("inning") or 0) >= 10 else set()
        codes.append(encode_play(play, before))
        before = bases_after(play)
    return codes


def automatic_runners(plays):
    """{side: extra-inning halves batted}: one automatic runner each under the regular-season rule."""
    halves = {(p["about"]["inning"], p["about"]["isTopInning"]) for p in plays if p["about"]["inning"] >= 10}
    return {"away": sum(top for _, top in halves), "home": sum(not top for _, top in halves)}


def complete_plays(pbp):
    return [p for p in pbp.get("allPlays", []) if p.get("about", {}).get("isComplete")]


# Scorer's notation
# -----------------
# What a scorekeeper writes in the batter's box, from the MLB play: hits and walks
# by name, strikeouts as K (Kc: called, drawn as a backwards K), outs as the fielders
# who handled the ball (6-3, F8, 3U), double plays as the whole relay (6-4-3 DP).

HITS = {"single": "1B", "double": "2B", "triple": "3B", "home_run": "HR"}
NAMED = {"walk": "BB", "intent_walk": "IBB", "hit_by_pitch": "HBP", "catcher_interf": "CI",
         "fielders_choice": "FC", "fielders_choice_out": "FC", "force_out": "FC",
         "triple_play": "TP", "strikeout_double_play": "K DP"}
DOUBLE_PLAYS = {"grounded_into_double_play": "", "double_play": "", "sac_fly_double_play": "SF ",
                "sac_bunt_double_play": "SAC "}
FLY_WORDS = (("flies", "F"), ("lines", "L"), ("pops", "P"))
RUNNER_PLAYS = (("pickoff_caught_stealing", "POCS"), ("caught_stealing", "CS"), ("pickoff", "PO"),
                ("stolen_base", "SB"), ("wild_pitch", "WP"), ("passed_ball", "PB"), ("balk", "BK"))
SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV"}


def last_name(full):
    words = [w for w in (full or "").split() if w not in SUFFIXES]
    return words[-1] if words else ""


def relay(runners):
    """Fielders who assisted and put out, in order, a fielder repeating in a row once."""
    out = []
    for r in runners:
        for c in r.get("credits", []):
            pos = (c.get("position") or {}).get("code")
            if c.get("credit") in ("f_assist", "f_putout") and pos and (not out or out[-1] != pos):
                out.append(pos)
    return out


def notation(play):
    result = play.get("result", {})
    kind, desc = result.get("eventType", ""), result.get("description", "").lower()
    runners = play.get("runners", [])
    batter = play.get("matchup", {}).get("batter", {}).get("id")
    own = relay([r for r in runners if r.get("details", {}).get("runner", {}).get("id") == batter])
    if kind in HITS:
        return HITS[kind]
    if kind == "strikeout":
        return "Kc" if "called out on strikes" in desc else "K"
    if kind in NAMED:
        return NAMED[kind]
    if kind in DOUBLE_PLAYS:
        return f"{DOUBLE_PLAYS[kind]}{'-'.join(relay(runners))} DP".strip()
    if kind == "field_error":
        pos = next(((c.get("position") or {}).get("code") for r in runners for c in r.get("credits", [])
                    if "error" in c.get("credit", "")), "")
        return f"E{pos}"
    if kind == "sac_fly":
        return f"SF{own[-1] if own else ''}"
    if kind == "sac_bunt":
        return f"SAC {'-'.join(own)}".strip()
    if kind == "field_out" and len(own) == 1:
        letter = next((l for word, l in FLY_WORDS if word in desc), None)
        return f"{letter}{own[0]}" if letter else f"{own[0]}U"
    if kind == "field_out" and own:
        return "-".join(own)
    return next((abbr for prefix, abbr in RUNNER_PLAYS if kind.startswith(prefix)), result.get("event", ""))


def scorecard(scoring):
    """{at_bat_index: {"batter": last name, "play": notation}} for every completed play."""
    return {p["about"]["atBatIndex"]: {
        "batter": last_name(p.get("matchup", {}).get("batter", {}).get("fullName")),
        "play": notation(p)} for p in complete_plays(scoring or {})}


def check_state(b, play, ghost=False):
    """Field names where Bend's state after `play` differs from MLB's."""
    bad = []
    res, about, outs = play["result"], play["about"], play["count"]["outs"]
    if b["away_runs"] != res["awayScore"]:
        bad.append("away_runs")
    if b["home_runs"] != res["homeScore"]:
        bad.append("home_runs")
    top = about["isTopInning"]
    if outs == 3:
        inning = about["inning"] + (0 if top else 1)
        goes_on = top or res["awayScore"] == res["homeScore"]
        want = (inning, not top, 0, "-2-" if ghost and inning >= 10 and goes_on else "---")
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

def counts(stat):
    """(batters faced, {outcome: count}) from a pitching line; (0, zeros) for None."""
    if stat is None:
        return 0, dict.fromkeys(ORDER, 0)
    d, t, h = stat["doubles"], stat["triples"], stat["homeRuns"]
    n = {"K": stat["strikeOuts"], "W": stat["baseOnBalls"] + stat["hitBatsmen"],
         "S": stat["hits"] - d - t - h, "D": d, "T": t, "H": h}
    n["O"] = stat["battersFaced"] - sum(n.values())
    return stat["battersFaced"], n


def shrunk(stat, toward, prior):
    """Per-batter outcome rates allowed, shrunk toward `toward` by `prior` batters."""
    bf, n = counts(stat)
    return {e: (n[e] + prior * toward[e]) / (bf + prior) for e in ORDER}


def team_stat(ts, group):
    """The group's stat line, or None before the first game of the range."""
    for st in ts["stats"]:
        if st["group"]["displayName"] == group:
            return st["splits"][0]["stat"] if st["splits"] else None
    raise ValueError(f"no {group} stats")


def starter_share(stat):
    """The share of a game's batters the starter is expected to face."""
    starts = (stat or {}).get("gamesStarted", 0)
    per = min(stat["battersFaced"] / starts, 30.0) if starts else STARTER_BF
    return min(1.0, (starts * per + STARTER_STARTS * STARTER_BF) / (starts + STARTER_STARTS) / PA_GAME)


def venue(p, factor):
    """Rates scaled by home or away factors, renormalised."""
    w = {e: p[e] * factor[e] for e in ORDER}
    tot = sum(w.values())
    return {e: w[e] / tot for e in ORDER}


def cumulative(p):
    acc, out = 0.0, []
    for e in ORDER:
        acc += p[e]
        out.append(round(10000 * acc))
    out[-1] = 10000
    return out


def scheduled(src):
    return src.get("schedule")["dates"][0]["games"][0]


def automatic_runner(src):
    """Regular-season extra innings start with a runner on second; the postseason's do not."""
    return scheduled(src)["gameType"] == "R"


def norms(season):
    return NORMS[int(season) - 1]


def game_rates(src, teams):
    """(awayCum, homeCum): each side bats at last season's league rates against the other side's
    pitching through the day before the game (team and probable starter), adjusted for
    home/away."""
    game = scheduled(src)
    season = game["officialDate"][:4]
    end = (date.fromisoformat(game["officialDate"]) - timedelta(days=1)).isoformat()
    norm = norms(season)
    pit = {}
    for s in ("away", "home"):
        team = shrunk(team_stat(src.get(f"asof_{teams[s]['id']}", id=teams[s]["id"], season=season, end=end),
                                "pitching"), norm["league"], PITCH_PRIOR)
        sp = game["teams"][s].get("probablePitcher", {}).get("id")
        if sp is None:
            pit[s] = team
            continue
        st = team_stat(src.get(f"starter_{sp}", id=sp, season=season, end=end), "pitching")
        w = starter_share(st)
        own = shrunk(st, team, STARTER_PRIOR)
        pit[s] = {e: w * own[e] + (1 - w) * team[e] for e in ORDER}
    return cumulative(venue(pit["home"], norm["away"])), cumulative(venue(pit["away"], norm["home"]))


# Bend
# ----

def run_bend(depth, seed, away_cum, home_cum, codes, mode, ghost=False):
    arg = "|".join([str(depth), str(seed), ",".join(map(str, away_cum)),
                    ",".join(map(str, home_cum)), ";".join(codes), mode, "1" if ghost else "0"])
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


def load_env():
    """WP_* settings: ./.env (KEY=VALUE lines), overridden by the environment."""
    vals = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip().startswith("WP_"):
                vals[key.strip()] = value.strip()
    vals.update({k: v for k, v in os.environ.items() if k.startswith("WP_")})
    return vals


class Publisher:
    """POSTs the CSV and teams to the Cloudflare Worker (cloudflare/worker.js) when they change."""

    def __init__(self, url, token):
        self.url, self.token = url.rstrip("/"), token
        self.last = None

    def push(self, pk, meta, csv_text):
        body = json.dumps({"meta": meta, "csv": csv_text})
        if body == self.last:
            return True
        req = urllib.request.Request(
            f"{self.url}/push/{pk}", method="POST",
            data=body.encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                     "User-Agent": "bend-winprob/1"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=10):
                    pass
                self.last = body
                return True
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    print(f"publish failed after 3 attempts: {e}", flush=True)
        return False


# Rows, ticker, CSV
# -----------------

class Book:
    """Rows keyed by at_bat_index (-1: pregame), rewritten to runs/<pk>.csv (and published)."""

    def __init__(self, pk, away, home, depth, mode, publisher=None, verbose=True, team_info=None, ghost=False):
        self.pk, self.away, self.home, self.depth, self.mode = pk, away, home, depth, mode
        self.publisher = publisher
        self.verbose = verbose
        self.ghost = ghost
        self.rows = {}
        runs = ROOT / "runs"
        runs.mkdir(exist_ok=True)
        self.csv = runs / f"{pk}.csv"
        self.meta_path = runs / f"{pk}-meta.json"
        self.meta = {"pk": pk, "away": away, "home": home}
        if team_info is not None:
            for side in ("away", "home"):
                self.meta[f"{side}_name"] = team_info[side]["name"]
                self.meta[f"{side}_logo"] = team_info[side]["logo"]
        self.meta_path.write_text(json.dumps(self.meta))
        self.tape, self.samples = markets.Tape(), {}
        self.notes = {}  # at_bat_index -> {"batter", "play"}: scorecard()

    def add(self, idx, b, play, mlb, code=""):
        bad = check_state(b, play, self.ghost) if play is not None else []
        if b["rejected"] > 0 and "rejected" not in bad:
            bad.append("rejected")
        decided = b["home_wins"] + b["away_wins"]
        bend = 100.0 * b["home_wins"] / decided if decided else None
        check = "ok" if not bad else "MISMATCH(" + ",".join(bad) + ")"
        self.rows[idx] = {
            "wall_time": time.strftime("%Y-%m-%dT%H:%M:%S"), "at_bat_index": idx,
            "inning": b["inning"], "half": "T" if b["top"] else "B", "outs": b["outs"],
            "bases": b["bases"], "code": code, "batter": "", "play": "",
            "away_runs": b["away_runs"], "home_runs": b["home_runs"],
            "bend_home_wp": "" if bend is None else round(bend, 2),
            "mlb_home_wp": "" if mlb is None else round(mlb, 2), "delta": "",
            "sims": 2 ** self.depth, "unfinished": b["unfinished"],
            "seconds": round(b["seconds"], 3), "mode": self.mode, "state_check": check,
        }
        self.fill_notes(idx)
        self.fill_markets(idx)
        self.fill_delta(idx)
        if self.verbose:
            self.print_row(idx)
        return self.rows[idx]

    def prune(self, valid_indices):
        """Drop rows removed or replaced by a replay-review correction."""
        valid = set(valid_indices)
        for idx in list(self.rows):
            if idx >= 0 and idx not in valid:
                del self.rows[idx]

    def mismatch_count(self):
        return sum(row["state_check"] != "ok" for row in self.rows.values())

    def fill_delta(self, idx):
        r = self.rows[idx]
        r["delta"] = "" if r["bend_home_wp"] == "" or r["mlb_home_wp"] == "" \
            else round(r["bend_home_wp"] - r["mlb_home_wp"], 2)

    def backfill(self, wp):
        """Refresh MLB WP, including revisions to earlier at-bats."""
        for idx, r in self.rows.items():
            if idx in wp:
                value = round(wp[idx], 2)
                if r["mlb_home_wp"] != value:
                    r["mlb_home_wp"] = value
                    self.fill_delta(idx)

    def fill_notes(self, idx):
        note = self.notes.get(idx, {})
        self.rows[idx]["batter"], self.rows[idx]["play"] = note.get("batter", ""), note.get("play", "")

    def set_scoring(self, notes):
        """Write each play's batter and the scorer's notation (`scorecard`) into its row."""
        self.notes = notes
        for idx in self.rows:
            self.fill_notes(idx)

    def fill_markets(self, idx):
        r = self.rows[idx]
        for key, col in zip(markets.KEYS, markets.COLUMNS):
            p = self.tape.at(key, *self.samples[idx]) if idx in self.samples else None
            r[col] = "" if p is None else round(p, 2)

    def set_markets(self, tape, samples, listings):
        """Read every row's market prices from `tape` at its instant in `samples`."""
        self.tape, self.samples = tape, samples
        for idx in self.rows:
            self.fill_markets(idx)
        if listings and listings != self.meta.get("markets"):
            self.meta["markets"] = listings
            self.meta_path.write_text(json.dumps(self.meta))

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
        if self.publisher is not None:
            return self.publisher.push(self.pk, self.meta, self.csv.read_text())
        return True

    def final(self, home_won):
        last = max(self.rows)
        r = self.rows[last]
        r["bend_home_wp"], r["sims"] = (100.0 if home_won else 0.0), 0
        self.fill_delta(last)

    def summary(self):
        deltas = [abs(r["delta"]) for r in self.rows.values() if r["delta"] != ""]
        mean = sum(deltas) / len(deltas) if deltas else float("nan")
        venues = ""
        for key, col in zip(markets.KEYS, markets.COLUMNS):
            gaps = [abs(r["bend_home_wp"] - r[col]) for r in self.rows.values()
                    if r["bend_home_wp"] != "" and r[col] != ""]
            if gaps:
                venues += f" | Bend-{key} {sum(gaps) / len(gaps):.2f} over {len(gaps)}"
        print(f"SUMMARY rows {len(self.rows)} mean |Δ| {mean:.2f} over {len(deltas)} "
              f"mismatches {self.mismatch_count()}{venues}", flush=True)
        return mean


def wp_map(wp):
    return {e["atBatIndex"]: e["homeTeamWinProbability"] for e in wp
            if "homeTeamWinProbability" in e}


def box_check(box, ls, b, auto=None):
    """OBR 9.03(c) on the official box score, and Bend's scorebook against it. `auto` counts each
    side's automatic runners: they score, are stranded or put out without batting, and Bend
    places each by a play whose batter goes to second."""
    ok = True
    for side, opp, at in (("away", "home", 0), ("home", "away", 4)):
        bat = box["teams"][side]["teamStats"]["batting"]
        supply = (bat["atBats"] + bat["baseOnBalls"] + bat["hitByPitch"] + bat["sacBunts"]
                  + bat["sacFlies"] + bat.get("catchersInterference", 0))
        a = (auto or {}).get(side, 0)
        runs, lob = ls["teams"][side]["runs"], ls["teams"][side]["leftOnBase"]
        po = box["teams"][opp]["teamStats"]["fielding"]["putOuts"]
        b_bat, b_runs, b_outs, b_lob = b["line"][at:at + 4]
        batting_now = b["top"] == (side == "away")
        b_lob += (3 - b["bases"].count("-")) if batting_now else 0
        good = (supply + a == runs + lob + po
                and (b_bat, b_runs, b_lob, b_outs) == (supply + a, runs, lob, po))
        ok &= good
        extra = f"+{a}" if a else ""
        print(f"BOX {side} official {supply}{extra}={runs}+{lob}+{po} "
              f"bend {b_bat}={b_runs}+{b_lob}+{b_outs} {'OK' if good else 'FAIL'}", flush=True)
    return ok


# Modes
# -----

def teams_of(status):
    t = status["gameData"]["teams"]
    result = {}
    for side in ("away", "home"):
        team = t[side]
        team_id = team["id"]
        abbr = team["abbreviation"]
        result[side] = {
            "id": team_id,
            "abbr": abbr,
            "name": team.get("teamName") or TEAM_NAMES.get(team_id, abbr),
            "logo": f"https://www.mlbstatic.com/team-logos/{team_id}.svg",
        }
    return result


def replay(args):
    # Lazy import avoids a cycle: sim_engine reuses this module's host helpers.
    from sim_engine import ReplayEngine
    engine = ReplayEngine(args.pk, depth=args.depth, mode=args.mode,
                          publisher=args.publisher, fetch=True, verbose=True)
    return engine.run()


def serve(port):
    """The hosted layout on localhost, as the Worker serves it: web/ at "/" and the CSV and meta
    this harness writes to runs/ under /runs/<file>. Returns the chart's base URL."""
    web, runs = ROOT / "web", ROOT / "runs"

    class Local(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if path.startswith("/runs/"):   # a file directly in runs/, never a path out of it
                target = (runs / urllib.parse.unquote(path.split("?", 1)[0].split("#", 1)[0])[len("/runs/"):]).resolve()
                return str(target if target.parent == runs.resolve() else runs / ".refused" / ".refused")
            return super().translate_path(path)

        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Local, directory=str(web)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/"


def live_setup(src, pk):
    """Fetch initial game/team data; called again after transient failures."""
    status = src.get("status")
    teams = teams_of(status)
    rates_path = ROOT / "runs" / f"{pk}-rates.json"
    (ROOT / "runs").mkdir(exist_ok=True)
    rates = json.loads(rates_path.read_text()) if rates_path.exists() else {}
    if "ghost" not in rates:
        away_cum, home_cum = game_rates(src, teams)
        rates = {"away": away_cum, "home": home_cum, "ghost": automatic_runner(src)}
        rates_path.write_text(json.dumps(rates))
    return teams, rates["away"], rates["home"], rates["ghost"]


def read_scoring(src, book, feed, started):
    """Per poll: each play's batter and notation, and with a market feed every row's prices.

    Before first pitch there is no play to score; the pregame row reads the latest
    market price. A failed fetch keeps the rows as they were.
    """
    if feed is not None:
        feed.poll()
    try:
        scoring = src.get("scoring") if started else {}
    except (RuntimeError, ValueError) as e:
        print(f"scoring poll failed: {e}", flush=True)
        return
    book.set_scoring(scorecard(scoring))
    if feed is not None:
        book.set_markets(feed.tape, markets.sample_times(scoring), feed.listings())


def live(args):
    src = Source(args.pk, cache=False)
    if not args.no_serve:
        print(f"chart: {serve(args.port)}?pk={args.pk}", flush=True)
    while True:
        try:
            teams, away_cum, home_cum, ghost = live_setup(src, args.pk)
            game = None if args.no_markets else markets.game_of(src.get("schedule"), teams)
            break
        except (RuntimeError, ValueError, KeyError, IndexError) as e:
            print(f"initialization failed: {e}; retrying in 10s", flush=True)
            time.sleep(10)
    away, home = teams["away"]["abbr"], teams["home"]["abbr"]
    print(f"{away} @ {home}  awayCum {away_cum}  homeCum {home_cum}  depth {args.depth}  {args.mode}",
          flush=True)
    book = Book(args.pk, away, home, args.depth, args.mode, args.publisher, team_info=teams, ghost=ghost)
    feed = None if game is None else markets.LiveFeed(game)
    done = []  # codes whose complete suffix succeeded
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
                    book.add(-1, run_bend(args.depth, seed_for(0), away_cum, home_cum, [], args.mode, ghost),
                             None, None)
                    book.write()
                except BendError as e:
                    print(f"#pre bend error: {e}", flush=True)
            if state == "Preview":
                read_scoring(src, book, feed, False)
                if -1 in book.rows:
                    book.write()  # also retries a failed pregame publish
                if time.time() - last_wait >= 60:
                    print(f"waiting: {detailed}", flush=True)
                    last_wait = time.time()
                time.sleep(wait)
                continue
            try:
                plays = complete_plays(src.get("plays"))
                codes = encode_plays(plays, ghost)
                wp = wp_map(src.get("wp"))
            except (RuntimeError, ValueError) as e:
                print(f"poll failed: {e}", flush=True)
                time.sleep(wait)
                continue
            if codes != done:
                same = 0
                while same < min(len(codes), len(done)) and codes[same] == done[same]:
                    same += 1
                book.prune(play["about"]["atBatIndex"] for play in plays)
                complete = True
                for k in range(same + 1, len(codes) + 1):
                    idx = plays[k - 1]["about"]["atBatIndex"]
                    try:
                        b = run_bend(args.depth, seed_for(k), away_cum, home_cum, codes[:k], args.mode, ghost)
                    except BendError as e:
                        complete = False
                        print(f"#{idx} bend error: {e}; will retry", flush=True)
                        break
                    book.add(idx, b, plays[k - 1], wp.get(idx), codes[k - 1])
                if complete:
                    done = codes
            read_scoring(src, book, feed, True)
            book.backfill(wp)
            book.write()
            if state == "Final":
                try:
                    b = run_bend(args.depth, seed_for(len(codes)), away_cum, home_cum, codes, args.mode, ghost)
                    book.final(b["home_runs"] > b["away_runs"])
                    box_ok = box_check(src.get("box"), src.get("linescore"), b,
                                       automatic_runners(plays) if ghost else None)
                    book.backfill(wp_map(src.get("wp")))
                    if feed is not None:
                        feed.catch_up(max((t for t, _ in book.samples.values() if t is not None), default=0))
                    read_scoring(src, book, feed, True)
                    published = book.write()
                    book.summary()
                    return 0 if box_ok and book.mismatch_count() == 0 and published else 1
                except (BendError, RuntimeError, ValueError) as e:
                    print(f"finalization failed: {e}; retrying", flush=True)
                    time.sleep(wait)
                    continue
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
    ap.add_argument("--no-markets", action="store_true", help="live: skip prediction-market prices")
    ap.add_argument("--publish", action="store_true",
                    help="push every update to the hosted page (WP_PUSH_URL, WP_PUSH_TOKEN)")
    args = ap.parse_args()
    if args.depth is None:
        args.depth = 16 if args.replay else 20
    if args.depth < 0:
        ap.error("--depth must be nonnegative")
    args.publisher = None
    if args.publish:
        env = load_env()
        if not env.get("WP_PUSH_URL") or not env.get("WP_PUSH_TOKEN"):
            sys.exit("--publish needs WP_PUSH_URL and WP_PUSH_TOKEN (environment or .env)")
        args.publisher = Publisher(env["WP_PUSH_URL"], env["WP_PUSH_TOKEN"])
        print(f"publishing: {env['WP_PUSH_URL'].rstrip('/')}/?pk={args.pk}", flush=True)
    sys.exit(replay(args) if args.replay else live(args))


if __name__ == "__main__":
    main()
