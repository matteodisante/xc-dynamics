import numpy as np
import pandas as pd
from pytest import approx

from xc_dynamics.preprocessing.speed import EARTH_RADIUS_M, speed_summary, step_speed, track_speed

METRES_PER_DEGREE = EARTH_RADIUS_M * np.pi / 180


def northward(speeds_kmh):
    """Fixes one second apart, flying north at the given speeds (km/h)."""
    metres = np.r_[0, np.cumsum(speeds_kmh)] / 3.6  # each step lasts 1 s
    lat = 45 + metres / METRES_PER_DEGREE
    return pd.DataFrame({"t": np.arange(len(lat), dtype=float), "lat": lat, "lon": 6.0})


def test_step_speed_along_a_meridian():
    assert step_speed(northward([36, 72, 108])) == approx([36, 72, 108])


def test_step_speed_along_a_parallel_shrinks_with_latitude():
    # At 60 degrees a degree of longitude is half as long as at the equator.
    fixes = pd.DataFrame({"t": [0.0, 10.0], "lat": [60.0, 60.0], "lon": [6.0, 6.001]})
    metres = METRES_PER_DEGREE * 0.001 * 0.5
    assert step_speed(fixes) == approx([3.6 * metres / 10], rel=1e-6)


def test_speed_summary():
    summary = speed_summary(northward([10, 20, 30, 40, 50, 60, 70, 80, 90, 100]))
    assert summary["steps"] == 10
    assert summary["median_kmh"] == approx(55)
    assert summary["p90_kmh"] == approx(91)  # 90 + 0.1 of the way to 100


def test_speed_summary_without_steps():
    summary = speed_summary(northward([]))
    assert summary["steps"] == 0
    assert np.isnan(summary["median_kmh"]) and np.isnan(summary["p90_kmh"])


def test_few_fast_steps_keep_the_flight():
    result = track_speed(northward([36] * 18 + [360] * 2), max_kmh=108, fast_share_max=0.10)
    assert result["fast_share"] == approx(0.10)
    assert result["speed_ok"]


def test_mostly_fast_track_is_dropped():
    result = track_speed(northward([36] * 17 + [360] * 3), max_kmh=108, fast_share_max=0.10)
    assert result["fast_share"] == approx(0.15)
    assert not result["speed_ok"]


def test_no_steps_keep_the_flight():
    assert track_speed(northward([]), max_kmh=108, fast_share_max=0.10) == {"fast_share": 0.0, "speed_ok": True}
