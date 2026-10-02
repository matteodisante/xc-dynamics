"""Step (i) of the pre-processing: the altitude channel.

The analysis uses the GNSS altitude. A flight is kept only if that channel has a
value at most fixes and actually moves. The pressure altitude is never used in its
place: it only serves as a witness in later steps, if it passes the same two tests.
"""

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
        and baro_range >= baro_witness_min_range_m,
    }
