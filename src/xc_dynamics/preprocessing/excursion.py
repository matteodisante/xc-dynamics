"""The excursion rule: delete the fixes a glider could not have reached, and split the
flight where the track does not come back.

The fixes are scanned in order against an anchor, the last fix accepted. A fix is
reachable if its distance from the anchor is at most the top speed times the time
elapsed. When a fix is not, a block opens: if a later fix, within window_s seconds of the
opening, is reachable again, the block is deleted and that fix becomes the anchor;
otherwise the flight is split between the anchor and the block, and a new segment starts
from the block. A block still open at the end of the track is deleted.

The first anchor of each segment is the first fix whose step to the next fix is
reachable, and the fixes before it are deleted, so a wrong fix never becomes an anchor.
"""

import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.speed import distance_m


def excursions(fixes: pd.DataFrame, max_kmh: float, window_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Two masks over the fixes: keep, True for the fixes to keep, and split_before, True on
    the first fix of every segment after the first. The times must be strictly increasing,
    as the clock rule leaves them."""
    t = fixes["t"].to_numpy()
    lat, lon = fixes["lat"].to_numpy(), fixes["lon"].to_numpy()
    n = len(t)
    max_speed = max_kmh / 3.6  # km/h -> m/s
    keep = np.zeros(n, dtype=bool)  # a fix is kept only when the scan accepts it
    split_before = np.zeros(n, dtype=bool)

    # Whether each fix i+1 is reachable from fix i. The anchor is almost always the fix
    # just before, so the scan mostly reads these values instead of computing a distance.
    step_ok = distance_m(lat[:-1], lon[:-1], lat[1:], lon[1:]) <= max_speed * np.diff(t)

    def reachable(a: int, j: int) -> bool:
        """Whether fix j is reachable from the anchor a."""
        if j == a + 1:
            return bool(step_ok[a])
        return bool(distance_m(lat[a], lon[a], lat[j], lon[j]) <= max_speed * (t[j] - t[a]))

    def first_anchor(i: int) -> int:
        """The first fix from i whose step to the next fix is reachable; n if there is none."""
        # Skip fix i while its step to the next is not reachable; stop at the first good one.
        while i < n - 1 and not step_ok[i]:
            i += 1
        return i if i < n - 1 else n

    a = first_anchor(0)
    if a == n:  # no step of the track is reachable: nothing is kept
        return keep, split_before
    keep[a] = True
    j = a + 1
    while j < n:
        if reachable(a, j):
            keep[j] = True
            a = j
            j += 1
            continue
        # Fix j is not reachable: a block opens at j. Look for a later fix that is
        # reachable from the anchor, within window_s seconds of the opening.
        k = j + 1
        while k < n and t[k] - t[j] <= window_s and not reachable(a, k):
            k += 1
        if k == n:
            # The track ends with the block still open: the block is deleted.
            break
        if t[k] - t[j] <= window_s:
            # Fix k comes back: the block j..k-1 is deleted and k becomes the anchor.
            keep[k] = True
            a = k
            j = k + 1
        else:
            # No fix came back within window_s: split, and a new segment starts at j.
            a = first_anchor(j)
            if a == n:
                break
            keep[a] = True
            split_before[a] = True
            j = a + 1
    return keep, split_before
