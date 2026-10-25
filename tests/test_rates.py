import unittest

import live

TEAMS = {"away": {"id": 1}, "home": {"id": 2}}
EMPTY = {"stats": [{"group": {"displayName": "pitching"}, "splits": []}]}


def pitching(bf, hits, starts=0):
    stat = {"battersFaced": bf, "strikeOuts": bf // 5, "baseOnBalls": bf // 12, "hitBatsmen": bf // 100,
            "hits": hits, "doubles": hits // 5, "triples": hits // 50, "homeRuns": hits // 8,
            "gamesStarted": starts}
    return {"stats": [{"group": {"displayName": "pitching"}, "splits": [{"stat": stat}]}]}


class Stub:
    """A source: the schedule (game type, probable starters) and pitching lines through the day before."""

    def __init__(self, teams, starters=None, game_type="R"):
        self.teams, self.starters = teams, starters or {}
        self.game_type = game_type

    def get(self, name, **kw):
        if name == "schedule":
            sides = {s: {"probablePitcher": {"id": pid}} if s in self.starters else {}
                     for s, pid in (("away", 11), ("home", 12))}
            return {"dates": [{"games": [{"officialDate": "2026-05-10", "gameType": self.game_type,
                                          "teams": sides}]}]}
        assert kw["end"] == "2026-05-09", kw
        if name.startswith("asof_"):
            return self.teams[int(name[5:])]
        return self.starters["away" if kw["id"] == 11 else "home"]


def mass(cum):
    """Per-outcome probability (out of 10000) from cumulative thresholds."""
    return dict(zip(live.ORDER, (b - a for a, b in zip([0, *cum], cum))))


class GameRatesTest(unittest.TestCase):
    def test_opening_day_has_no_stats_and_uses_the_league(self):
        away, home = live.game_rates(Stub({1: EMPTY, 2: EMPTY}), TEAMS)
        self.assertGreater(mass(home)["W"], mass(away)["W"])
        self.assertEqual((10000, 10000), (away[-1], home[-1]))

    def test_identical_pitching_favours_the_home_side(self):
        same = pitching(6000, 1400)
        away, home = live.game_rates(Stub({1: same, 2: same}), TEAMS)
        a, h = mass(away), mass(home)
        for e in "WDTH":
            self.assertGreater(h[e], a[e], e)

    def test_better_pitching_lowers_the_hits_its_opponent_bats_at(self):
        weak, strong = pitching(6000, 1600), pitching(6000, 1200)
        away_vs_strong, _ = live.game_rates(Stub({1: weak, 2: strong}), TEAMS)
        away_vs_weak, _ = live.game_rates(Stub({1: strong, 2: weak}), TEAMS)
        self.assertLess(mass(away_vs_strong)["S"], mass(away_vs_weak)["S"])

    def test_an_ace_starter_moves_his_side_and_a_missing_one_falls_back_to_the_team(self):
        team = pitching(6000, 1400)
        ace = pitching(700, 120, starts=28)
        without, _ = live.game_rates(Stub({1: team, 2: team}), TEAMS)
        with_ace, _ = live.game_rates(Stub({1: team, 2: team}, {"home": ace}), TEAMS)
        self.assertLess(mass(with_ace)["S"], mass(without)["S"])


class AutomaticRunnerTest(unittest.TestCase):
    def test_regular_season_only(self):
        self.assertTrue(live.automatic_runner(Stub({}, game_type="R")))
        self.assertFalse(live.automatic_runner(Stub({}, game_type="W")))


if __name__ == "__main__":
    unittest.main()
