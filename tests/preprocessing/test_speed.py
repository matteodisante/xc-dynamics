import numpy as np
import pandas as pd
from pytest import approx

from xc_dynamics.preprocessing.speed import (
    EARTH_RADIUS_M,
    speed_summary,
    step_speed,
    step_straightness,
    track_speed,
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


def test_straight_track_has_straightness_one():
    s = step_straightness(northward([36, 72, 108, 36]))
    assert np.isnan(s[0]) and np.isnan(s[-1])  # end steps lack a neighbour
    assert s[1:-1] == approx([1, 1])


def test_spike_lowers_both_steps_that_touch_it():
    # Along a meridian distances are proportional to latitude differences. The third fix
    # is a spike: from 45.001 to 45.002 the track goes out to 45.010 and back, so the
    # straightness there is 0.001 / (0.009 + 0.008) = 1/17.
    lat = [45.000, 45.001, 45.010, 45.002, 45.003]
    fixes = pd.DataFrame({"t": np.arange(5.0), "lat": lat, "lon": 6.0})
    s = step_straightness(fixes)
    assert np.isnan(s[0]) and np.isnan(s[-1])
    assert s[1:-1] == approx([1 / 17, 1 / 17])
