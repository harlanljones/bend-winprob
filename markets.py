"""Prediction-market home win probabilities, beside Bend's and MLB's.

Three venues list a game-winner contract for every MLB game and publish
market data without credentials:

  kalshi         Kalshi, series KXMLBGAME: one Yes/No market per team
  polymarket     Polymarket (international order book): one market, a token per team
  polymarket_us  Polymarket US: one market whose long side is one of the teams

Each market is found from the game's scheduled first pitch and the two MLB
abbreviations, and read as the home team's win probability in percent: the
midpoint of best bid and best ask (Polymarket: its own displayed price; Kalshi:
the home and away markets' midpoints normalised to sum to 100). Prices are kept
as a Tape of (unix seconds, percent) observations, minute history plus live
quotes, and every CSV row reads the tape at one instant (`sample_times`).

Not included: Novig (API keys; its read-only GraphQL is being retired),
ProphetX and Betfair (credentials), Smarkets (its API refuses non-browser
clients), Manifold (no per-game markets).
"""

import bisect
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

AGENT = "bend-winprob/1"  # Polymarket's CDN refuses a bare browser User-Agent from a script
LAG = 60                  # a play's price is read this many seconds after it ended...
STALE = 300               # ...from an observation at most this old (history can skip minutes)
MARGIN = 3600             # history starts an hour before the scheduled first pitch
TAIL = 1800               # recordings run half an hour past the last play
MAX_SPREAD = 0.10         # a wider book says nothing about the price
REFRESH = 300             # live: seconds between market searches and history reloads
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
ET = ZoneInfo("America/New_York")


def get(url):
    """JSON from `url`; None for 404 (not listed). Two attempts, short timeout."""
    last = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # network or JSON failure: retry once
            last = e
        if attempt == 0:
            time.sleep(1)
    raise RuntimeError(f"fetch failed: {url}: {last}")


def stamp(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def mid(bid, ask):
    """Midpoint of a two-sided book in [0, 1], or None when one-sided or too wide."""
    if bid is None or ask is None:
        return None
    bid, ask = float(bid), float(ask)
    if not 0.0 <= bid <= ask <= 1.0 or ask - bid > MAX_SPREAD or (bid == 0.0 and ask == 1.0):
        return None
    return (bid + ask) / 2


def game_of(schedule, teams):
    """The facts every venue searches by: MLB abbreviations, scheduled first pitch, official date."""
    g = schedule["dates"][0]["games"][0]
    return {"away": teams["away"]["abbr"], "home": teams["home"]["abbr"],
            "start": stamp(g["gameDate"]), "date": g["officialDate"]}


# Venues
# ------
# find(game) -> listing dict (key, name, url, id + venue fields) or None when not listed
# history(listing, t0, t1) -> [(ts, home % or None)]   quote(listing) -> home % or None
# None is an observation too: the book was one-sided or too wide to give a price.

class Kalshi:
    key, name = "kalshi", "Kalshi"
    API = "https://api.elections.kalshi.com/trade-api/v2"

    def find(self, game):
        d = datetime.fromtimestamp(game["start"], ET)
        event = f"KXMLBGAME-{d:%y}{MONTHS[d.month - 1]}{d:%d%H%M}{game['away']}{game['home']}"
        for base in ("/markets", "/historical/markets"):  # settled markets move to /historical
            markets = (get(f"{self.API}{base}?event_ticker={event}") or {}).get("markets", [])
            if markets:
                break
        teams = {m["ticker"].rsplit("-", 1)[1]: m["ticker"] for m in markets}
        if game["home"] not in teams or game["away"] not in teams:
            return None
        return {"key": self.key, "name": self.name, "id": event,
                "url": f"https://kalshi.com/markets/kxmlbgame/professional-baseball-game/{event.lower()}",
                "home_ticker": teams[game["home"]], "away_ticker": teams[game["away"]]}

    @staticmethod
    def devig(home, away):
        if home is not None and away is not None and home + away > 0:
            return 100.0 * home / (home + away)
        if home is not None:
            return 100.0 * home
        return None if away is None else 100.0 * (1.0 - away)

    def candles(self, ticker, t0, t1):
        query = f"start_ts={t0}&end_ts={t1}&period_interval=1"
        got = get(f"{self.API}/series/KXMLBGAME/markets/{ticker}/candlesticks?{query}")
        if got is None:
            got = get(f"{self.API}/historical/markets/{ticker}/candlesticks?{query}")
        out = {}
        for c in (got or {}).get("candlesticks", []):
            close = [(c.get(side) or {}).get("close_dollars", (c.get(side) or {}).get("close"))
                     for side in ("yes_bid", "yes_ask")]
            out[int(c["end_period_ts"])] = mid(*close)
        return out

    def history(self, listing, t0, t1):
        home = self.candles(listing["home_ticker"], t0, t1)
        away = self.candles(listing["away_ticker"], t0, t1)
        return [(ts, self.devig(home.get(ts), away.get(ts))) for ts in sorted(home.keys() | away.keys())]

    def quote(self, listing):
        markets = (get(f"{self.API}/markets?event_ticker={listing['id']}") or {}).get("markets", [])
        by = {m["ticker"]: mid(m.get("yes_bid_dollars"), m.get("yes_ask_dollars")) for m in markets}
        return self.devig(by.get(listing["home_ticker"]), by.get(listing["away_ticker"]))


class Polymarket:
    key, name = "polymarket", "Polymarket"
    GAMMA = "https://gamma-api.polymarket.com"
    CLOB = "https://clob.polymarket.com"
    ALIAS = {"AZ": "ari", "ATH": "oak"}  # Polymarket's abbreviations where MLB's differ

    def find(self, game):
        away, home = (self.ALIAS.get(t, t.lower()) for t in (game["away"], game["home"]))
        slug = f"mlb-{away}-{home}-{game['date']}"
        events = get(f"{self.GAMMA}/events?slug={slug}") or []
        if not events:
            return None
        event = events[0]
        market = next((m for m in event.get("markets", []) if m.get("slug") == slug), None)
        home_name = next((t.get("name") for t in event.get("teams", []) if t.get("ordering") == "home"), None)
        if market is None or home_name is None:
            return None
        outcomes, tokens = json.loads(market["outcomes"]), json.loads(market["clobTokenIds"])
        if home_name not in outcomes:
            return None
        return {"key": self.key, "name": self.name, "id": slug,
                "url": f"https://polymarket.com/event/{slug}", "token": tokens[outcomes.index(home_name)]}

    def history(self, listing, t0, t1):
        got = get(f"{self.CLOB}/prices-history?market={listing['token']}&startTs={t0}&endTs={t1}&fidelity=1")
        return [(int(h["t"]), 100.0 * float(h["p"])) for h in (got or {}).get("history", [])]

    def quote(self, listing):
        got = get(f"{self.CLOB}/midpoint?token_id={listing['token']}")  # 404 once the book closes
        return None if not got or got.get("mid") is None else 100.0 * float(got["mid"])


class PolymarketUS:
    key, name = "polymarket_us", "Polymarket US"
    API = "https://gateway.polymarket.us"

    def find(self, game):
        slug = f"aec-mlb-{game['away'].lower()}-{game['home'].lower()}-{game['date']}"
        got = get(f"{self.API}/v1/market/slug/{slug}")
        if not got:
            return None
        long = next((s for s in got["market"].get("marketSides", []) if s.get("long")), None)
        ordering = ((long or {}).get("team") or {}).get("ordering")
        if ordering not in ("home", "away"):
            return None
        return {"key": self.key, "name": self.name, "id": slug,
                "url": f"https://polymarket.us/event/{slug}", "long_home": ordering == "home"}

    def home(self, listing, long_mid):
        if long_mid is None:
            return None
        return 100.0 * (long_mid if listing["long_home"] else 1.0 - long_mid)

    def history(self, listing, t0, t1):
        got = get(f"{self.API}/v1/price-history?symbol={listing['id']}&timestamp.startTimestamp={t0}"
                  f"&timestamp.endTimestamp={t1}&fidelity=1")
        # longPrice is the best ask; shortPrice is one minus the best bid.
        return [(int(h["timestamp"]), self.home(listing, mid(1.0 - float(h["shortPrice"]), h["longPrice"])))
                for h in (got or {}).get("history", [])]

    def quote(self, listing):
        data = (get(f"{self.API}/v1/markets/{listing['id']}/bbo") or {}).get("marketData", {})
        bid, ask = ((data.get(k) or {}).get("value") for k in ("bestBid", "bestAsk"))
        return self.home(listing, mid(bid, ask))


VENUES = (Kalshi(), Polymarket(), PolymarketUS())
KEYS = tuple(v.key for v in VENUES)
COLUMNS = tuple(f"{k}_home_wp" for k in KEYS)


def public(listing):
    """The part of a listing the page shows."""
    return {k: listing[k] for k in ("key", "name", "url", "id")}


# Tape
# ----

class Tape:
    """Per venue: (ts, home % or None) observations in time order, and the instant they are complete to.

    Each venue's track is replaced as one tuple, so a reader on another thread never
    sees a half-updated track.
    """

    def __init__(self):
        self.tracks = {}

    def put(self, key, points, until):
        points = sorted(points, key=lambda p: p[0])
        self.tracks[key] = ([p[0] for p in points], [p[1] for p in points], until)

    def until(self, key):
        return self.tracks.get(key, ((), (), None))[2]

    def at(self, key, t, after=None):
        """Home % at instant t (None: the latest), from an observation taken after instant `after`.

        None when unknown, stale, not yet observed, or when the last observation by t
        predates `after` (for a play: a price from before the play happened).
        """
        if key not in self.tracks:
            return None
        stamps, values, until = self.tracks[key]
        t = until if t is None else t
        if t > until:
            return None
        i = bisect.bisect_right(stamps, t) - 1
        if i < 0 or t - stamps[i] > STALE or (after is not None and stamps[i] <= after):
            return None
        return values[i]


def sample_times(scoring):
    """{at_bat_index: (instant its market price is read, instant the price must postdate)}.

    A completed play reads LAG seconds after it ended, or when the next completed
    play ended if that came sooner, from an observation taken after it ended; the
    pregame row (-1) reads at the first play's start, or the latest observation
    (None) before the game begins.
    """
    plays = [p["about"] for p in (scoring or {}).get("allPlays", [])
             if p.get("about", {}).get("isComplete") and p["about"].get("endTime")]
    ends = [stamp(p["endTime"]) for p in plays]
    out = {-1: (stamp(plays[0]["startTime"]) if plays and plays[0].get("startTime") else None, None)}
    for k, p in enumerate(plays):
        t = ends[k] + LAG
        out[p["atBatIndex"]] = (min(t, ends[k + 1]) if k + 1 < len(ends) else t, ends[k])
    return out


# Recorded (replay) and live feeds
# --------------------------------

def record(game, t0, t1, venues=VENUES):
    """Find and fetch every venue's history over [t0, t1], in parallel. Raises on any fetch failure."""
    def one(v):
        listing = v.find(game)
        return v.key, None if listing is None else {"listing": listing, "points": v.history(listing, t0, t1)}

    with ThreadPoolExecutor(max_workers=len(venues)) as pool:
        return {"window": [t0, t1], "venues": dict(pool.map(one, venues))}


def tape_of(recording):
    tape, listings = Tape(), []
    t1 = recording["window"][1]
    for key in KEYS:
        got = recording["venues"].get(key)
        if got is not None:
            tape.put(key, [tuple(p) for p in got["points"]], t1)
            listings.append(public(got["listing"]))
    return tape, listings


def recorded(source, teams, scoring):
    """(tape, listings, samples) for a replay from fixtures/<pk>/markets.json.

    `scoring` is the game's play-by-play with each play's start and end time. The
    recording is fetched once when the source may fetch, then frozen like every
    other fixture; without one the market columns stay empty.
    """
    path = source.dir / "markets.json"
    if not path.exists() and not source.allow_fetch:
        return Tape(), [], {}
    if not path.exists():
        plays = [p["about"] for p in scoring.get("allPlays", []) if p.get("about", {}).get("endTime")]
        if not plays:
            return Tape(), [], {}
        game = game_of(source.get("schedule"), teams)
        t0 = min(game["start"], stamp(plays[0]["startTime"])) - MARGIN
        rec = record(game, t0, stamp(plays[-1]["endTime"]) + TAIL)
        path.write_text(json.dumps(rec, separators=(",", ":")))
    tape, listings = tape_of(json.loads(path.read_text()))
    return tape, listings, sample_times(scoring)


class LiveFeed:
    """Live tapes, refreshed in background threads so a slow venue never delays a Bend run.

    poll() starts one refresh per venue whose previous refresh has finished:
    search for the market until found (every REFRESH s), reload minute history
    every REFRESH s (so a restart, or a missed poll, is filled in), and take a
    quote. Failures are printed once per distinct message and never raised.
    """

    def __init__(self, game, venues=VENUES, log=print):
        self.game, self.venues, self.log = game, venues, log
        self.tape = Tape()
        self.found = {}
        self.quotes = {v.key: [] for v in venues}
        self.history = {v.key: [] for v in venues}
        self.next_find = {v.key: 0.0 for v in venues}
        self.next_history = {v.key: 0.0 for v in venues}
        self.notes = {}
        self.jobs = {}
        self.pool = ThreadPoolExecutor(max_workers=len(venues), thread_name_prefix="market")

    def listings(self):
        return [public(self.found[v.key]) for v in self.venues if v.key in self.found]

    def poll(self):
        for v in self.venues:
            job = self.jobs.get(v.key)
            if job is None or job.done():
                self.jobs[v.key] = self.pool.submit(self.refresh, v)

    def catch_up(self, t, timeout=120, step=10):
        """Block until every listed venue is observed through instant t (bounded by timeout)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if all((self.tape.until(k) or 0) >= t for k in list(self.found)):
                return True
            self.poll()
            time.sleep(step)
        return False

    def note(self, v, message):
        if self.notes.get(v.key) != message:
            self.notes[v.key] = message
            self.log(f"market {v.name}: {message}")

    def refresh(self, v):
        try:
            now = time.time()
            listing = self.found.get(v.key)
            if listing is None:
                if now < self.next_find[v.key]:
                    return
                self.next_find[v.key] = now + REFRESH
                listing = v.find(self.game)
                if listing is None:
                    self.note(v, "no game-winner market listed yet")
                    return
                self.found[v.key] = listing
                self.note(v, f"{listing['id']} {listing['url']}")
            if now >= self.next_history[v.key]:
                self.history[v.key] = v.history(listing, self.game["start"] - MARGIN, int(now))
                self.next_history[v.key] = now + REFRESH
            self.quotes[v.key].append((now, v.quote(listing)))
            self.tape.put(v.key, self.history[v.key] + self.quotes[v.key], now)
        except Exception as e:  # a venue outage must not stop the scorebook
            self.note(v, f"refresh failed: {e}")
