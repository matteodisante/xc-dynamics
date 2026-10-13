import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.excursion import excursions
from xc_dynamics.preprocessing.speed import EARTH_RADIUS_M

METRES_PER_DEGREE = EARTH_RADIUS_M * np.pi / 180
MAX_KMH = 100.0  # 27.8 m/s
WINDOW_S = 20.0


def track(east_m, north_m):
    """Fixes one second apart, at the given positions in metres east and north of 45 N, 6 E."""
    east, north = np.asarray(east_m, dtype=float), np.asarray(north_m, dtype=float)
    return pd.DataFrame({
        "t": np.arange(len(east), dtype=float),
        "lat": 45 + north / METRES_PER_DEGREE,
        "lon": 6 + east / (METRES_PER_DEGREE * np.cos(np.radians(45))),
    })


def northward(n, speed_m_s=10.0):
    """n fixes flying north at a steady speed: east and north positions in metres."""
    return np.zeros(n), speed_m_s * np.arange(n)


def test_steady_flight_is_untouched():
    keep, split_before = excursions(track(*northward(50)), MAX_KMH, WINDOW_S)
    assert keep.all() and not split_before.any()


def test_spike_is_deleted():
    east, north = northward(50)
    east[20] = 300
    keep, split_before = excursions(track(east, north), MAX_KMH, WINDOW_S)
    assert list(np.flatnonzero(~keep)) == [20]
    assert not split_before.any()


def test_block_that_comes_back_is_deleted():
    east, north = northward(50)
    east[20:23] = 300
    keep, split_before = excursions(track(east, north), MAX_KMH, WINDOW_S)
    assert list(np.flatnonzero(~keep)) == [20, 21, 22]
    assert not split_before.any()


def test_jump_that_does_not_come_back_splits_the_flight():
    east, north = northward(80)
    east[30:] = 3000  # from fix 30 the track goes on 3 km to the east
    keep, split_before = excursions(track(east, north), MAX_KMH, WINDOW_S)
    assert keep.all()
    assert list(np.flatnonzero(split_before)) == [30]


def test_wrong_first_fix_is_deleted():
    east, north = northward(50)
    east[0] = 300_000  # an old position, 300 km away
    keep, split_before = excursions(track(east, north), MAX_KMH, WINDOW_S)
    assert list(np.flatnonzero(~keep)) == [0]
    assert not split_before.any()


def test_block_open_at_the_end_is_deleted():
    east, north = northward(40)
    east[37:] = 2000
    keep, split_before = excursions(track(east, north), MAX_KMH, WINDOW_S)
    assert list(np.flatnonzero(~keep)) == [37, 38, 39]
    assert not split_before.any()


def test_spike_after_a_jump_moves_the_start_of_the_new_segment():
    east, north = northward(80)
    east[30:] = 3000
    east[30] = 3500  # the first fix after the jump is itself a spike
    keep, split_before = excursions(track(east, north), MAX_KMH, WINDOW_S)
    assert list(np.flatnonzero(~keep)) == [30]
    assert list(np.flatnonzero(split_before)) == [31]


def test_real_flight_faster_than_the_top_speed_for_longer_than_the_window_is_split():
    # 20 steps at 10 m/s, 60 at 35 m/s (126 km/h), 20 at 10 m/s. No fast step is
    # reachable, so the fast stretch is deleted and the flight split after it: the top
    # speed must lie above every real speed.
    speeds = [10.0] * 20 + [35.0] * 60 + [10.0] * 20
    north = np.r_[0, np.cumsum(speeds)]
    keep, split_before = excursions(track(np.zeros(len(north)), north), MAX_KMH, WINDOW_S)
    assert list(np.flatnonzero(~keep)) == list(range(21, 80))
    assert list(np.flatnonzero(split_before)) == [80]
