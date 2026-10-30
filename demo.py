"""Run: python demo.py  -> plan, simulate, grid, detect planted targets, write an ArduPilot mission."""
import numpy as np

from survey import plan, process, sim

spacing = plan.line_spacing_m(min_depth_m=3.0)
wps = plan.lawnmower(width_m=60, length_m=80, spacing_m=spacing)
print(f"footprint at 3 m: {plan.footprint_m(3):.2f} m -> line spacing {spacing:.2f} m, {len(wps)//2} lines")
mission = plan.qgc_wpl(wps, 44.2310, -76.4860)
open("data/mission.waypoints", "w").write(mission)

planted = [(20, 30), (45, 60)]
e, n, d, c = sim.run(wps, targets=planted)
depth = process.correct(d, c, draft_m=0.0, temp_c=8.0)
hits, res, sigma = process.along_track_hits(depth)
objs = process.cluster_points(e, n, res, hits)
g, ee, nn = process.grid(e, n, depth, cell_m=1.0, bounds=(0, 60, 0, 80))   # bathymetry map product
print(f"bathymetry grid {g.shape}, depth {np.nanmin(g):.2f}-{np.nanmax(g):.2f} m; along-track sigma {sigma:.3f} m")
print("objects:", [(round(o[0], 1), round(o[1], 1), o[2], round(o[3], 2)) for o in objs])
print("score:", process.score(objs, planted))
