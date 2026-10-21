"""The take-off and landing rule: the flight goes from the first to the last stretch in
which the horizontal speed stays above a threshold for long enough. The fixes before and
after are on the ground and are deleted. A flight that stops flying for too long between
the two is not one flight; longest_pause measures the stop.
"""

import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.speed import step_speed


def fast_steps(fixes: pd.DataFrame, min_kmh: float) -> np.ndarray:
    """A mask over the steps from each fix to the next, True for a step faster than min_kmh
    inside a segment. The fixes need a column segment; a step across a split is never fast."""
    segment = fixes["segment"].to_numpy()
    return (step_speed(fixes) > min_kmh) & (segment[1:] == segment[:-1])


def airborne_span(fixes: pd.DataFrame, min_kmh: float, min_s: float) -> np.ndarray:
    """A mask over the fixes, True from the first fix of the first stretch in which every
    step is faster than min_kmh for at least min_s seconds to the last fix of the last one;
    all False if there is no such stretch. The fixes need strictly increasing times and a
    column segment."""
    t = fixes["t"].to_numpy()
    fast = fast_steps(fixes, min_kmh)
    # Each run of fast steps starts at fix start and ends at fix stop.
    edges = np.diff(np.concatenate([[0], fast.astype(int), [0]]))
    start, stop = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    long = t[stop] - t[start] >= min_s
    keep = np.zeros(len(t), dtype=bool)
    if long.any():
        keep[start[long][0] : stop[long][-1] + 1] = True
    return keep


def longest_pause(fixes: pd.DataFrame, min_kmh: float) -> float:
    """The longest time in seconds, from the first fix to the last, without a step faster
    than min_kmh: before the first fast step, between two, after the last. A step across a
    split is not fast, so the time between two segments is part of a pause. 0 for no fixes."""
    t = fixes["t"].to_numpy()
    if not len(t):
        return 0.0
    fast = np.flatnonzero(fast_steps(fixes, min_kmh))
    # A pause starts at the first fix or where a fast step ends, and ends where the next
    # fast step starts or at the last fix.
    starts = np.concatenate([[t[0]], t[fast + 1]])
    ends = np.concatenate([t[fast], [t[-1]]])
    return float((ends - starts).max())
