"""Horizontal speed between consecutive fixes, and the rule on tracks that are too fast.

A free flight spends much of its time climbing in thermals at a low ground speed, so
the median speed of its steps stays well below the top speed of the wing. A track with
a faster median is not a free flight (a powered aircraft, a file with compressed time),
so the whole flight is dropped. Single steps that are too fast are a different problem,
left to the excursion rule.

The speed over a window of some seconds is barely moved by a single wrong fix, so it shows
how fast real flight goes, and serves to choose the top speed of the excursion rule.
"""

import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6_371_000.0  # mean radius of the Earth, taken as a sphere


def hav(theta: np.ndarray) -> np.ndarray:
    """Haversine of an angle in radians: sin^2(theta / 2)."""
    return np.sin(theta / 2) ** 2


def distance_m(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Distance in metres on the sphere from each point (lat1, lon1) to (lat2, lon2), in degrees."""
    phi1, phi2, lam1, lam2 = np.radians(lat1), np.radians(lat2), np.radians(lon1), np.radians(lon2)
    # Haversine formula (https://en.wikipedia.org/wiki/Haversine_formula):
    # hav(theta) = hav(phi2 - phi1) + cos(phi1) cos(phi2) hav(lam2 - lam1), d = 2 r arcsin(sqrt(hav(theta))).
    hav_theta = hav(phi2 - phi1) + np.cos(phi1) * np.cos(phi2) * hav(lam2 - lam1)
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(hav_theta))


def step_speed(fixes: pd.DataFrame) -> np.ndarray:
    """Apparent horizontal speed in km/h from each fix to the next: one value fewer than the fixes.

    Distance on the sphere divided by the elapsed time. The times must be increasing,
    as the clock rule leaves them.
    """
    lat, lon = fixes["lat"].to_numpy(), fixes["lon"].to_numpy()
    # From each fix (lat[:-1], lon[:-1]) to the next (lat[1:], lon[1:]).
    distance = distance_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    return 3.6 * distance / np.diff(fixes["t"].to_numpy())  # m/s -> km/h


def window_speed(fixes: pd.DataFrame, window_s: float) -> np.ndarray:
    """Mean horizontal speed in km/h over a window starting at each fix.

    The window goes from fix i to the first fix j at least window_s seconds later, and the
    speed is d(i, j) / (t_j - t_i). Across a gap the window is longer than window_s. The
    fixes of the last window_s seconds have no such j, so there are fewer values than
    fixes. The times must be increasing, as the clock rule leaves them.
    """
    t = fixes["t"].to_numpy()
    lat, lon = fixes["lat"].to_numpy(), fixes["lon"].to_numpy()
    # For each fix, the index of the first fix at least window_s later; len(t) if none.
    end = np.searchsorted(t, t + window_s)
    start = np.nonzero(end < len(t))[0]  # the fixes that have such an end
    end = end[start]
    distance = distance_m(lat[start], lon[start], lat[end], lon[end])
    return 3.6 * distance / (t[end] - t[start])  # m/s -> km/h


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


def track_speed(fixes: pd.DataFrame, median_max_kmh: float) -> dict:
    """Median step speed in km/h (NaN without steps), and whether the flight is kept
    (speed_ok): if its median is at most median_max_kmh, or if it has no steps."""
    # The same median the threshold was chosen on, in scripts/preprocessing/flight_speeds.py.
    median = speed_summary(fixes)["median_kmh"]
    return {"median_kmh": median, "speed_ok": bool(np.isnan(median) or median <= median_max_kmh)}
