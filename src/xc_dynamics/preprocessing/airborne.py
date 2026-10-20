"""The take-off and landing rule: the flight goes from the first to the last stretch in
which the horizontal speed stays above a threshold for long enough. The fixes before and
after are on the ground and are deleted.
"""

import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.speed import step_speed


def airborne(fixes: pd.DataFrame, min_kmh: float, min_s: float) -> np.ndarray:
    """A mask over the fixes, True from the first fix of the first stretch in which every
    step is faster than min_kmh for at least min_s seconds to the last fix of the last one;
    all False if there is no such stretch. Steps are taken inside a segment, never across a
    split. The fixes need strictly increasing times and a column segment."""
    t = fixes["t"].to_numpy()
    segment = fixes["segment"].to_numpy()
    # Step k goes from fix k to fix k+1.
    fast = (step_speed(fixes) > min_kmh) & (segment[1:] == segment[:-1])
    # Each run of fast steps starts at fix start and ends at fix stop.
    edges = np.diff(np.concatenate([[0], fast.astype(int), [0]]))
    start, stop = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    long = t[stop] - t[start] >= min_s
    keep = np.zeros(len(t), dtype=bool)
    if long.any():
        keep[start[long][0] : stop[long][-1] + 1] = True
    return keep
