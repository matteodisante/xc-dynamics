"""Read the GPS fixes of an IGC file.

Each fix is a B record with fixed columns (FAI/IGC standard):

    B HHMMSS DDMMmmmN DDDMMmmmE V PPPPP GGGGG ...

UTC time, latitude and longitude (degrees, minutes x 1000, hemisphere), a validity
flag (A = 3D fix; V = 2D fix or no GNSS data, so no valid GNSS altitude), pressure
and GNSS altitude in metres.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

# MULTILINE: ^ matches at the start of every line, so findall on the whole file yields one match per B record.
B_RECORD = re.compile(r"^B(\d{6})(\d{7})([NS])(\d{8})([EW])(.)(.{5})(.{5})", re.MULTILINE)
FIELDS = ["time", "lat", "ns", "lon", "ew", "flag", "baro", "gnss"]


def degrees(value: pd.Series, hemisphere: pd.Series) -> np.ndarray:
    """Signed degrees from DDMMmmm or DDDMMmmm; NaN if the minutes are 60 or more."""
    x = value.astype(int).to_numpy()
    # The last 5 digits are the minutes in thousandths (MMmmm): 5206343 -> 06343 -> 6.343.
    minutes = x % 100000 / 1000
    deg = np.where(minutes < 60, x // 100000 + minutes / 60, np.nan)
    return np.where(hemisphere.isin(["S", "W"]), -deg, deg)


def altitude(field: pd.Series) -> np.ndarray:
    """Altitude in metres; NaN if the field is blank, malformed or 0 (IGC for missing)."""
    # Text to number ("00587" -> 587); blank or malformed fields become NaN, and so does 0.
    return pd.to_numeric(field, errors="coerce").replace(0, np.nan).to_numpy()


def read_igc(path: str | Path) -> pd.DataFrame:
    """One row per fix: t (seconds from the first fix), lat, lon, valid, baro_alt, gnss_alt.

    A record with an impossible time or position is skipped. A bad altitude only
    costs the altitude: the fix keeps its time and position.
    """
    # Read the file as text (latin-1 decodes any byte) and turn every \r into \n, so all line ends are \n.
    text = Path(path).read_bytes().decode("latin-1").replace("\r", "\n")
    # Find every B record and put them in a table: one row per fix, one text column per field.
    b = pd.DataFrame(B_RECORD.findall(text), columns=FIELDS)
    hhmmss = b.time.astype(int).to_numpy()
    # Split HHMMSS into hours, minutes, seconds: 110135 -> 11, 01, 35.
    hh, mm, ss = hhmmss // 10000, hhmmss // 100 % 100, hhmmss % 100
    lat, lon = degrees(b.lat, b.ns), degrees(b.lon, b.ew)
    ok = (hh < 24) & (mm < 60) & (ss < 60) & (abs(lat) <= 90) & (abs(lon) <= 180)

    # The clock restarts at UTC midnight: add a day when it jumps from the last hour
    # of a day to the first of the next. Other backward steps are recorder errors,
    # left in place for the cleaning to find.
    sec = (hh * 3600 + mm * 60 + ss)[ok]
    new_day = (sec[:-1] >= 23 * 3600) & (sec[1:] <= 3600)
    t = sec + 86400 * np.r_[0, np.cumsum(new_day)]

    b = b[ok]
    return pd.DataFrame({
        "t": t - t[0] if len(t) else t,
        "lat": lat[ok],
        "lon": lon[ok],
        "valid": (b.flag == "A").to_numpy(),
        "baro_alt": altitude(b.baro),
        "gnss_alt": altitude(b.gnss),
    })
