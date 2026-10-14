from xc_dynamics.preprocessing.flight import before_excursions

ALTITUDE = dict(
    gnss_present_min=0.95,
    gnss_min_range_m=30.0,
    baro_witness_present_min=0.95,
    baro_witness_min_range_m=30.0,
)
MEDIAN_MAX_KMH = 70.0


def b(second, lat_milliminutes, gnss):
    """A B record at 12:00:<second>, latitude 45 degrees and the given minutes x 1000."""
    return f"B1200{second:02d}45{lat_milliminutes:05d}N00615000EA01000{gnss:05d}"


def write(tmp_path, *records):
    path = tmp_path / "f.igc"
    path.write_bytes(("AXGD123\r\nHFDTE010724\r\n" + "\r\n".join(records) + "\r\n").encode())
    return path


def test_clock_then_repeated_positions(tmp_path):
    path = write(
        tmp_path,
        b(0, 30000, 1000),
        b(1, 30100, 1100),
        b(1, 30200, 1100),  # same second: the clock deletes it
        b(2, 30100, 1100),  # same position as the fix kept before it
        b(3, 30300, 1200),
    )
    fixes, row = before_excursions(path, ALTITUDE, MEDIAN_MAX_KMH)
    assert list(fixes.t) == [0, 1, 3]
    assert row["fixes_read"] == 5 and row["gnss_ok"]
    assert (row["clock_deleted"], row["repeated_deleted"]) == (1, 1)


def test_flight_without_gnss_altitude_stops_at_the_altitude_channel(tmp_path):
    path = write(tmp_path, b(0, 30000, 0), b(1, 30100, 0), b(2, 30200, 0))
    _, row = before_excursions(path, ALTITUDE, MEDIAN_MAX_KMH)
    assert not row["gnss_ok"]
    assert "clock_deleted" not in row
    assert row["sampling_s"] == 1  # measured before any rule


def test_speed_rule_flags_a_fast_track_and_deletes_no_fix(tmp_path):
    # A thousandth of a minute of latitude is about 1.85 m and the fixes are 1 s apart:
    # 5 per step is about 33 km/h, 100 per step about 667 km/h.
    slow = write(tmp_path, b(0, 30000, 1000), b(1, 30005, 1100), b(2, 30010, 1200))
    _, row = before_excursions(slow, ALTITUDE, MEDIAN_MAX_KMH)
    assert row["speed_ok"]
    fast = write(tmp_path, b(0, 30000, 1000), b(1, 30100, 1100), b(2, 30200, 1200))
    fixes, row = before_excursions(fast, ALTITUDE, MEDIAN_MAX_KMH)
    assert not row["speed_ok"]
    assert len(fixes) == 3
