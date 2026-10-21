import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.airborne import airborne_span, longest_pause
from xc_dynamics.preprocessing.speed import EARTH_RADIUS_M

METRES_PER_DEGREE = EARTH_RADIUS_M * np.pi / 180
MIN_KMH = 15.0  # 4.2 m/s
MIN_S = 30.0
WALK, FLY = 1.0, 10.0  # m/s


def track(step_m_s, segment=0):
    """Fixes one second apart moving north from 45 N, 6 E, step k at speed step_m_s[k]."""
    north = np.concatenate([[0.0], np.cumsum(step_m_s)])
    return pd.DataFrame({
        "t": np.arange(len(north), dtype=float),
        "lat": 45 + north / METRES_PER_DEGREE,
        "lon": 6.0,
        "segment": segment,
    })


def test_ground_before_and_after_is_deleted():
    steps = np.r_[np.full(60, WALK), np.full(100, FLY), np.full(60, WALK)]
    keep = airborne_span(track(steps), MIN_KMH, MIN_S)
    # The first fast step goes from fix 60, the last one reaches fix 160.
    assert list(np.flatnonzero(keep)) == list(range(60, 161))


def test_short_fast_stretch_is_not_a_take_off():
    steps = np.r_[np.full(20, FLY), np.full(40, WALK), np.full(100, FLY)]
    keep = airborne_span(track(steps), MIN_KMH, MIN_S)
    assert np.flatnonzero(keep)[0] == 60


def test_slow_stretch_inside_the_flight_is_kept():
    steps = np.r_[np.full(50, FLY), np.full(40, WALK), np.full(50, FLY)]
    assert airborne_span(track(steps), MIN_KMH, MIN_S).all()


def test_no_long_stretch_deletes_every_fix():
    steps = np.r_[np.full(20, FLY), np.full(20, WALK), np.full(20, FLY)]
    assert not airborne_span(track(steps), MIN_KMH, MIN_S).any()


def test_stretch_does_not_cross_a_split():
    segment = np.r_[np.zeros(20), np.ones(21)]  # 40 s of flight split after 19 s
    keep = airborne_span(track(np.full(40, FLY), segment), MIN_KMH, MIN_S)
    assert not keep.any()


def test_pause_is_the_longest_time_without_a_fast_step():
    steps = np.r_[np.full(40, FLY), np.full(70, WALK), np.full(40, FLY), np.full(10, WALK)]
    assert longest_pause(track(steps), MIN_KMH) == 70


def test_pause_counts_the_time_between_two_segments():
    segment = np.r_[np.zeros(30), np.ones(31)]  # the step of 1 s that joins them is not fast
    assert longest_pause(track(np.full(60, FLY), segment), MIN_KMH) == 1


def test_pause_of_a_flight_without_fast_steps_is_its_whole_duration():
    assert longest_pause(track(np.full(50, WALK)), MIN_KMH) == 50
