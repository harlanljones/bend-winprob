import unittest

from sim_engine import ReplayEngine


class ReplayEngineTest(unittest.TestCase):
    """These tests use the committed World Series Game 1 fixture and never access the network."""

    def engine(self, depth=3):
        return ReplayEngine(849805, depth=depth, mode="cpu", fetch=False, verbose=False)

    @staticmethod
    def comparable(row):
        # Wall time and subprocess timing are intentionally not deterministic.
        return {k: v for k, v in row.items() if k not in ("wall_time", "seconds")}

    def test_seek_matches_sequential_replay(self):
        sequential = self.engine()
        sequential.pregame()
        expected = [sequential.step() for _ in range(8)]
        sought = self.engine()
        rows = sought.seek(8)
        self.assertEqual(8, sought.cursor)
        for row in expected:
            self.assertEqual(self.comparable(row), self.comparable(rows[row["at_bat_index"]]))

    def test_same_fixture_and_seed_are_deterministic(self):
        first, second = self.engine(), self.engine()
        first.pregame()
        second.pregame()
        for _ in range(6):
            a, b = first.step(), second.step()
            self.assertEqual(self.comparable(a), self.comparable(b))

    def test_full_replay_finishes_with_official_box_score(self):
        engine = self.engine(depth=2)
        self.assertEqual(0, engine.run())
        self.assertTrue(engine.box_ok)
        self.assertEqual(70, len(engine.book.rows))
        self.assertEqual(100.0, engine.book.rows[68]["bend_home_wp"])
        self.assertEqual(0, engine.book.rows[68]["sims"])

    def test_missing_fixture_is_offline_error(self):
        with self.assertRaises(FileNotFoundError):
            ReplayEngine(999999999, fetch=False)


if __name__ == "__main__":
    unittest.main()
