import subprocess
import unittest

import live


def runner(rid, segments):
    return [
        {
            "details": {"runner": {"id": rid}, "playIndex": 1},
            "movement": {
                "originBase": origin,
                "start": start,
                "end": end,
                "isOut": is_out,
            },
        }
        for origin, start, end, is_out in segments
    ]


class EncodingRegressionTest(unittest.TestCase):
    def test_round_trip_uses_chronological_origin_and_destination(self):
        play = {
            "about": {"atBatIndex": 33},
            "runners": [
                *runner(660271, [(None, None, "1B", False), (None, "1B", "2B", False)]),
                *runner(669242, [("1B", "1B", "2B", False),
                                 ("1B", "2B", "1B", False),
                                 ("1B", "1B", "score", False)]),
            ],
        }
        # Batter reaches second; the runner who started on first scores.
        self.assertEqual("--R2", live.encode_play(play, before={1}))

    def test_omitted_force_advance_is_recovered(self):
        play = {
            "about": {"atBatIndex": 4},
            "runners": [
                *runner(661388, [("2B", "2B", None, True)]),
                *runner(683734, [(None, None, "1B", False)]),
            ],
        }
        # Two outs, runners on first and second: the omitted first runner
        # must advance to second before the batter lands on first.
        self.assertEqual("-X21", live.encode_play(play, before={1, 2}))

    def test_play_list_carries_previous_bases(self):
        first = {
            "about": {"atBatIndex": 3},
            "count": {"outs": 2},
            "matchup": {"postOnFirst": {}, "postOnSecond": {}},
            "runners": [
                *runner(1, [("1B", "1B", "2B", False)]),
                *runner(2, [(None, None, "1B", False)]),
            ],
        }
        force = {
            "about": {"atBatIndex": 4},
            "count": {"outs": 3},
            "matchup": {},
            "runners": [
                *runner(1, [("2B", "2B", None, True)]),
                *runner(3, [(None, None, "1B", False)]),
            ],
        }
        self.assertEqual(["--21", "-X21"], live.encode_plays([first, force]))

    def test_bend_accepts_runner_exchange(self):
        rates = "2222,6860,7806,9234,9657,9691,10000"
        result = subprocess.run(
            [str(live.ROOT / "wp"), f"0|1|{rates}|{rates}|---1;--21;-12X|cpu"],
            cwd=live.ROOT, capture_output=True, text=True, check=True)
        self.assertIn("STATE 1 T 1 12- 0 0 0", result.stdout)
        self.assertIn("LINE 3 0 1 0 0 0 0 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
