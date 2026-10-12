import numpy as np
import pandas as pd
from pytest import approx

from xc_dynamics.preprocessing.speed import EARTH_RADIUS_M, step_speed, track_speed

METRES_PER_DEGREE = EARTH_RADIUS_M * np.pi / 180


def northward(speeds):
    """Fixes one second apart, flying north at the given speeds (m/s)."""
    lat = 45 + np.r_[0, np.cumsum(speeds)] / METRES_PER_DEGREE
    return pd.DataFrame({"t": np.arange(len(lat), dtype=float), "lat": lat, "lon": 6.0})


def test_step_speed_along_a_meridian():
    assert step_speed(northward([10, 20, 30])) == approx([10, 20, 30])


def test_step_speed_along_a_parallel_shrinks_with_latitude():
    # At 60 degrees a degree of longitude is half as long as at the equator.
    fixes = pd.DataFrame({"t": [0.0, 10.0], "lat": [60.0, 60.0], "lon": [6.0, 6.001]})
    assert step_speed(fixes) == approx([METRES_PER_DEGREE * 0.001 * 0.5 / 10], rel=1e-6)


def test_few_fast_steps_keep_the_flight():
    result = track_speed(northward([10] * 18 + [100] * 2), max_m_s=30, fast_share_max=0.10)
    assert result["fast_share"] == approx(0.10)
    assert result["speed_ok"]


def test_mostly_fast_track_is_dropped():
    result = track_speed(northward([10] * 17 + [100] * 3), max_m_s=30, fast_share_max=0.10)
    assert result["fast_share"] == approx(0.15)
    assert not result["speed_ok"]


def test_no_steps_keep_the_flight():
    assert track_speed(northward([]), max_m_s=30, fast_share_max=0.10) == {"fast_share": 0.0, "speed_ok": True}
