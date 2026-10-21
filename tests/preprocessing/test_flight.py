from xc_dynamics.preprocessing.flight import before_horizontal, before_vertical, preprocess

ALTITUDE = dict(
    gnss_present_min=0.95,
    gnss_min_range_m=30.0,
    baro_witness_present_min=0.95,
    baro_witness_min_range_m=30.0,
    baro_witness_range_tolerance=0.1,
)
MEDIAN_MAX_KMH = 70.0
PREPROCESS = dict(max_kmh=100.0, window_s=3.0, max_ms=30.0, min_kmh=15.0, min_s=20.0)


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
    fixes, row = before_horizontal(path, ALTITUDE, MEDIAN_MAX_KMH)
    assert list(fixes.t) == [0, 1, 3]
    assert row["fixes_read"] == 5 and row["gnss_ok"]
    assert (row["clock_deleted"], row["repeated_deleted"]) == (1, 1)


def test_fix_without_gnss_altitude_is_deleted(tmp_path):
    # 20 fixes, one without a GNSS altitude (0 in IGC): 95% present, so the flight is kept.
    records = [b(s, 30000 + 5 * s, 0 if s == 7 else 1000 + 10 * s) for s in range(20)]
    fixes, row = before_horizontal(write(tmp_path, *records), ALTITUDE, MEDIAN_MAX_KMH)
    assert row["gnss_ok"] and row["altitude_deleted"] == 1
    assert 7 not in list(fixes.t) and len(fixes) == 19


def test_flight_without_gnss_altitude_stops_at_the_altitude_channel(tmp_path):
    path = write(tmp_path, b(0, 30000, 0), b(1, 30100, 0), b(2, 30200, 0))
    _, row = before_horizontal(path, ALTITUDE, MEDIAN_MAX_KMH)
    assert not row["gnss_ok"]
    assert "clock_deleted" not in row
    assert row["sampling_s"] == 1  # measured before any rule


def test_speed_rule_flags_a_fast_track_and_deletes_no_fix(tmp_path):
    # A thousandth of a minute of latitude is about 1.85 m and the fixes are 1 s apart:
    # 5 per step is about 33 km/h, 100 per step about 667 km/h.
    slow = write(tmp_path, b(0, 30000, 1000), b(1, 30005, 1100), b(2, 30010, 1200))
    _, row = before_horizontal(slow, ALTITUDE, MEDIAN_MAX_KMH)
    assert row["speed_ok"]
    fast = write(tmp_path, b(0, 30000, 1000), b(1, 30100, 1100), b(2, 30200, 1200))
    fixes, row = before_horizontal(fast, ALTITUDE, MEDIAN_MAX_KMH)
    assert not row["speed_ok"]
    assert len(fixes) == 3


def test_horizontal_excursions_delete_a_spike_and_split_at_a_jump(tmp_path):
    # Steps of 5 thousandths of a minute, about 33 km/h; the fix at 3 s is a spike that
    # comes back at 4 s, the track jumps at 6 s and stays there longer than the window.
    lats = [30000, 30005, 30010, 31000, 30020, 30025, 40000, 40005, 40010, 40015, 40020]
    path = write(tmp_path, *(b(s, lat, 1000 + 10 * s) for s, lat in enumerate(lats)))
    fixes, row = before_vertical(path, ALTITUDE, MEDIAN_MAX_KMH, max_kmh=100.0, window_s=3.0)
    assert list(fixes.t) == [0, 1, 2, 4, 5, 6, 7, 8, 9, 10]
    assert list(fixes.segment) == [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    assert (row["horizontal_deleted"], row["horizontal_splits"]) == (1, 1)


def test_vertical_excursions_delete_a_spike_and_split_at_a_jump(tmp_path):
    # A clean horizontal track climbing at 2 m/s; the GNSS altitude has a spike of 300 m
    # at 10 s that comes back at 11 s, and jumps by 3000 m at 20 s for good.
    gnss = [1000 + 2 * s + 300 * (s == 10) + 3000 * (s >= 20) for s in range(30)]
    path = write(tmp_path, *(b(s, 30000 + 5 * s, z) for s, z in enumerate(gnss)))
    fixes, row = preprocess(path, ALTITUDE, MEDIAN_MAX_KMH, **PREPROCESS)
    assert (row["vertical_deleted"], row["vertical_splits"]) == (1, 1)
    assert list(fixes.t) == [s for s in range(30) if s != 10]
    assert list(fixes.segment) == [0] * 19 + [1] * 10


def ground_flight(tmp_path):
    """10 s at 6.7 km/h, 30 s at 33 km/h climbing at 2 m/s, then 10 s at 6.7 km/h."""
    lat = [30000 + s if s < 10 else 30009 + 5 * (s - 9) if s < 40 else 30159 + (s - 39) for s in range(50)]
    z = [1000 + 2 * min(s, 40) for s in range(50)]
    return write(tmp_path, *(b(s, la, h) for s, (la, h) in enumerate(zip(lat, z))))


def test_ground_before_take_off_and_after_landing_is_deleted(tmp_path):
    fixes, row = preprocess(ground_flight(tmp_path), ALTITUDE, MEDIAN_MAX_KMH, **PREPROCESS)
    assert row["airborne_ok"] and row["airborne_deleted"] == 19
    assert (row["t_takeoff"], row["t_landing"]) == (9, 39)
    assert (row["ground_before_s"], row["ground_after_s"]) == (9, 10)
    assert list(fixes.t) == list(range(9, 40))


def test_flight_without_a_fast_stretch_is_dropped(tmp_path):
    _, row = preprocess(ground_flight(tmp_path), ALTITUDE, MEDIAN_MAX_KMH, **PREPROCESS | dict(min_s=100.0))
    assert not row["airborne_ok"]
    assert "t_takeoff" not in row
