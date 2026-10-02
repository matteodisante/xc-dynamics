"""Download paraglider and hang-glider flights from the FFVL CFD.

For each season the CFD (Coupe Fédérale de Distance) publishes an XML list of the
declared flights, with a link to each .igc track. A season is named by its start
year: 2024 is the season 2024-2025.
"""

import threading
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from curl_cffi import requests

SITE = {"para": "https://parapente.ffvl.fr", "delta": "https://delta.ffvl.fr"}

# XML attribute -> catalog column. The XML has more attributes; these are the useful ones.
CATALOG_COLUMNS = {
    "date": "date",
    "pilot": "pilot",
    "flight_type": "flight_type",
    "distance": "distance_km",
    "points": "points",
    "duration": "duration_s",
    "speed": "speed",
    "takeOff": "takeoff",
    "landing": "landing",
    "depNum": "dept",
    "club": "club",
    "aile": "wing",
    "aile_class": "wing_class",
    "flight_link": "flight_link",
    "igc_tracklog_link": "igc_link",
    "igc_tracklog": "tracklog_id",
    "pilot_link": "pilot_link",
}

_local = threading.local()


def get(url: str, retries: int = 5) -> bytes:
    """Download a URL, retrying with growing pauses. Raises RuntimeError on failure.

    The FFVL site sits behind Cloudflare, which blocks ordinary HTTP clients;
    curl_cffi imitates Chrome's TLS handshake to look like a browser.
    """
    if not hasattr(_local, "session"):  # sessions are not thread-safe: one per thread
        _local.session = requests.Session(impersonate="chrome")
    error = ""
    for attempt in range(retries):
        if attempt:
            time.sleep(2**attempt)  # 2, 4, 8, 16 s
        try:
            response = _local.session.get(url, timeout=60)
        except requests.RequestsError as err:
            error = str(err)  # network problem: try again
            continue
        if response.status_code == 200:
            return response.content
        error = f"HTTP {response.status_code}"
        if response.status_code == 404:  # not on the server: retrying won't help
            break
    raise RuntimeError(f"{url}: {error}")


def save(path: Path, data: bytes) -> None:
    """Write through a temporary file, so an interrupted run never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def season_label(year: int) -> str:
    """Name of the season starting in year: 2024 -> '2024-2025'."""
    return f"{year}-{year + 1}"


def xml_dir(root: Path) -> Path:
    """Folder of the saved flight lists."""
    return root / "raw" / "raw_xml"


def xml_path(root: Path, year: int) -> Path:
    """Saved flight list of a season."""
    return xml_dir(root) / f"{year}.xml"


def igc_dir(root: Path, year: int) -> Path:
    """Folder of the tracks of a season."""
    return root / "raw" / "igc" / season_label(year)


def igc_path(root: Path, year: int, flight: dict) -> Path:
    """Where the track of a flight is saved: {date}_{flight_id}.igc."""
    day = flight["date"] or "0000-00-00"  # a few flights have no date
    return igc_dir(root, year) / f"{day}_{flight['id']}.igc"


def catalog_path(root: Path) -> Path:
    """Where the catalog is saved."""
    return root / "catalog" / "catalog.csv"


def read_flights(root: Path, year: int) -> list[dict]:
    """Flights of a season, each as a dict of its XML attributes."""
    return [f.attrib for f in ET.parse(xml_path(root, year)).iter("flight")]


def has_track(flight: dict) -> bool:
    """True if the flight links to a track file."""
    # Flights without a track link to the bare igcfiles/ folder instead.
    return flight.get("igc_tracklog_link", "").endswith(".igc")


def looks_like_igc(data: bytes) -> bool:
    """True if data starts with an A record and holds B records (GPS fixes)."""
    # This rejects the HTML pages the server sometimes returns instead of a track.
    return data.lstrip().startswith(b"A") and b"\nB" in data


def tracks_on_disk(root: Path, year: int) -> set[Path]:
    """Tracks of a season already downloaded."""
    # One directory listing: checking each file on the exFAT SSD is 40x slower.
    return set(igc_dir(root, year).glob("*.igc"))


def fetch_xml(discipline: str, root: Path, year: int) -> None:
    """Download and save the flight list of a season."""
    save(xml_path(root, year), get(f"{SITE[discipline]}/cfd/liste/{year}?xml=1"))


def missing_tracks(root: Path, year: int) -> dict[Path, str]:
    """Tracks of a season not yet on disk, as {local path: url}."""
    on_disk = tracks_on_disk(root, year)
    missing = {}
    for flight in read_flights(root, year):
        path = igc_path(root, year, flight)
        if has_track(flight) and path not in on_disk:
            missing[path] = flight["igc_tracklog_link"]
    return missing


def download_track(url: str, path: Path) -> str | None:
    """Download and save one track; return an error message, or None on success."""
    try:
        data = get(url)
    except RuntimeError as err:
        return str(err)
    if not looks_like_igc(data):
        return f"{url}: not an IGC file"
    save(path, data)
    return None


def download_tracks(tracks: dict[Path, str], workers: int) -> Iterator[str | None]:
    """Download tracks in parallel, yielding an error message (or None) for each."""
    with ThreadPoolExecutor(workers) as pool:
        yield from pool.map(download_track, tracks.values(), tracks.keys())


def build_catalog(root: Path) -> pd.DataFrame:
    """One row per flight in the saved season lists, with its local track if any."""
    rows = []
    for xml in sorted(xml_dir(root).glob("[0-9]*.xml")):  # skips macOS ._ files
        year = int(xml.stem)
        on_disk = tracks_on_disk(root, year)
        for flight in read_flights(root, year):
            row = {
                "flight_id": flight["id"],
                "season": season_label(year),
                "season_year": year,
            }
            row |= {col: flight.get(attr, "") for attr, col in CATALOG_COLUMNS.items()}
            if not has_track(flight):
                row["igc_link"] = ""
            path = igc_path(root, year, flight)
            row["local_path"] = str(path) if path in on_disk else ""
            rows.append(row)
    return pd.DataFrame(rows)
