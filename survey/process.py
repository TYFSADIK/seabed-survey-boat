"""Sonar log -> corrected soundings -> grid -> anomalies -> score against planted targets.

Corrections, in order of how much they matter on a lake:
  1. transducer draft (depth below the surface, not below the sensor)
  2. confidence gating (Ping reports 0-100%)
  3. water level / tide offset for the survey day
  4. speed-of-sound scaling (Ping assumes 1500 m/s; cold fresh water is ~1420-1450)
"""
import math

import numpy as np


def sound_speed_fresh(temp_c):
    """Marczak (1997) speed of sound in pure water, m/s."""
    t = temp_c
    return 1.402385e3 + 5.038813 * t - 5.799136e-2 * t ** 2 + 3.287156e-4 * t ** 3 - 1.398845e-6 * t ** 4 + 2.787860e-9 * t ** 5


def correct(raw_depth_m, confidence, draft_m=0.10, level_offset_m=0.0, temp_c=8.0, assumed_c=1500.0, min_conf=80):
    ok = confidence >= min_conf
    d = raw_depth_m * sound_speed_fresh(temp_c) / assumed_c + draft_m - level_offset_m
    return np.where(ok, d, np.nan)


def grid(e, n, depth, cell_m=1.0, bounds=None):
    """Mean depth per cell (NaN where empty). Returns (grid, e_edges, n_edges)."""
    ok = ~np.isnan(depth)
    e, n, depth = e[ok], n[ok], depth[ok]
    if bounds is None:
        bounds = (e.min(), e.max(), n.min(), n.max())
    ee = np.arange(bounds[0], bounds[1] + cell_m, cell_m)
    nn = np.arange(bounds[2], bounds[3] + cell_m, cell_m)
    s, _, _ = np.histogram2d(n, e, bins=[nn, ee], weights=depth)
    c, _, _ = np.histogram2d(n, e, bins=[nn, ee])
    with np.errstate(invalid="ignore"):
        return s / np.where(c == 0, np.nan, c), ee, nn


def fill_idw(g, power=2, radius=4):
    """Fill empty cells (between single-beam lines) by inverse-distance weighting of neighbours."""
    out = g.copy()
    H, W = g.shape
    known = np.argwhere(~np.isnan(g))
    for y, x in np.argwhere(np.isnan(g)):
        d = np.hypot(known[:, 0] - y, known[:, 1] - x)
        sel = d <= radius
        if sel.any():
            w = 1 / d[sel] ** power
            out[y, x] = np.sum(w * g[known[sel, 0], known[sel, 1]]) / w.sum()
    return out


def anomalies(g, win=7, k=4.0):
    """Robust local anomaly score: residual from a local median, scaled by local MAD.
    Returns list of (row, col, residual_m, z) for |z| > k. Objects on the floor are negative residuals (shallower)."""
    H, W = g.shape
    r = win // 2
    out = []
    for y in range(H):
        for x in range(W):
            if np.isnan(g[y, x]):
                continue
            patch = g[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
            patch = patch[~np.isnan(patch)]
            if patch.size < 9:
                continue
            med = np.median(patch)
            mad = np.median(np.abs(patch - med)) * 1.4826 + 0.01
            z = (g[y, x] - med) / mad
            if abs(z) > k:
                out.append((y, x, float(g[y, x] - med), float(z)))
    return out


def cluster_cells(cells, e_edges, n_edges, cell_m):
    """Merge adjacent anomalous cells into objects -> [(east, north, n_cells, min_residual)]."""
    cells = sorted(cells)
    groups = []
    for c in cells:
        for g in groups:
            if any(abs(c[0] - o[0]) <= 1 and abs(c[1] - o[1]) <= 1 for o in g):
                g.append(c)
                break
        else:
            groups.append([c])
    out = []
    for g in groups:
        ys = np.array([c[0] for c in g]); xs = np.array([c[1] for c in g])
        out.append((float(e_edges[0] + (xs.mean() + 0.5) * cell_m), float(n_edges[0] + (ys.mean() + 0.5) * cell_m),
                    len(g), float(min(c[2] for c in g))))
    return out


def score(objects, planted, radius_m=3.0):
    """planted: [(east, north)]. Returns detection rate, false alarms, and position errors."""
    used, errs = set(), []
    for pe, pn in planted:
        best = None
        for i, (e, n, *_rest) in enumerate(objects):
            d = math.hypot(e - pe, n - pn)
            if i not in used and d <= radius_m and (best is None or d < best[1]):
                best = (i, d)
        if best:
            used.add(best[0]); errs.append(best[1])
    return {"detected": len(errs), "planted": len(planted), "pd": len(errs) / len(planted) if planted else None,
            "false_alarms": len(objects) - len(used), "mean_pos_err_m": float(np.mean(errs)) if errs else None}


def along_track_hits(depth, win=31, k=4.0):
    """Single-beam target detection on the ping sequence (time order), before any gridding.

    Residual = depth - running median over `win` pings; robust sigma from the MAD of all
    residuals. Objects are SHALLOWER than the surrounding bed -> negative residuals.
    Gridding first would average a 2 m object away into its cell neighbours.
    """
    d = np.asarray(depth, float)
    r = win // 2
    pad = np.pad(d, r, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(pad, win)
    med = np.nanmedian(windows, axis=1)
    res = d - med
    sigma = 1.4826 * np.nanmedian(np.abs(res - np.nanmedian(res))) + 1e-3
    hits = res < -k * sigma
    return np.where(np.isnan(res), False, hits), res, sigma


def cluster_points(e, n, res, mask, radius_m=2.0, min_pts=3):
    """Single-linkage clustering (union-find) of along-track hits -> [(east, north, n_hits, min_residual)]."""
    idx = np.nonzero(mask)[0]
    parent = list(range(len(idx)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if math.hypot(e[idx[a]] - e[idx[b]], n[idx[a]] - n[idx[b]]) <= radius_m:
                parent[find(a)] = find(b)
    groups = {}
    for a in range(len(idx)):
        groups.setdefault(find(a), []).append(idx[a])
    out = []
    for g in groups.values():
        if len(g) >= min_pts:
            g = np.array(g)
            out.append((float(e[g].mean()), float(n[g].mean()), len(g), float(res[g].min())))
    return out
