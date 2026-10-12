"""Horizontal speed between consecutive fixes, and the rule on tracks that are too fast.

A free flight has only a few steps faster than the top speed of its discipline, and
the excursion rule deletes them one by one. A track that is too fast most of the time
is not a free flight (a powered aircraft, a file with compressed time),
so the whole flight is dropped.
"""

import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6_371_000.0  # mean radius of the Earth, taken as a sphere


def hav(theta: np.ndarray) -> np.ndarray:
    """Haversine of an angle in radians: sin^2(theta / 2)."""
    return np.sin(theta / 2) ** 2


def step_speed(fixes: pd.DataFrame) -> np.ndarray:
    """Apparent horizontal speed in km/h from each fix to the next: one value fewer than the fixes.

    Distance on the sphere divided by the elapsed time. The times must be increasing,
    as the clock rule leaves them.
    """
    phi, lam = np.radians(fixes["lat"].to_numpy()), np.radians(fixes["lon"].to_numpy())
    # Haversine formula (https://en.wikipedia.org/wiki/Haversine_formula), between each
    # fix (phi1, lam1) and the next (phi2, lam2):
    # hav(theta) = hav(phi2 - phi1) + cos(phi1) cos(phi2) hav(lam2 - lam1), d = 2 r arcsin(sqrt(hav(theta))).
    hav_theta = hav(np.diff(phi)) + np.cos(phi[:-1]) * np.cos(phi[1:]) * hav(np.diff(lam))
    distance = 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(hav_theta))
    return 3.6 * distance / np.diff(fixes["t"].to_numpy())  # m/s -> km/h


def speed_summary(fixes: pd.DataFrame) -> dict:
    """Number of steps between fixes, and the median and 90th percentile of their
    speed in km/h (NaN without steps)."""
    speed = step_speed(fixes)
    if not len(speed):
        return {"steps": 0, "median_kmh": np.nan, "p90_kmh": np.nan}
    return {
        "steps": len(speed),
        "median_kmh": float(np.median(speed)),
        "p90_kmh": float(np.quantile(speed, 0.9)),
    }


def track_speed(fixes: pd.DataFrame, max_kmh: float, fast_share_max: float) -> dict:
    """Share of steps faster than the top speed (0 with fewer than two fixes), and
    whether the flight is kept (speed_ok)."""
    fast = step_speed(fixes) > max_kmh
    fast_share = float(fast.mean()) if len(fast) else 0.0
    return {"fast_share": fast_share, "speed_ok": fast_share <= fast_share_max}
