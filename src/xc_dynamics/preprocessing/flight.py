"""One flight through the pre-processing, in the order of the thesis.

The excursion rule needs a threshold chosen on the fixes it receives, so the steps before
it can run on their own.
"""

from pathlib import Path

import pandas as pd

from xc_dynamics.preprocessing.altitude import altitude_channel
from xc_dynamics.preprocessing.clean import increasing_time, moving_position
from xc_dynamics.preprocessing.igc import read_igc
from xc_dynamics.preprocessing.speed import track_speed


def before_excursions(
    path: str | Path, altitude: dict, median_max_kmh: float
) -> tuple[pd.DataFrame, dict]:
    """Run one IGC file through the pre-processing up to the excursion rule, excluded;
    return the fixes as that rule receives them and a row of counters.

    altitude holds the thresholds of the altitude channel, median_max_kmh the speed
    threshold of the discipline (configs/preprocessing.yaml). A flight that fails the
    altitude channel stops there: its row has gnss_ok False and no counters of the
    later steps. A flight too fast for the speed rule has speed_ok False.
    """
    fixes = read_igc(path)
    row = {"fixes_read": len(fixes)} | altitude_channel(fixes, **altitude)
    if not row["gnss_ok"]:
        return fixes, row
    # Each rule runs on the fixes the previous one left.
    for name, rule in (("clock", increasing_time), ("repeated", moving_position)):
        # rule is increasing_time, then moving_position. keep has one value per fix:
        # True to keep the fix, False to delete it.
        keep = rule(fixes)
        row[f"{name}_deleted"] = int((~keep).sum())
        fixes = fixes[keep]
    # The speed rule deletes no fix: it only adds median_kmh and speed_ok to the row.
    # row |= d copies every key of the dictionary d into row.
    row |= track_speed(fixes, median_max_kmh)
    return fixes, row
