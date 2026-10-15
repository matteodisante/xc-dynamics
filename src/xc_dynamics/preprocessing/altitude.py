"""The altitude channel of the pre-processing.

The analysis uses the GNSS altitude. A flight is kept only if that channel has a
value at most fixes and actually moves, and in a flight kept the fixes without a GNSS
altitude are deleted. The pressure altitude is never used in its
place: it only serves as a witness in later steps, if it passes the same two tests and
its range agrees with the GNSS range.
"""

import numpy as np
import pandas as pd


def presence_and_range(alt: pd.Series) -> tuple[float, float]:
    """Fraction of fixes with an altitude, and the altitude range in metres (0 if none)."""
    span = alt.max() - alt.min()
    return float(alt.notna().mean()), 0.0 if pd.isna(span) else float(span)


def altitude_channel(
    fixes: pd.DataFrame,
    gnss_present_min: float,
    gnss_min_range_m: float,
    baro_witness_present_min: float,
    baro_witness_min_range_m: float,
    baro_witness_range_tolerance: float,
) -> dict:
    """Presence and range of both channels, whether the flight is kept (gnss_ok)
    and whether its barometer can act as a witness (baro_witness)."""
    gnss_present, gnss_range = presence_and_range(fixes["gnss_alt"])
    baro_present, baro_range = presence_and_range(fixes["baro_alt"])
    return {
        "gnss_present": gnss_present,
        "gnss_range_m": gnss_range,
        "baro_present": baro_present,
        "baro_range_m": baro_range,
        "gnss_ok": gnss_present >= gnss_present_min and gnss_range >= gnss_min_range_m,
        "baro_witness": baro_present >= baro_witness_present_min
        and baro_range >= baro_witness_min_range_m
        # Written without a ratio, so a flat GNSS channel does not divide by zero.
        and abs(baro_range - gnss_range) <= baro_witness_range_tolerance * gnss_range,
    }


def known_altitude(fixes: pd.DataFrame) -> np.ndarray:
    """True for the fixes with a GNSS altitude, the ones to keep."""
    return fixes["gnss_alt"].notna().to_numpy()


def vertical_speeds(fixes: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Vertical speed in m/s of the GNSS and of the pressure altitude, from each fix to the
    next of the same segment, on the steps where both channels have a value at both ends.

    The fixes are those before_vertical returns: strictly increasing times and a column
    segment.
    """
    dt = np.diff(fixes["t"].to_numpy())
    dz_gnss = np.diff(fixes["gnss_alt"].to_numpy())
    dz_baro = np.diff(fixes["baro_alt"].to_numpy())
    # np.diff(segment) is 0 between fixes of the same segment and 1 across a split, a jump
    # that is not real motion; a missing altitude at either end makes dz NaN.
    ok = (np.diff(fixes["segment"].to_numpy()) == 0) & ~np.isnan(dz_gnss) & ~np.isnan(dz_baro)
    return dz_gnss[ok] / dt[ok], dz_baro[ok] / dt[ok]


def vertical_window_speeds(fixes: pd.DataFrame, window_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Mean vertical speed in m/s of the GNSS and of the pressure altitude over a window
    starting at each fix, on the windows inside one segment where both channels have a
    value at both ends.

    The window goes from fix i to the first fix j at least window_s seconds later, as in
    window_speed. The fixes are those before_vertical returns.
    """
    t = fixes["t"].to_numpy()
    segment = fixes["segment"].to_numpy()
    gnss, baro = fixes["gnss_alt"].to_numpy(), fixes["baro_alt"].to_numpy()
    # For each fix, the index of the first fix at least window_s later; len(t) if none.
    end = np.searchsorted(t, t + window_s)
    start = np.nonzero(end < len(t))[0]  # the fixes that have such an end
    end = end[start]
    dt = t[end] - t[start]
    dz_gnss, dz_baro = gnss[end] - gnss[start], baro[end] - baro[start]
    ok = (segment[end] == segment[start]) & ~np.isnan(dz_gnss) & ~np.isnan(dz_baro)
    return dz_gnss[ok] / dt[ok], dz_baro[ok] / dt[ok]
