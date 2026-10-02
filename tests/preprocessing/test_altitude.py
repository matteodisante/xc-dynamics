import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.altitude import altitude_channel

THRESHOLDS = dict(
    gnss_present_min=0.95,
    gnss_min_range_m=30.0,
    baro_witness_present_min=0.95,
    baro_witness_min_range_m=30.0,
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
