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

The scan judges one coordinate through its distance: excursions applies it to the
horizontal position, vertical_excursions to the GNSS altitude inside each segment that
the horizontal scan left.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.speed import distance_m


def scan(
    t: np.ndarray, distance: Callable, max_speed: float, window_s: float
) -> tuple[np.ndarray, np.ndarray]:
    """The excursion rule on one coordinate. distance(i, j) is the distance from fix i to
    fix j, for two indices or two arrays of indices, in the unit of max_speed times one
    second. Two masks over the fixes: keep, True for the fixes to keep, and split_before,
    True on the first fix of every segment after the first. The times must be strictly
    increasing."""
    n = len(t)
    keep = np.zeros(n, dtype=bool)  # a fix is kept only when the scan accepts it
    split_before = np.zeros(n, dtype=bool)

    # Whether each fix i+1 is reachable from fix i. The anchor is almost always the fix
    # just before, so the scan mostly reads these values instead of computing a distance.
    step_ok = distance(np.arange(n - 1), np.arange(1, n)) <= max_speed * np.diff(t)

    def reachable(a: int, j: int) -> bool:
        """Whether fix j is reachable from the anchor a."""
        if j == a + 1:
            return bool(step_ok[a])
        return bool(distance(a, j) <= max_speed * (t[j] - t[a]))

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


def excursions(fixes: pd.DataFrame, max_kmh: float, window_s: float) -> tuple[np.ndarray, np.ndarray]:
    """The scan on the horizontal position, with the distance on the sphere. Two masks over
    the fixes: keep, True for the fixes to keep, and split_before, True on the first fix of
    every segment after the first. The times must be strictly increasing, as the clock rule
    leaves them."""
    lat, lon = fixes["lat"].to_numpy(), fixes["lon"].to_numpy()

    def distance(i, j):
        """Distance in metres on the sphere from fix i to fix j."""
        return distance_m(lat[i], lon[i], lat[j], lon[j])

    return scan(fixes["t"].to_numpy(), distance, max_kmh / 3.6, window_s)  # km/h -> m/s


def vertical_excursions(fixes: pd.DataFrame, max_ms: float, window_s: float) -> tuple[np.ndarray, np.ndarray]:
    """The scan on the GNSS altitude, with the vertical distance, inside each segment. Two
    masks over the fixes: keep, True for the fixes to keep, and split_before, True on the
    first fix of every new segment the scan starts. The fixes are those before_vertical
    returns: strictly increasing times, a GNSS altitude on every fix, a column segment."""
    t = fixes["t"].to_numpy()
    z = fixes["gnss_alt"].to_numpy()
    segment = fixes["segment"].to_numpy()
    keep = np.zeros(len(t), dtype=bool)
    split_before = np.zeros(len(t), dtype=bool)
    for s in np.unique(segment):
        i = np.flatnonzero(segment == s)  # the fixes of this segment, in order
        z_s = z[i]

        def distance(p, q):
            """Vertical distance in metres from fix p to fix q of the segment."""
            return np.abs(z_s[q] - z_s[p])

        keep[i], split_before[i] = scan(t[i], distance, max_ms, window_s)
    return keep, split_before
