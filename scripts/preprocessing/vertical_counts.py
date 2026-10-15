"""Fixes deleted and splits of the vertical excursion rule in every flight, on the GNSS
altitude and, as a check, on the pressure altitude of the flights whose barometer is a
witness (vertical.max_ms).

Each flight with a track goes through the pre-processing up to the vertical excursion rule
(before_vertical). A flight kept by the previous steps then goes through the rule on its
GNSS altitude. The barometer measures altitude independently of the GNSS, so in a witness
flight the same rule also runs on the pressure altitude: what it deletes or splits there
is real vertical motion, or an error the two channels share.

    uv run python scripts/preprocessing/vertical_counts.py para
    uv run python scripts/preprocessing/vertical_counts.py hang --sample 200

Data and tracks folders come from configs/download.yaml, the thresholds from
configs/preprocessing.yaml. Saves flights.csv and run.yaml in
derived/preprocessing/vertical/ (scratch/ with --sample).
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

from xc_dynamics.common.provenance import now, run_record
from xc_dynamics.download import ffvl
from xc_dynamics.preprocessing.excursion import vertical_excursions
from xc_dynamics.preprocessing.flight import before_vertical

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"


def one_flight(
    local_path: str,
    tracks: Path,
    altitude: dict,
    median_max_kmh: float,
    max_kmh: float,
    window_s: float,
    max_ms: float,
) -> dict:
    """The counters of the steps of one flight, and the fixes deleted and the splits of the
    vertical excursion rule on the GNSS altitude and, in a witness flight, on the pressure
    altitude."""
    try:
        fixes, row = before_vertical(tracks / local_path, altitude, median_max_kmh, max_kmh, window_s)
    except Exception as err:  # one broken file must not stop a run over the whole archive
        return {"error": f"{type(err).__name__}: {err}"}
    if not (row["gnss_ok"] and row["speed_ok"]):  # a flight dropped by the pre-processing
        return row
    row["vertical_fixes"] = len(fixes)  # the fixes the vertical rule receives
    keep, split_before = vertical_excursions(fixes, max_ms, window_s)
    row["vertical_deleted"] = int((~keep).sum())
    row["vertical_splits"] = int(split_before.sum())
    if row["baro_witness"]:
        # The same rule on the pressure altitude, only to check it. The barometer can miss
        # a value on a few fixes, and the rule needs one on every fix.
        baro = fixes.dropna(subset=["baro_alt"])
        keep, split_before = vertical_excursions(baro, max_ms, window_s, column="baro_alt")
        row["baro_fixes"] = len(baro)
        row["baro_deleted"] = int((~keep).sum())
        row["baro_splits"] = int(split_before.sum())
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Fixes deleted and splits of the vertical excursion rule in every flight.")
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
    thresholds = yaml.safe_load((CONFIGS / "preprocessing.yaml").read_text(encoding="utf-8"))
    altitude = thresholds["altitude"]
    median_max_kmh = thresholds["speed"]["median_max_kmh"][args.discipline]
    max_kmh = thresholds["speed"]["max_kmh"][args.discipline]
    window_s = thresholds["excursion"]["window_s"]
    max_ms = thresholds["vertical"]["max_ms"][args.discipline]
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
    work = partial(
        one_flight,
        tracks=tracks,
        altitude=altitude,
        median_max_kmh=median_max_kmh,
        max_kmh=max_kmh,
        window_s=window_s,
        max_ms=max_ms,
    )
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(tqdm(pool.map(work, flights.local_path, chunksize=64), total=len(flights)))
    result = pd.DataFrame(rows)
    result.insert(0, "flight_id", flights.flight_id.to_numpy())
    # Counts stay whole numbers: Int64 allows the empty cells of flights stopped early.
    counts = [
        "fixes_read", "altitude_deleted", "clock_deleted", "repeated_deleted",
        "horizontal_deleted", "horizontal_splits",
        "vertical_fixes", "vertical_deleted", "vertical_splits",
        "baro_fixes", "baro_deleted", "baro_splits",
    ]
    result[counts] = result[counts].astype("Int64")

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "preprocessing" / "vertical"
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "flights.csv", index=False)

    errors = int(result["error"].notna().sum()) if "error" in result else 0
    judged = int(result.vertical_fixes.notna().sum())
    witnesses = int(result.baro_fixes.notna().sum())
    split = int(result.vertical_splits.gt(0).sum())  # flights split at least once
    baro_split = int(result.baro_splits.gt(0).sum())
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {
            "altitude": altitude,
            "speed": {"max_kmh": max_kmh, "median_max_kmh": median_max_kmh},
            "excursion": {"window_s": window_s},
            "vertical": {"max_ms": max_ms},
        },
        "flights": len(result),
        "unreadable": errors,
        "judged": judged,
        "split": split,
        "witnesses": witnesses,
        "baro_split": baro_split,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(result)} flights: {errors} unreadable, {judged} through the vertical rule")
    print(f"split at least once: {split} on the GNSS altitude, "
          f"{baro_split} of {witnesses} witnesses on the pressure altitude")
    print(f"saved {out / 'flights.csv'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
