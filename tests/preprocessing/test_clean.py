import pandas as pd

from xc_dynamics.preprocessing.clean import increasing_time, moving_position


def kept_times(t):
    fixes = pd.DataFrame({"t": t}, dtype=float)
    return fixes.t[increasing_time(fixes)].tolist()


def test_increasing_time_is_untouched():
    assert kept_times([0, 1, 2, 5, 6]) == [0, 1, 2, 5, 6]


def test_repeated_second_keeps_the_first_fix():
    keep = increasing_time(pd.DataFrame({"t": [0.0, 1.0, 1.0, 1.0, 2.0]}))
    assert keep.tolist() == [True, True, False, False, True]


def test_backward_step_drops_fixes_until_the_clock_catches_up():
    assert kept_times([0, 1, 2, 3, 1, 2, 3, 4, 5]) == [0, 1, 2, 3, 4, 5]


def test_forward_glitch_drops_the_good_fixes_behind_it():
    # The rule trusts the fixes it already kept: 100 stays, so 2 and 3 are the ones lost.
    assert kept_times([0, 1, 100, 2, 3, 101]) == [0, 1, 100, 101]


def test_no_fixes_and_one_fix():
    assert kept_times([]) == []
    assert kept_times([7]) == [7]


def moving_mask(lat, lon):
    return moving_position(pd.DataFrame({"lat": lat, "lon": lon})).tolist()


def test_distinct_positions_are_untouched():
    assert moving_mask([45.0, 45.1, 45.2], [6.0, 6.0, 6.0]) == [True, True, True]


def test_run_of_identical_positions_keeps_the_first_fix():
    assert moving_mask([45.0, 45.0, 45.0, 45.1], [6.0, 6.0, 6.0, 6.0]) == [True, False, False, True]


def test_one_coordinate_changing_is_enough_to_keep_the_fix():
    assert moving_mask([45.0, 45.0, 45.1], [6.0, 6.1, 6.1]) == [True, True, True]


def test_returning_to_an_earlier_position_is_kept():
    assert moving_mask([45.0, 45.1, 45.0], [6.0, 6.0, 6.0]) == [True, True, True]


def test_no_fixes_and_one_fix_for_positions():
    assert moving_mask([], []) == []
    assert moving_mask([45.0], [6.0]) == [True]
