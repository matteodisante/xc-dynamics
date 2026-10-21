"""Fixes deleted by the take-off and landing rule in every flight, the time cut before the
take-off and after the landing, and the longest slow stretch left inside the flight
(airborne.min_kmh, airborne.min_s).

Each flight with a track goes through the whole pre-processing (preprocess). The rule
deletes the fixes before the first and after the last stretch faster than min_kmh for
min_s; a flight without such a stretch is dropped (airborne_ok False). A slow stretch
inside the flight is kept, so longest_slow_s, the longest time between two fast steps,
shows the flights that stop or land in the middle.

    uv run python scripts/preprocessing/airborne_counts.py para
    uv run python scripts/preprocessing/airborne_counts.py hang --sample 200

Data and tracks folders come from configs/download.yaml, the thresholds from
configs/preprocessing.yaml. Saves flights.csv and run.yaml in
derived/preprocessing/airborne/ (scratch/ with --sample).
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from tqdm import tqdm

from xc_dynamics.common.provenance import now, run_record
from xc_dynamics.download import ffvl
from xc_dynamics.preprocessing.flight import preprocess
from xc_dynamics.preprocessing.speed import step_speed

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"


def one_flight(local_path: str, tracks: Path, altitude: dict, **thresholds) -> dict:
    """The counters of the steps of one flight, and, in a flight kept, the longest time in
    seconds between two steps faster than min_kmh."""
    try:
        fixes, row = preprocess(tracks / local_path, altitude, **thresholds)
    except Exception as err:  # one broken file must not stop a run over the whole archive
        return {"error": f"{type(err).__name__}: {err}"}
    if row.get("airborne_ok"):
        t = fixes["t"].to_numpy()
        fast = np.flatnonzero(step_speed(fixes) > thresholds["min_kmh"])
        # Between step k and the next fast step j, the slow time goes from fix k+1 to fix j.
        row["longest_slow_s"] = float((t[fast[1:]] - t[fast[:-1] + 1]).max(initial=0.0))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Fixes deleted by the take-off and landing rule in every flight.")
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
    config = yaml.safe_load((CONFIGS / "preprocessing.yaml").read_text(encoding="utf-8"))
    altitude = config["altitude"]
    thresholds = {
        "median_max_kmh": config["speed"]["median_max_kmh"][args.discipline],
        "max_kmh": config["speed"]["max_kmh"][args.discipline],
        "window_s": config["excursion"]["window_s"],
        "max_ms": config["vertical"]["max_ms"][args.discipline],
        "min_kmh": config["airborne"]["min_kmh"],
        "min_s": config["airborne"]["min_s"],
    }
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
    work = partial(one_flight, tracks=tracks, altitude=altitude, **thresholds)
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(tqdm(pool.map(work, flights.local_path, chunksize=64), total=len(flights)))
    result = pd.DataFrame(rows)
    result.insert(0, "flight_id", flights.flight_id.to_numpy())
    # Counts stay whole numbers: Int64 allows the empty cells of flights stopped early.
    counts = [
        "fixes_read", "altitude_deleted", "clock_deleted", "repeated_deleted",
        "horizontal_deleted", "horizontal_splits", "vertical_deleted", "vertical_splits",
        "airborne_deleted",
    ]
    result[counts] = result[counts].astype("Int64")

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "preprocessing" / "airborne"
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "flights.csv", index=False)

    errors = int(result["error"].notna().sum()) if "error" in result else 0
    judged = int(result.airborne_ok.notna().sum())  # flights that reached the rule
    dropped = int(result.airborne_ok.eq(False).sum())
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {"altitude": altitude, **thresholds},
        "flights": len(result),
        "unreadable": errors,
        "judged": judged,
        "dropped": dropped,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(result)} flights: {errors} unreadable, {judged} through the rule, {dropped} dropped")
    print(f"saved {out / 'flights.csv'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
