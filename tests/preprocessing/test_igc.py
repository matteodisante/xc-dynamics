import numpy as np
import pytest

from xc_dynamics.preprocessing.igc import read_igc


def write(tmp_path, *records):
    path = tmp_path / "f.igc"
    path.write_bytes(("AXGD123\r\nHFDTE010724\r\n" + "\r\n".join(records) + "\r\n").encode())
    return path


def test_fields(tmp_path):
    fixes = read_igc(write(tmp_path, "B1200004530000N00615000WA0100001050"))
    fix = fixes.iloc[0]
    assert fix.t == 0
    assert fix.lat == pytest.approx(45.5)
    assert fix.lon == pytest.approx(-6.25)
    assert fix.valid
    assert (fix.baro_alt, fix.gnss_alt) == (1000, 1050)


def test_bad_records(tmp_path):
    fixes = read_igc(write(
        tmp_path,
        "B1200004530000N00615000EA0100001050",
        "B1260004530000N00615000EA0100001050",  # 60 minutes
        "B1200014590000N00615000EA0100001050",  # 90 arc-minutes
        "B1200024530000N00615000EV00000     ",  # no fix, no altitudes
    ))
    assert list(fixes.t) == [0, 2]
    assert not fixes.valid.iloc[1]
    assert np.isnan(fixes.baro_alt.iloc[1]) and np.isnan(fixes.gnss_alt.iloc[1])


def test_midnight(tmp_path):
    fixes = read_igc(write(
        tmp_path,
        "B2359594530000N00615000EA0100001050",
        "B0000014530000N00615000EA0100001050",
        "B0000004530000N00615000EA0100001050",  # a step back: kept
    ))
    assert list(fixes.t) == [0, 2, 1]


def test_no_fixes(tmp_path):
    assert read_igc(write(tmp_path)).empty
