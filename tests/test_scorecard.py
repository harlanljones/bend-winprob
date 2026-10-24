import unittest

import live


def credit(pos, kind):
    return {"position": {"code": pos}, "credit": kind}


def play(kind, desc="", runners=(), batter=7, event=""):
    return {"result": {"eventType": kind, "description": desc, "event": event},
            "matchup": {"batter": {"id": batter, "fullName": "Mookie Betts"}},
            "runners": list(runners)}


def runner(rid, *credits):
    return {"details": {"runner": {"id": rid}}, "credits": list(credits)}


class NotationTest(unittest.TestCase):
    def test_double_play_is_the_whole_relay_once_per_fielder(self):
        p = play("grounded_into_double_play", runners=[
            runner(1, credit("6", "f_assist"), credit("4", "f_putout")),
            runner(7, credit("4", "f_assist"), credit("3", "f_putout"))])
        self.assertEqual("6-4-3 DP", live.notation(p))

    def test_strikeouts_swinging_and_called(self):
        self.assertEqual("K", live.notation(play("strikeout", "Betts strikes out swinging.")))
        self.assertEqual("Kc", live.notation(play("strikeout", "Betts called out on strikes.")))

    def test_outs_name_the_batters_fielders_not_a_runners(self):
        lead = runner(1, credit("5", "f_putout"))
        self.assertEqual("F8", live.notation(play("field_out", "Betts flies out to center fielder.",
                                                  [lead, runner(7, credit("8", "f_putout"))])))
        self.assertEqual("P4", live.notation(play("field_out", "Betts pops out to second baseman.",
                                                  [runner(7, credit("4", "f_putout"))])))
        self.assertEqual("3U", live.notation(play("field_out", "Betts grounds out to first baseman.",
                                                  [runner(7, credit("3", "f_putout"))])))
        self.assertEqual("6-3", live.notation(play("field_out", "Betts grounds out.",
                                                   [runner(7, credit("6", "f_assist"), credit("3", "f_putout"))])))

    def test_error_names_the_fielder_and_runner_plays_are_abbreviated(self):
        self.assertEqual("E6", live.notation(play("field_error", runners=[
            runner(7, credit("6", "f_fielding_error"))])))
        self.assertEqual("CS", live.notation(play("caught_stealing_2b", event="Caught Stealing 2B")))

    def test_batter_is_named_by_surname(self):
        self.assertEqual("Acuña", live.last_name("Ronald Acuña Jr."))
        self.assertEqual("", live.last_name(None))


if __name__ == "__main__":
    unittest.main()
