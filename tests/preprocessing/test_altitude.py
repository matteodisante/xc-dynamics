import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.altitude import (
    altitude_channel,
    vertical_speeds,
    vertical_window_speeds,
)

THRESHOLDS = dict(
    gnss_present_min=0.95,
    gnss_min_range_m=30.0,
    baro_witness_present_min=0.95,
    baro_witness_min_range_m=30.0,
    baro_witness_range_tolerance=0.1,
)


def flight(gnss, baro):
    return pd.DataFrame({"gnss_alt": gnss, "baro_alt": baro}, dtype=float)


def test_kept():
    gnss = np.linspace(1000, 1500, 100)
    gnss[50] = np.nan  # one missing value of 100 is allowed
    result = altitude_channel(flight(gnss, gnss), **THRESHOLDS)
    assert result["gnss_ok"] and result["baro_witness"]
    assert result["gnss_present"] == 0.99
    assert result["gnss_range_m"] == 500


def test_stuck_or_missing():
    stuck = np.full(100, 1000.0)
    missing = np.full(100, np.nan)
    assert not altitude_channel(flight(stuck, stuck), **THRESHOLDS)["gnss_ok"]
    result = altitude_channel(flight(missing, missing), **THRESHOLDS)
    assert (result["gnss_present"], result["gnss_range_m"]) == (0, 0)
    assert not result["gnss_ok"] and not result["baro_witness"]


def test_barometer_witness_needs_the_gnss_range():
    gnss = np.linspace(1000, 1500, 100)  # range 500 m
    close = np.linspace(990, 1530, 100)  # range 540 m, within 10%
    pressure = 16000 - 5 * (gnss - 1000)  # moves against GNSS, range 2500
    assert altitude_channel(flight(gnss, close), **THRESHOLDS)["baro_witness"]
    result = altitude_channel(flight(gnss, pressure), **THRESHOLDS)
    assert result["gnss_ok"] and not result["baro_witness"]


def test_vertical_speeds_skip_missing_altitudes_and_splits():
    fixes = pd.DataFrame({
        "t": [0, 1, 3, 4, 5, 6],
        "gnss_alt": [1000, 1002, 1008, np.nan, 1010, 1020],  # no GNSS altitude at 4 s
        "baro_alt": [990, 991, 995, 996, 997, 1000],
        "segment": [0, 0, 0, 0, 0, 1],  # split before 6 s
    })
    w_gnss, w_baro = vertical_speeds(fixes)
    assert list(w_gnss) == [2, 3]
    assert list(w_baro) == [1, 2]


def test_vertical_window_speeds_skip_missing_altitudes_and_splits():
    fixes = pd.DataFrame({
        "t": [0, 1, 2, 3, 4, 5, 6],
        "gnss_alt": [1000, 1002, 1004, np.nan, 1010, 1020, 1030],  # no GNSS altitude at 3 s
        "baro_alt": [1000, 1001, 1002, 1003, 1004, 1005, 1006],
        "segment": [0, 0, 0, 0, 0, 1, 1],  # split before 5 s
    })
    # Windows of 2 s: 0-2 and 2-4 are kept; 1-3 and 3-5 touch the missing altitude,
    # 4-6 crosses the split; 5 and 6 have no fix 2 s later.
    w_gnss, w_baro = vertical_window_speeds(fixes, 2.0)
    assert list(w_gnss) == [2, 3]
    assert list(w_baro) == [1, 1]
