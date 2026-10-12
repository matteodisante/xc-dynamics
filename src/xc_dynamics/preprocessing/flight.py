"""One flight through the pre-processing, in the order of the thesis.

For now the steps written so far: reading, altitude channel, clock and repeated
positions.
"""

from pathlib import Path

import pandas as pd

from xc_dynamics.preprocessing.altitude import altitude_channel
from xc_dynamics.preprocessing.clean import increasing_time, moving_position
from xc_dynamics.preprocessing.igc import read_igc


def preprocess(path: str | Path, altitude: dict) -> tuple[pd.DataFrame, dict]:
    """Run one IGC file through the steps; return the fixes left and a row of counters.

    altitude holds the thresholds of the altitude channel (configs/preprocessing.yaml).
    A flight that fails the altitude channel stops there: its row has gnss_ok False
    and no counters of the later steps.
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
    return fixes, row
