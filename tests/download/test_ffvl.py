from xc_dynamics.download import ffvl

XML = b"""<ffvldata><flights>
<flight id="1" date="2024-07-01" pilot="A" igc_tracklog_link="https://x/files/a.igc"/>
<flight id="2" date="" pilot="B" igc_tracklog_link="https://x/files/"/>
</flights></ffvldata>"""


def make_season(root):
    """Save a season list with one flight with a track and one without; return the track path."""
    ffvl.save(ffvl.xml_path(root, 2024), XML)
    return ffvl.igc_path(root, 2024, ffvl.read_flights(root, 2024)[0])


def test_looks_like_igc():
    assert ffvl.looks_like_igc(b"AXGD123\r\nHFDTE010724\r\nB1200004500000N00600000EA0100001000\r\n")
    assert not ffvl.looks_like_igc(b"<!DOCTYPE html><title>Just a moment...</title>")
    assert not ffvl.looks_like_igc(b"AXGD123\r\nHFDTE010724\r\n")  # no fixes


def test_missing_tracks(tmp_path):
    track = make_season(tmp_path)
    assert ffvl.missing_tracks(tmp_path, 2024) == {track: "https://x/files/a.igc"}
    ffvl.save(track, b"A")
    assert ffvl.missing_tracks(tmp_path, 2024) == {}


def test_catalog(tmp_path):
    track = make_season(tmp_path)
    ffvl.save(track, b"A")

    catalog = ffvl.build_catalog(tmp_path)

    assert track.name == "2024-07-01_1.igc"
    assert list(catalog.flight_id) == ["1", "2"]
    assert list(catalog.igc_link) == ["https://x/files/a.igc", ""]
    assert list(catalog.local_path) == [str(track), ""]
