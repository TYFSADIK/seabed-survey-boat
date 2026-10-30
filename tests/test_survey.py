import unittest

import numpy as np

from survey import plan, process


class TestSurvey(unittest.TestCase):
    def test_spacing(self):
        self.assertAlmostEqual(plan.footprint_m(10, 25), 4.43, places=2)
        self.assertLess(plan.line_spacing_m(2), plan.line_spacing_m(5))

    def test_mission_format(self):
        m = plan.qgc_wpl(plan.lawnmower(10, 20, 5), 44.0, -76.0)
        lines = m.strip().splitlines()
        self.assertEqual(lines[0], "QGC WPL 110")
        self.assertTrue(lines[-1].split("\t")[3] == "20")      # RTL last

    def test_sound_speed(self):
        self.assertAlmostEqual(process.sound_speed_fresh(20), 1482.3, delta=0.5)

    def test_anomaly_finds_bump(self):
        g = np.full((30, 30), 5.0) + np.random.default_rng(0).normal(0, 0.02, (30, 30))
        g[14:16, 14:16] -= 0.6
        objs = process.cluster_cells(process.anomalies(g), np.arange(31.0), np.arange(31.0), 1.0)
        self.assertEqual(len(objs), 1)
        self.assertAlmostEqual(objs[0][0], 15.0, delta=1)


    def test_along_track_end_to_end(self):
        from survey import sim
        wps = plan.lawnmower(40, 40, plan.line_spacing_m(3.0))
        e, n, d, c = sim.run(wps, targets=((20, 20),))
        hits, res, _ = process.along_track_hits(process.correct(d, c, draft_m=0.0))
        sc = process.score(process.cluster_points(e, n, res, hits), [(20, 20)])
        self.assertEqual(sc["detected"], 1)
        self.assertEqual(sc["false_alarms"], 0)


if __name__ == "__main__":
    unittest.main()
