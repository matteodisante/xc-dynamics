"""Speed statistics of every flight, to calibrate the speed thresholds of the pre-processing.

Each flight with a track goes through the first steps (reading, altitude channel, clock,
repeated positions); then the median and 90th percentile of its step speed are computed.

    uv run python scripts/preprocessing/flight_speeds.py para
    uv run python scripts/preprocessing/flight_speeds.py hang --sample 200
    uv run python scripts/preprocessing/flight_speeds.py para --root E:/paragliders/ffvl_cfd_igc --tracks E:/xc-viewer-data/paragliders

Data and tracks folders come from configs/download.yaml, the thresholds of the steps
from configs/preprocessing.yaml.
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import pandas as pd
import yaml
from tqdm import tqdm

from xc_dynamics.download import ffvl
from xc_dynamics.preprocessing.flight import preprocess
from xc_dynamics.preprocessing.speed import speed_summary
from xc_dynamics.common.provenance import now, run_record

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"


def one_flight(local_path: str, tracks: Path, altitude: dict) -> dict:
    """The counters of the first steps and the speed summary of one flight."""
    try:
        fixes, row = preprocess(tracks / local_path, altitude)
    except Exception as err:  # one broken file must not stop a run over the whole archive
        return {"error": f"{type(err).__name__}: {err}"}
    if row["gnss_ok"]:  # a flight dropped by the altitude channel gets no speeds
        row |= speed_summary(fixes)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Speed statistics of every flight.")
    parser.add_argument("discipline", choices=["para", "hang"])
    parser.add_argument("--root", type=Path, help="data folder (default: from the config)")
    parser.add_argument("--tracks", type=Path, help="tracks folder (default: from the config)")
    parser.add_argument("--sample", type=int, help="only N flights drawn at random, for a quick run")
    # Windows allows at most 61 processes in a pool.
    parser.add_argument("--workers", type=int, default=min(os.cpu_count(), 61), help="parallel processes")
    args = parser.parse_args()
    record = run_record(REPO)

    # encoding="utf-8" everywhere: Windows would otherwise read and write text as cp1252.
    settings = yaml.safe_load((CONFIGS / "download.yaml").read_text(encoding="utf-8"))[args.discipline]
    altitude = yaml.safe_load((CONFIGS / "preprocessing.yaml").read_text(encoding="utf-8"))["altitude"]
    root = args.root or Path(settings["root"])
    tracks = args.tracks or Path(settings["tracks"])
    if not root.is_dir() or not tracks.is_dir():
        sys.exit(f"{root} or {tracks} not found: is the disk mounted?")

    # keep_default_na=False: an empty local_path stays "" instead of becoming NaN.
    catalog = pd.read_csv(ffvl.catalog_path(root), dtype=str, keep_default_na=False)
    flights = catalog[catalog.local_path != ""]
    if args.sample:
        flights = flights.sample(args.sample, random_state=0)

    # One process per core; each takes the flights in chunks, and map returns the rows
    # in the order of the catalog.
    work = partial(one_flight, tracks=tracks, altitude=altitude)
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(tqdm(pool.map(work, flights.local_path, chunksize=64), total=len(flights)))
    result = pd.DataFrame(rows)
    result.insert(0, "flight_id", flights.flight_id.to_numpy())
    # Counts stay whole numbers: Int64 allows the empty cells of flights stopped early.
    counts = ["fixes_read", "clock_deleted", "repeated_deleted", "steps"]
    result[counts] = result[counts].astype("Int64")

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "speed"
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "flights.csv", index=False)

    errors = int(result["error"].notna().sum()) if "error" in result else 0
    kept = int(result.gnss_ok.eq(True).sum())
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {"altitude": altitude},
        "flights": len(result),
        "unreadable": errors,
        "past_altitude_channel": kept,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(result)} flights: {errors} unreadable, {kept} past the altitude channel")
    print(f"saved {out / 'flights.csv'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
