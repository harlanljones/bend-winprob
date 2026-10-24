import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import markets
from sim_engine import ReplayEngine


def play(idx, start, end, complete=True):
    return {"about": {"atBatIndex": idx, "startTime": start, "endTime": end, "isComplete": complete}}


class SampleTimesTest(unittest.TestCase):
    def test_reads_after_play_but_never_after_next_play_ended(self):
        times = {"allPlays": [
            play(0, "2026-10-12T00:16:42Z", "2026-10-12T00:17:35Z"),
            play(1, "2026-10-12T00:17:56Z", "2026-10-12T00:18:05Z"),  # quick: 30 s later
            play(2, "2026-10-12T00:19:35Z", "2026-10-12T00:20:47Z"),
            play(3, "2026-10-12T00:21:00Z", "2026-10-12T00:21:30Z", complete=False),
        ]}
        s = markets.sample_times(times)
        end = markets.stamp
        self.assertEqual((end("2026-10-12T00:16:42Z"), None), s[-1], "pregame reads at first pitch")
        self.assertEqual((end("2026-10-12T00:18:05Z"), end("2026-10-12T00:17:35Z")), s[0],
                         "clipped to the next play's end")
        self.assertEqual(end("2026-10-12T00:19:05Z"), s[1][0])
        self.assertEqual(end("2026-10-12T00:21:47Z"), s[2][0], "last completed play: LAG after its end")
        self.assertNotIn(3, s, "an at-bat in progress has no price yet")

    def test_before_first_pitch_pregame_reads_latest(self):
        self.assertEqual({-1: (None, None)}, markets.sample_times({"allPlays": []}))


class TapeTest(unittest.TestCase):
    def setUp(self):
        self.tape = markets.Tape()
        self.tape.put("v", [(100, 40.0), (160, 55.0)], until=400)

    def test_reads_last_observation_at_or_before_instant(self):
        self.assertIsNone(self.tape.at("v", 99))
        self.assertEqual(40.0, self.tape.at("v", 159))
        self.assertEqual(55.0, self.tape.at("v", 160))
        self.tape.put("w", [(100, 40.0)], until=150)
        self.assertEqual(40.0, self.tape.at("w", None), "None reads the latest")
        self.tape.put("w", [(100, 40.0)], until=100 + markets.STALE + 1)
        self.assertIsNone(self.tape.at("w", None), "...unless the latest is stale by the tape's end")

    def test_an_unusable_book_masks_the_older_price(self):
        self.tape.put("v", [(100, 40.0), (160, None)], until=400)
        self.assertEqual(40.0, self.tape.at("v", 159))
        self.assertIsNone(self.tape.at("v", 200))

    def test_a_play_never_reads_a_price_from_before_it_ended(self):
        # Play ended at 130; the last observation by its read instant (190) is from 100.
        self.assertIsNone(self.tape.at("v", 150, after=130))
        self.assertEqual(55.0, self.tape.at("v", 190, after=130))

    def test_stale_or_unobserved_instants_are_unknown(self):
        self.tape.put("v", [(100, 40.0), (160, 55.0)], until=10_000)
        self.assertEqual(55.0, self.tape.at("v", 160 + markets.STALE))
        self.assertIsNone(self.tape.at("v", 160 + markets.STALE + 1), "stale")
        self.assertIsNone(self.tape.at("v", 10_001), "after the tape is complete: not yet known")
        self.assertIsNone(self.tape.at("other", 150))


class PriceTest(unittest.TestCase):
    def test_midpoint_needs_a_tight_two_sided_book(self):
        self.assertAlmostEqual(0.615, markets.mid("0.61", "0.62"))
        self.assertIsNone(markets.mid("0.40", "0.60"), "too wide")
        self.assertIsNone(markets.mid("0", "1"), "empty book")
        self.assertIsNone(markets.mid(None, "0.5"))
        self.assertIsNone(markets.mid("0.6", "0.5"), "crossed")

    def test_kalshi_normalises_its_two_team_markets(self):
        self.assertAlmostEqual(60.0, markets.Kalshi.devig(0.63, 0.42))
        self.assertAlmostEqual(63.0, markets.Kalshi.devig(0.63, None))
        self.assertAlmostEqual(58.0, markets.Kalshi.devig(None, 0.42))
        self.assertIsNone(markets.Kalshi.devig(None, None))


GAME = {"away": "LAD", "home": "MIL", "start": markets.stamp("2026-10-12T00:00:00Z"), "date": "2026-10-11"}


class VenueTest(unittest.TestCase):
    def test_kalshi_ticker_uses_eastern_first_pitch_and_falls_back_to_historical(self):
        asked = []

        def fake_get(url):
            asked.append(url)
            if "/historical/markets?" in url:
                return {"markets": [{"ticker": "KXMLBGAME-26OCT112000LADMIL-LAD"},
                                    {"ticker": "KXMLBGAME-26OCT112000LADMIL-MIL"}]}
            return {"markets": []}

        with patch.object(markets, "get", fake_get):
            listing = markets.Kalshi().find(GAME)
        self.assertEqual("KXMLBGAME-26OCT112000LADMIL", listing["id"])
        self.assertEqual("KXMLBGAME-26OCT112000LADMIL-MIL", listing["home_ticker"])
        self.assertIn("/historical/markets?event_ticker=KXMLBGAME-26OCT112000LADMIL", asked[-1])

    def test_polymarket_us_long_side_is_oriented_to_the_home_team(self):
        side = {"long": True, "team": {"ordering": "away"}}
        responses = {
            "/v1/market/slug/aec-mlb-lad-mil-2026-10-11": {"market": {"marketSides": [side]}},
            "/bbo": {"marketData": {"bestBid": {"value": "0.30"}, "bestAsk": {"value": "0.32"}}},
            "/v1/price-history": {"history": [{"timestamp": 5, "longPrice": 0.32, "shortPrice": 0.70}]},
        }

        def fake_get(url):
            return next(v for k, v in responses.items() if k in url)

        venue = markets.PolymarketUS()
        with patch.object(markets, "get", fake_get):
            listing = venue.find(GAME)
            self.assertAlmostEqual(69.0, venue.quote(listing))       # away long at 31: home 69
            self.assertAlmostEqual(69.0, venue.history(listing, 0, 10)[0][1])

    def test_polymarket_picks_the_home_teams_token(self):
        event = {"teams": [{"name": "Los Angeles Dodgers", "ordering": "away"},
                           {"name": "Milwaukee Brewers", "ordering": "home"}],
                 "markets": [{"slug": "mlb-lad-mil-2026-10-11-nrfi", "outcomes": "[]", "clobTokenIds": "[]"},
                             {"slug": "mlb-lad-mil-2026-10-11",
                              "outcomes": '["Los Angeles Dodgers", "Milwaukee Brewers"]',
                              "clobTokenIds": '["away-token", "home-token"]'}]}
        with patch.object(markets, "get", lambda url: [event]):
            self.assertEqual("home-token", markets.Polymarket().find(GAME)["token"])


class FeedTest(unittest.TestCase):
    def test_live_feed_merges_history_and_quotes_and_survives_outages(self):
        now = time.time()

        class Good:
            key, name = "good", "Good"
            find = staticmethod(lambda game: {"key": "good", "name": "Good", "url": "https://x", "id": "g"})
            history = staticmethod(lambda listing, t0, t1: [(now - 60, 50.0)])
            quote = staticmethod(lambda listing: 52.0)

        class Down:
            key, name = "down", "Down"

            @staticmethod
            def find(game):
                raise RuntimeError("venue outage")

        notes = []
        feed = markets.LiveFeed(GAME, venues=(Good(), Down()), log=notes.append)
        feed.poll()
        for job in feed.jobs.values():
            job.result(timeout=5)
        self.assertEqual(50.0, feed.tape.at("good", now - 1))
        self.assertEqual(52.0, feed.tape.at("good", None))
        self.assertEqual([{"key": "good", "name": "Good", "url": "https://x", "id": "g"}], feed.listings())
        self.assertTrue(any("venue outage" in n for n in notes))


class RecordedReplayTest(unittest.TestCase):
    def test_replay_without_recording_leaves_market_columns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            source = SimpleNamespace(dir=Path(d), allow_fetch=False)
            tape, listings, samples = markets.recorded(source, teams=None, scoring={})
        self.assertEqual(([], {}), (listings, samples))

    def test_bundled_replay_reads_recorded_prices_offline(self):
        engine = ReplayEngine(849809, depth=2, mode="cpu", fetch=False, verbose=False)
        rows = engine.seek(3)
        self.assertEqual(["kalshi", "polymarket", "polymarket_us"], [m["key"] for m in engine.listings])
        for idx in (-1, 0, 1, 2):
            for col in markets.COLUMNS:
                self.assertIsInstance(rows[idx][col], float, f"{col} at {idx}")
                self.assertTrue(0.0 <= rows[idx][col] <= 100.0)


if __name__ == "__main__":
    unittest.main()
