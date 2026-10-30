# Autonomous Seabed-Survey Boat (build guide)

Private research repo. An autonomous seabed-survey boat: ArduPilot lawnmower survey lines, Ping sonar depth logs, and gridded anomaly maps scored on planted targets.

Full write-up and phase plan: [`docs/project-page.md`](docs/project-page.md)

## What's here

| File | Purpose |
|---|---|
| `survey/plan.py` | Beam footprint → line spacing (planned for the shallowest water), lawnmower lines with run-ins, **QGC WPL 110** mission for ArduPilot Rover (boat) |
| `survey/process.py` | Draft, water-level, and **speed-of-sound** corrections (Marczak fresh water), confidence gating, **along-track target detection** (running-median residual with MAD sigma, before gridding so objects aren't averaged away), spatial clustering, gridding, IDW gap fill, grid-level median/MAD anomalies, scoring against planted targets |
| `survey/sim.py` | Simulated lake bed with planted targets and Ping-like single-beam behaviour (returns the shallowest point in the cone) |

## Quickstart

```bash
python demo.py       # writes data/mission.waypoints
python -m unittest -v
```

## Phase checklist
- [ ] Phase 0: ArduPilot Rover SITL with `FRAME_CLASS=2` (boat). Load `data/mission.waypoints`
- [ ] Phase 1: Ping2 on the bench via `brping` at 10 Hz, logged with GNSS time
- [ ] Phase 2 (after ice-out): plant 2–3 targets at surveyed positions and run the lines
- [ ] Phase 3: grid, then score Pd, false alarms, and position error per target size and depth
- [ ] Measure water temperature at depth on survey day for `sound_speed_fresh`. At 4 °C vs the assumed 1500 m/s, depths are off by about 5%
- [ ] Upgrade path: side-scan (e.g. a Ping360 in profiling mode) for coverage between lines
