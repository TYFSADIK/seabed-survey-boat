"""Survey planning: beam footprint -> line spacing -> lawnmower lines -> ArduPilot mission file.

Ping sonar (Blue Robotics Ping2) is single-beam, ~25 deg cone:
    footprint diameter = 2 * depth * tan(beam/2)
For a gridded bathymetry map you want overlap, so spacing = footprint * (1 - overlap).
Single-beam never covers 100% of the floor; the gap between lines is interpolated, which
is why planted targets must be scored, not assumed.
"""
import math


def footprint_m(depth_m, beam_deg=25.0):
    return 2 * depth_m * math.tan(math.radians(beam_deg) / 2)


def line_spacing_m(min_depth_m, beam_deg=25.0, overlap=0.2, max_spacing=10.0):
    """Plan for the SHALLOWEST water in the box (smallest footprint)."""
    return min(footprint_m(min_depth_m, beam_deg) * (1 - overlap), max_spacing)


def lawnmower(width_m, length_m, spacing_m, heading_deg=0.0, origin=(0.0, 0.0), run_in_m=5.0):
    """Waypoints (east, north) for parallel lines along `heading_deg`, with straight run-ins
    so the boat is stable (heading, speed) before data on each line counts."""
    h = math.radians(heading_deg)
    ux, uy = math.sin(h), math.cos(h)          # along-line unit vector
    vx, vy = math.cos(h), -math.sin(h)         # cross-line
    n = int(width_m // spacing_m) + 1
    wps = []
    for i in range(n):
        off = i * spacing_m
        a = (-run_in_m, length_m + run_in_m) if i % 2 == 0 else (length_m + run_in_m, -run_in_m)
        for s in a:
            wps.append((origin[0] + off * vx + s * ux, origin[1] + off * vy + s * uy))
    return wps


def enu_to_ll(e, n, lat0, lon0):
    return lat0 + math.degrees(n / 6378137.0), lon0 + math.degrees(e / (6378137.0 * math.cos(math.radians(lat0))))


def qgc_wpl(waypoints_en, lat0, lon0, speed_ms=1.2, accept_radius_m=1.5):
    """QGroundControl WPL 110 text for ArduPilot Rover (boat frame). Upload with MAVProxy `wp load`."""
    lines = ["QGC WPL 110", f"0\t1\t0\t16\t0\t0\t0\t0\t{lat0:.7f}\t{lon0:.7f}\t0\t1"]
    seq = 1
    lines.append(f"{seq}\t0\t3\t178\t1\t{speed_ms}\t-1\t0\t0\t0\t0\t1")   # DO_CHANGE_SPEED
    for e, n in waypoints_en:
        seq += 1
        lat, lon = enu_to_ll(e, n, lat0, lon0)
        lines.append(f"{seq}\t0\t3\t16\t0\t{accept_radius_m}\t0\t0\t{lat:.7f}\t{lon:.7f}\t0\t1")
    seq += 1
    lines.append(f"{seq}\t0\t3\t20\t0\t0\t0\t0\t0\t0\t0\t1")               # RETURN_TO_LAUNCH
    return "\n".join(lines) + "\n"
