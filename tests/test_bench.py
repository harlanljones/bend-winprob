import unittest

import bench


def game(pk, day, state="Final"):
    return {"gamePk": pk, "officialDate": day, "status": {"detailedState": state}}


# 3 months of 5, 3 and 2 Final games, plus a postponed game, a dev game and a duplicate.
SCHEDULE = ([game(100 + i, f"2026-04-{i + 1:02d}") for i in range(5)]
            + [game(200 + i, f"2026-05-{i + 1:02d}") for i in range(3)]
            + [game(300 + i, f"2026-06-{i + 1:02d}") for i in range(2)]
            + [game(400, "2026-06-10", "Postponed"), game(999, "2026-04-20"), game(100, "2026-04-21")])


class MetricsTest(unittest.TestCase):
    def test_calibration_puts_certainties_in_the_end_bins(self):
        cal = bench.calibration([0.0, 1.0, 1.0], [0, 1, 1])
        self.assertEqual(10, len(cal))
        self.assertEqual(1, cal[0]["n"])
        self.assertEqual(2, cal[9]["n"])
        self.assertIsNone(cal[5]["forecast"])

    def test_decomposition_sums_to_brier_when_bins_are_constant(self):
        ps = [.15] * 6 + [.55] * 5 + [.85] * 9
        ys = [0, 0, 1, 0, 0, 0] + [1, 0, 1, 1, 0] + [1, 1, 1, 0, 1, 1, 1, 1, 0]
        d = bench.decompose(ps, ys)
        self.assertAlmostEqual(bench.brier(ps, ys), d["rel"] - d["res"] + d["unc"])

    def test_every_game_better_is_a_clear_win(self):
        point, lo, hi, p = bench.bootstrap_delta([(-.5, 10), (-.2, 8), (-.9, 12)], b=500)
        self.assertLess(point, 0)
        self.assertEqual("clear win", bench.verdict(lo, hi))
        self.assertEqual(1, p)

    def test_symmetric_games_are_no_clear_difference(self):
        _, lo, hi, _ = bench.bootstrap_delta([(-1, 10), (1, 10)] * 10, b=500)
        self.assertEqual("no clear difference", bench.verdict(lo, hi))
        self.assertEqual("clear loss", bench.verdict(.001, .01))

    def test_sign_test(self):
        self.assertAlmostEqual(2 * 299 / 4096, bench.sign_test(9, 3))
        self.assertEqual(1.0, bench.sign_test(4, 4))


class SampleTest(unittest.TestCase):
    def test_same_seed_same_sample(self):
        a = bench.stratified_sample(SCHEDULE, 5, 7, (999,))
        self.assertEqual(a, bench.stratified_sample(SCHEDULE, 5, 7, (999,)))

    def test_largest_remainder_quotas(self):
        # exact shares 2.5, 1.5, 1.0 of 5: floors 2, 1, 1, the spare seat to April (tie, first month)
        pks, strata = bench.stratified_sample(SCHEDULE, 5, 7, (999,))
        self.assertEqual({"2026-04": 3, "2026-05": 1, "2026-06": 1}, strata)
        self.assertEqual(5, len(pks))
        # 7 of 10: exact 3.5, 2.1, 1.4 -> 3, 2, 1, spare to April (.5 beats .4)
        _, strata = bench.stratified_sample(SCHEDULE, 7, 7, (999,))
        self.assertEqual({"2026-04": 4, "2026-05": 2, "2026-06": 1}, strata)

    def test_only_final_unexcluded_unique_games(self):
        pks, _ = bench.stratified_sample(SCHEDULE, 10, 3, (999,))
        self.assertEqual(sorted(pks), sorted(set(pks)))
        self.assertEqual(10, len(pks))
        self.assertNotIn(999, pks)
        self.assertNotIn(400, pks)


if __name__ == "__main__":
    unittest.main()
