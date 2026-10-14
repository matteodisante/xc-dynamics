"""The sampling interval of a track: how often its logger records a fix."""

import numpy as np
import pandas as pd


def sampling_interval(fixes: pd.DataFrame) -> float:
    """The most frequent positive time between consecutive fixes, in seconds, the shortest
    on a tie; NaN if there is none. Intervals of zero or less (repeated or backward times)
    are left out, so the fixes can be taken as read. IGC times are whole seconds, so the
    interval is too."""
    dt = np.diff(fixes["t"].to_numpy())
    dt = dt[dt > 0]
    if not len(dt):
        return np.nan
    # np.unique lists the intervals from the shortest up, each with how often it occurs.
    # argmax returns the position of the first of the most frequent ones, so on a tie the
    # shortest interval wins.
    intervals, counts = np.unique(dt, return_counts=True)
    return float(intervals[np.argmax(counts)])
