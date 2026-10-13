import numpy as np
import pandas as pd
from pytest import approx

from xc_dynamics.preprocessing.speed import (
    EARTH_RADIUS_M,
    speed_summary,
    step_speed,
    track_speed,
    window_speed,
)

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


def test_slow_flight_with_a_few_spikes_is_kept():
    # Two steps at 360 km/h do not move the median of a flight at 36 km/h.
    result = track_speed(northward([36] * 18 + [360] * 2), median_max_kmh=110)
    assert result["median_kmh"] == approx(36)
    assert result["speed_ok"]


def test_flight_always_fast_is_dropped():
    result = track_speed(northward([150] * 20), median_max_kmh=110)
    assert result["median_kmh"] == approx(150)
    assert not result["speed_ok"]


def test_threshold_falls_between_just_below_and_just_above():
    # Not exactly 110: the speed recomputed from degrees carries a tiny rounding error.
    assert track_speed(northward([109.9] * 20), median_max_kmh=110)["speed_ok"]
    assert not track_speed(northward([110.1] * 20), median_max_kmh=110)["speed_ok"]


def test_flight_without_steps_is_kept():
    result = track_speed(northward([]), median_max_kmh=110)
    assert np.isnan(result["median_kmh"]) and result["speed_ok"]


def test_window_speed_of_a_steady_flight():
    # 31 fixes one second apart: the last 20 seconds start no window.
    speeds = window_speed(northward([36] * 30), window_s=20)
    assert len(speeds) == 11
    assert speeds == approx([36] * 11)


def test_spike_barely_moves_the_window_speed():
    # 10 m/s north, fix 20 pushed 100 m ahead: the step into it covers 110 m in 1 s,
    # the window 0 -> 20 covers 300 m in 20 s, the window 20 -> 40 covers 100 m.
    fixes = northward([36] * 40)
    fixes.loc[20, "lat"] += 100 / METRES_PER_DEGREE
    assert step_speed(fixes).max() == approx(396)
    speeds = window_speed(fixes, window_s=20)
    assert speeds[0] == approx(54) and speeds[20] == approx(18)
    assert speeds[1:20] == approx([36] * 19)


def test_window_across_a_gap_uses_its_real_duration():
    # 10 m/s north with a gap from 2 s to 30 s: the windows from 0, 1 and 2 s all end
    # at 30 s, and their speed is the distance over the time really elapsed.
    t = np.array([0.0, 1, 2, 30, 31])
    lat = 45 + 10 * t / METRES_PER_DEGREE
    speeds = window_speed(pd.DataFrame({"t": t, "lat": lat, "lon": 6.0}), window_s=20)
    assert speeds == approx([36, 36, 36])
