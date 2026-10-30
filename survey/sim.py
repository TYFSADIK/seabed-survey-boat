"""Simulate a survey: sloping lake bed + planted targets, boat on the planned lines, Ping-like noise."""
import numpy as np


def seabed(e, n, targets=((20, 30), (45, 60)), target_h=0.5, target_r=1.0):
    d = 3.0 + 0.04 * n + 0.3 * np.sin(e / 15.0)
    for te, tn in targets:
        d = d - target_h * (np.hypot(e - te, n - tn) < target_r)
    return d


def run(waypoints, beam_deg=25.0, ping_hz=10, speed=1.2, rng=None, **kw):
    rng = rng or np.random.default_rng(0)
    E, N, D, C = [], [], [], []
    for (e0, n0), (e1, n1) in zip(waypoints, waypoints[1:]):
        L = np.hypot(e1 - e0, n1 - n0)
        k = max(int(L / speed * ping_hz), 1)
        f = np.linspace(0, 1, k, endpoint=False)
        e = e0 + f * (e1 - e0) + rng.normal(0, 0.5, k)           # GNSS noise
        n = n0 + f * (n1 - n0) + rng.normal(0, 0.5, k)
        # single beam returns roughly the shallowest point in the footprint
        true = seabed(e, n, **kw)
        r = true * np.tan(np.radians(beam_deg / 2))
        jitter = np.array([seabed(e[i] + rng.uniform(-1, 1, 6) * r[i], n[i] + rng.uniform(-1, 1, 6) * r[i], **kw).min()
                           for i in range(k)])
        E.append(e); N.append(n); D.append(jitter * 1500 / 1440 + rng.normal(0, 0.02, k)); C.append(rng.integers(70, 101, k))
    return np.concatenate(E), np.concatenate(N), np.concatenate(D), np.concatenate(C)
