import numpy as np
import pandas as pd

from xc_dynamics.preprocessing.sampling import sampling_interval


def fixes_at(times):
    """Fixes at the given times, in seconds."""
    return pd.DataFrame({"t": np.asarray(times, dtype=float)})


def test_regular_logger():
    assert sampling_interval(fixes_at(range(0, 100, 5))) == 5


def test_mixed_logger_takes_the_most_frequent_interval():
    # Every second for a minute, as in a thermal, then every 5 s, as in a glide.
    times = np.r_[np.arange(0, 60), np.arange(60, 160, 5)]
    assert sampling_interval(fixes_at(times)) == 1


def test_tie_takes_the_shortest():
    assert sampling_interval(fixes_at([0, 1, 3])) == 1


def test_repeated_and_backward_times_are_left_out():
    # Three fixes per second, as a fast logger writes them in whole seconds, and one
    # time that goes back: only the positive intervals count.
    assert sampling_interval(fixes_at([0, 0, 0, 1, 1, 1, 2, 2, 2, 1, 3])) == 1


def test_one_fix_has_no_interval():
    assert np.isnan(sampling_interval(fixes_at([0])))
