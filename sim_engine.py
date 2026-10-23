#!/usr/bin/env python3
"""Deterministic, offline replay of past MLB games through the Bend engine.

The fixture is the input timeline; Bend remains the owner of the scorebook
and the Monte Carlo simulation. This module adds a reusable replay engine
for tests and demos rather than another game model:

    engine = ReplayEngine(849809, depth=8)       # no network needed
    engine.pregame()
    first = engine.step()                         # one completed play
    engine.seek(20)                               # reset + replay 20 plays
    engine.run()                                  # whole game, returns 0/1

CLI:
    python3 sim_engine.py --pk 849809
    python3 sim_engine.py --pk 849809 --delay 1 --serve
    python3 sim_engine.py --pk 849809 --fetch --publish

Fixtures are read from fixtures/<pk>/ and are never downloaded unless
--fetch (or fetch=True) is explicitly supplied. The same engine backs
`live.py --replay`, so the rehearsal and the reusable API cannot drift.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import live


class ReplayEngine:
    """Replay one fixture with deterministic per-play Bend simulations.

    `cursor` is the number of completed plays applied. `step()` advances one
    play and raises BendError without advancing on a Bend failure. `run()`
    is the command-line-friendly wrapper: it counts errors, writes the CSV,
    performs the final box check when the fixture is Final, and returns 0/1.
    """

    def __init__(self, pk, depth=16, mode="cpu", publisher=None, fetch=False,
                 verbose=False):
        self.pk = pk
        self.depth = depth
        self.mode = mode
        self.publisher = publisher
        self.verbose = verbose
        self.source = live.Source(pk, cache=True, allow_fetch=fetch)
        self.status = self.source.get("status")
        self.teams = live.teams_of(self.status)
        self.away_cum, self.home_cum = live.game_rates(self.source, self.teams)
        (live.ROOT / "runs").mkdir(exist_ok=True)
        (live.ROOT / "runs" / f"{pk}-rates.json").write_text(
            json.dumps({"away": self.away_cum, "home": self.home_cum}))
        self.plays = live.complete_plays(self.source.get("plays"))
        self.codes = live.encode_plays(self.plays)
        self.wp = live.wp_map(self.source.get("wp"))
        self.is_final = self.status["gameData"]["status"]["abstractGameState"] == "Final"
        self.reset()

    def reset(self):
        """Reset to before the first pitch, retaining the loaded fixture."""
        self.cursor = 0
        self.errors = 0
        self.box_ok = True
        self._last_bend = None
        self._finalized = False
        self.book = live.Book(
            self.pk, self.teams["away"]["abbr"], self.teams["home"]["abbr"],
            self.depth, self.mode, self.publisher, verbose=self.verbose)
        return self

    def _bend(self, count):
        return live.run_bend(self.depth, live.seed_for(count), self.away_cum,
                             self.home_cum, self.codes[:count], self.mode)

    def pregame(self):
        """Compute and return the pregame row (idempotent)."""
        if -1 in self.book.rows:
            return self.book.rows[-1]
        b = self._bend(0)
        self._last_bend = b
        return self.book.add(-1, b, None, None)

    def step(self):
        """Apply one completed play and return its row, or None at the end."""
        if self.cursor >= len(self.plays):
            return None
        count = self.cursor + 1
        play = self.plays[self.cursor]
        b = self._bend(count)
        idx = play["about"]["atBatIndex"]
        row = self.book.add(idx, b, play, self.wp.get(idx))
        self._last_bend = b
        self.cursor = count
        return row

    def seek(self, count):
        """Reset and replay exactly `count` plays; return the row dictionary."""
        if not 0 <= count <= len(self.plays):
            raise ValueError(f"play count must be between 0 and {len(self.plays)}")
        self.reset()
        self.pregame()
        while self.cursor < count:
            self.step()
        return self.book.rows

    def finalize(self):
        """Finalize a fully replayed Final fixture; return box-check status."""
        if not self.is_final or self.cursor != len(self.plays):
            return None
        self.pregame()
        b = self._bend(len(self.plays))
        self._last_bend = b
        self.book.final(b["home_runs"] > b["away_runs"])
        self.box_ok = live.box_check(self.source.get("box"), self.source.get("linescore"), b)
        self._finalized = True
        return self.box_ok

    def _error(self, label, error):
        self.errors += 1
        if self.verbose:
            print(f"#{label} bend error: {error}", flush=True)

    def run(self, delay=0.0, limit=None, stream=False, on_row=None):
        """Replay from the start; optionally sleep between plays for a demo.

        `limit` restricts the number of plays (useful for a short demo or a
        test). `stream` writes/publishes after every row; otherwise the CSV
        is written once at the end. `on_row` receives each row, including
        the pregame row, after it is added.
        """
        if delay < 0:
            raise ValueError("delay must be nonnegative")
        target = len(self.plays) if limit is None else min(limit, len(self.plays))
        if target < 0:
            raise ValueError("limit must be nonnegative")
        self.reset()
        try:
            row = self.pregame()
            if on_row:
                on_row(row)
            if stream:
                self.book.write()
        except live.BendError as e:
            self._error("pre", e)
        while self.cursor < target:
            try:
                row = self.step()
            except live.BendError as e:
                self._error(self.plays[self.cursor]["about"]["atBatIndex"], e)
                self.cursor += 1
                continue
            if on_row:
                on_row(row)
            if stream:
                self.book.write()
            if delay:
                time.sleep(delay)
        if target == len(self.plays) and self.is_final:
            try:
                self.finalize()
            except (live.BendError, RuntimeError, ValueError) as e:
                self._error("final", e)
                self.box_ok = False
        published = self.book.write()
        if self.verbose:
            self.book.summary()
        return 0 if self.errors == 0 and self.book.mismatch_count() == 0 and self.box_ok and published else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pk", type=int, default=849809, help="fixture gamePk (default: NLCS Game 1)")
    ap.add_argument("--depth", type=int, default=16, help="2^depth simulations per play")
    ap.add_argument("--mode", choices=("cpu", "gpu"), default=live.DEFAULT_MODE)
    ap.add_argument("--fetch", action="store_true", help="download missing fixture data; otherwise offline")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds between plays for a demo")
    ap.add_argument("--limit", type=int, help="stop after this many completed plays")
    ap.add_argument("--serve", action="store_true", help="serve the local chart while replaying")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--publish", action="store_true", help="publish streamed updates to Cloudflare")
    args = ap.parse_args(argv)
    if args.depth < 0 or (args.limit is not None and args.limit < 0) or args.delay < 0:
        ap.error("depth, limit and delay must be nonnegative")
    publisher = None
    if args.publish:
        env = live.load_env()
        if not env.get("WP_PUSH_URL") or not env.get("WP_PUSH_TOKEN"):
            ap.error("--publish needs WP_PUSH_URL and WP_PUSH_TOKEN (environment or .env)")
        publisher = live.Publisher(env["WP_PUSH_URL"], env["WP_PUSH_TOKEN"])
        print(f"publishing: {env['WP_PUSH_URL'].rstrip('/')}/?pk={args.pk}", flush=True)
    try:
        engine = ReplayEngine(args.pk, depth=args.depth, mode=args.mode,
                              publisher=publisher, fetch=args.fetch, verbose=True)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        ap.error(str(e))
    if args.serve:
        live.serve(args.port)
        print(f"chart: http://127.0.0.1:{args.port}/web/?pk={args.pk}", flush=True)
    rc = engine.run(delay=args.delay, limit=args.limit,
                    stream=args.serve or args.publish or args.delay > 0)
    if args.serve:
        print("replay complete; chart remains available (Ctrl-C to stop)", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
