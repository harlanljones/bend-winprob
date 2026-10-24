import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import live


class RecoveryTest(unittest.TestCase):
    def test_transient_bend_failure_is_retried_before_final(self):
        pk = 999001
        runs = live.ROOT / "runs"
        runs.mkdir(exist_ok=True)
        rates = [2222, 6860, 7806, 9234, 9657, 9691, 10000]
        (runs / f"{pk}-rates.json").write_text(json.dumps({"away": rates, "home": rates}))
        play = {
            "about": {"atBatIndex": 0, "isComplete": True, "inning": 1, "isTopInning": True},
            "result": {"awayScore": 0, "homeScore": 0, "eventType": "strikeout"},
            "count": {"outs": 1}, "matchup": {},
            "runners": [{"details": {"runner": {"id": 1}, "playIndex": 0},
                         "movement": {"originBase": None, "start": None, "end": None, "isOut": True}}],
        }

        class FakeSource:
            def __init__(self):
                self.status_calls = 0

            def get(self, name, **kwargs):
                if name == "status":
                    self.status_calls += 1
                    state = "Live" if self.status_calls <= 2 else "Final"
                    return {
                        "metaData": {"wait": 10},
                        "gameData": {
                            "status": {"abstractGameState": state, "detailedState": state},
                            "teams": {"away": {"id": 1, "abbreviation": "AWY"},
                                      "home": {"id": 2, "abbreviation": "HME"}},
                        },
                    }
                if name == "plays":
                    return {"allPlays": [play]}
                if name == "wp":
                    return []
                if name in ("box", "linescore"):
                    return {}
                raise AssertionError(f"unexpected fetch {name}")

        source = FakeSource()
        calls = []

        def fake_bend(depth, seed, away, home, codes, mode):
            calls.append(len(codes))
            if len(codes) == 1 and calls.count(1) in (1, 3):
                raise live.BendError("transient test failure")
            n = len(codes)
            return {
                "inning": 1, "top": True, "outs": n, "bases": "---",
                "away_runs": 0, "home_runs": 0, "rejected": 0,
                "line": [n, 0, n, 0, 0, 0, 0, 0],
                "home_wins": 0, "away_wins": 1, "unfinished": 0, "seconds": 0.001,
            }

        args = SimpleNamespace(pk=pk, no_serve=True, port=8765, depth=1, mode="cpu", publisher=None)
        try:
            with patch.object(live, "Source", return_value=source), \
                 patch.object(live, "run_bend", side_effect=fake_bend), \
                 patch.object(live, "box_check", return_value=True), \
                 patch.object(live.time, "sleep", lambda _: None):
                result = live.live(args)
            self.assertEqual(0, result)
            self.assertEqual(4, calls.count(1), "play and finalization must both be retried")
            with (runs / f"{pk}.csv").open() as f:
                self.assertEqual(3, len(f.readlines()))
        finally:
            for suffix in ("csv", "meta.json", "rates.json"):
                (runs / f"{pk}-{suffix}").unlink(missing_ok=True)

    def test_publisher_retries_transient_failures(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        publisher = live.Publisher("http://example.test", "token")
        with patch.object(live.urllib.request, "urlopen",
                          side_effect=[OSError("down"), OSError("down"), Response()]) as request, \
             patch.object(live.time, "sleep", lambda _: None):
            self.assertTrue(publisher.push(1, {"away": "A", "home": "H"}, "csv"))
        self.assertEqual(3, request.call_count)

    def test_backfill_updates_revised_mlb_probability(self):
        book = live.Book.__new__(live.Book)
        book.rows = {3: {"mlb_home_wp": 46.0, "bend_home_wp": 56.36, "delta": 10.36}}
        book.backfill({3: 54.8})
        self.assertEqual(54.8, book.rows[3]["mlb_home_wp"])
        self.assertEqual(1.56, book.rows[3]["delta"])

    def test_team_mapping_includes_name_and_logo(self):
        teams = live.teams_of({"gameData": {"teams": {
            "away": {"id": 139, "abbreviation": "TB", "teamName": "Rays"},
            "home": {"id": 158, "abbreviation": "MIL", "teamName": "Brewers"},
        }}})
        self.assertEqual("Rays", teams["away"]["name"])
        self.assertEqual("Brewers", teams["home"]["name"])
        self.assertEqual("https://www.mlbstatic.com/team-logos/139.svg", teams["away"]["logo"])
        self.assertEqual("https://www.mlbstatic.com/team-logos/158.svg", teams["home"]["logo"])

    def test_prune_and_mismatch_count_follow_current_rows(self):
        book = live.Book.__new__(live.Book)
        book.rows = {
            -1: {"state_check": "ok"},
            0: {"state_check": "MISMATCH(outs)"},
            2: {"state_check": "ok"},
        }
        self.assertEqual(1, book.mismatch_count())
        book.prune({0})
        self.assertEqual({-1, 0}, set(book.rows))
        self.assertEqual(1, book.mismatch_count())
        book.rows[0]["state_check"] = "ok"
        self.assertEqual(0, book.mismatch_count())


if __name__ == "__main__":
    unittest.main()
