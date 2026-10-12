"""Rules of the pre-processing that delete fixes.

Each rule takes the fixes as read by `read_igc` and returns a boolean mask, True for
the fixes to keep. The rules are applied in order, each on the fixes the previous
ones left.
"""

import numpy as np
import pandas as pd


def increasing_time(fixes: pd.DataFrame) -> np.ndarray:
    """The clock rule: keep a fix only if its time is later than that of every fix kept before it.

    A repeated second keeps its first fix. A backward step is dropped, and so is
    every fix after it until the clock passes the latest time already kept.
    """
    t = fixes["t"].to_numpy()
    # Running maximum of all timestamps before the current fix.
    latest_before = np.maximum.accumulate(t)[:-1]
    keep = np.ones(len(t), dtype=bool)  # the first fix has nothing before it
    keep[1:] = t[1:] > latest_before
    return keep


def moving_position(fixes: pd.DataFrame) -> np.ndarray:
    """The repeated-position rule: delete a fix whose latitude and longitude equal those of the fix before it.

    The recorder repeats its last position while the clock runs, so the fix is not a
    new measurement. In a run of identical positions only the first fix is kept.
    """
    lat, lon = fixes["lat"].to_numpy(), fixes["lon"].to_numpy()
    # Entry j: fix j+1 has the same latitude and longitude as fix j (exact, same IGC digits).
    same_as_before = (lat[1:] == lat[:-1]) & (lon[1:] == lon[:-1])
    keep = np.ones(len(lat), dtype=bool)  # the first fix has nothing before it
    # Keep each fix only if its position differs from the previous one.
    keep[1:] = ~same_as_before
    return keep
