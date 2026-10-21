"""One flight through the pre-processing, in the order of the thesis.

The excursion rules need thresholds chosen on the fixes they receive, so the steps before
each rule can run on their own.
"""

from pathlib import Path

import pandas as pd

from xc_dynamics.preprocessing.airborne import airborne_span, longest_pause
from xc_dynamics.preprocessing.altitude import altitude_channel, known_altitude
from xc_dynamics.preprocessing.clean import increasing_time, moving_position
from xc_dynamics.preprocessing.excursion import horizontal_excursions, vertical_excursions
from xc_dynamics.preprocessing.igc import read_igc
from xc_dynamics.preprocessing.sampling import sampling_interval
from xc_dynamics.preprocessing.speed import track_speed


def before_horizontal(
    path: str | Path, altitude: dict, median_max_kmh: float
) -> tuple[pd.DataFrame, dict]:
    """Run one IGC file through the pre-processing up to the excursion rule, excluded;
    return the fixes as that rule receives them and a row with the sampling interval of
    the track as read and the counters of the steps.

    altitude holds the thresholds of the altitude channel, median_max_kmh the speed
    threshold of the discipline (configs/preprocessing.yaml). A flight that fails the
    altitude channel stops there: its row has gnss_ok False and no counters of the
    later steps. A flight too fast for the speed rule has speed_ok False.
    """
    fixes = read_igc(path)
    # The sampling interval is a property of the logger, so it is measured before any rule.
    row = {"fixes_read": len(fixes), "sampling_s": sampling_interval(fixes)}
    row |= altitude_channel(fixes, **altitude)
    if not row["gnss_ok"]:
        return fixes, row
    # Each rule runs on the fixes the previous one left.
    rules = (
        ("altitude", known_altitude),
        ("clock", increasing_time),
        ("repeated", moving_position),
    )
    for name, rule in rules:
        # keep has one value per fix: True to keep the fix, False to delete it.
        keep = rule(fixes)
        row[f"{name}_deleted"] = int((~keep).sum())
        fixes = fixes[keep]
    # The speed rule deletes no fix: it only adds median_kmh and speed_ok to the row.
    # row |= d copies every key of the dictionary d into row.
    row |= track_speed(fixes, median_max_kmh)
    return fixes, row


def before_vertical(
    path: str | Path, altitude: dict, median_max_kmh: float, max_kmh: float, window_s: float
) -> tuple[pd.DataFrame, dict]:
    """Run one IGC file through the pre-processing up to the vertical excursion rule,
    excluded; return the fixes as that rule receives them, with a column segment that
    numbers from 0 the pieces the flight was split into, and the row of before_horizontal
    with the fixes deleted and the splits of the horizontal excursion rule.

    max_kmh is the top speed of the discipline and window_s the window W
    (configs/preprocessing.yaml). A flight dropped before the horizontal excursion rule is
    returned as before_horizontal leaves it.
    """
    fixes, row = before_horizontal(path, altitude, median_max_kmh)
    if not (row["gnss_ok"] and row["speed_ok"]):
        return fixes, row
    keep, split_before = horizontal_excursions(fixes, max_kmh, window_s)
    row["horizontal_deleted"] = int((~keep).sum())
    row["horizontal_splits"] = int(split_before.sum())
    # Each split starts a new segment: 0 up to the first split, 1 up to the second, ...
    fixes = fixes[keep].assign(segment=split_before[keep].cumsum())
    return fixes, row


def preprocess(
    path: str | Path,
    altitude: dict,
    median_max_kmh: float,
    max_kmh: float,
    window_s: float,
    max_ms: float,
    airborne: dict,
) -> tuple[pd.DataFrame, dict]:
    """Run one IGC file through every step of the pre-processing; return the fixes kept,
    with a column segment that numbers from 0 the pieces the flight was split into, and the
    row with the counters of every step. In a flight kept the row also has the times
    t_takeoff and t_landing of the first and last fix kept, the seconds ground_before_s and
    ground_after_s cut before and after, and the longest_pause_s between them.

    max_ms is the top vertical speed of the discipline, airborne the keys min_kmh, min_s and
    max_pause_s of the take-off and landing rule (configs/preprocessing.yaml), the other
    thresholds as in before_vertical. A flight dropped by a step is returned as that step leaves it:
    airborne_ok is False if no stretch of it is fast enough, or if it stops flying for
    longer than max_pause_s between the take-off and the landing.
    """
    fixes, row = before_vertical(path, altitude, median_max_kmh, max_kmh, window_s)
    if not (row["gnss_ok"] and row["speed_ok"]):
        return fixes, row
    keep, split_before = vertical_excursions(fixes, max_ms, window_s)
    row["vertical_deleted"] = int((~keep).sum())
    row["vertical_splits"] = int(split_before.sum())
    # Each vertical split shifts by one the numbers of the segments after it.
    segment = fixes["segment"].to_numpy() + split_before.cumsum()
    # A segment can lose all its fixes: factorize numbers those left from 0, without gaps.
    fixes = fixes[keep].assign(segment=pd.factorize(segment[keep])[0])
    # Fixes from the take-off to the landing.
    keep = airborne_span(fixes, airborne["min_kmh"], airborne["min_s"])
    # False if the flight has no fast stretch.
    row["airborne_ok"] = bool(keep.any())
    if not row["airborne_ok"]:
        return fixes, row
    flight = fixes[keep]
    # A flight that stops flying for too long between take-off and landing (a landing and a
    # second take-off, a ride in a vehicle) is not one flight: drop it if its longest pause
    # exceeds max_pause_s.
    row["longest_pause_s"] = longest_pause(flight, airborne["min_kmh"])
    row["airborne_ok"] = bool(row["longest_pause_s"] <= airborne["max_pause_s"])
    if not row["airborne_ok"]:
        return fixes, row
    row["airborne_deleted"] = int((~keep).sum())
    row["t_takeoff"], row["t_landing"] = float(flight["t"].iloc[0]), float(flight["t"].iloc[-1])
    # The time cut before the take-off and after the landing.
    row["ground_before_s"] = row["t_takeoff"] - float(fixes["t"].iloc[0])
    row["ground_after_s"] = float(fixes["t"].iloc[-1]) - row["t_landing"]
    # A segment wholly before the take-off or after the landing has lost all its fixes, and
    # its number is gone. Number the segments left from 0 again, so that none is missing:
    # 1 1 2 2 becomes 0 0 1 1 when segment 0 was on the ground.
    return flight.assign(segment=pd.factorize(flight["segment"])[0]), row
