"""Fixes deleted and splits of the excursion rule in every flight, with W, half W and twice
W, to see how much the splits depend on W (excursion.window_s, excursion.window_short_s,
excursion.window_long_s).

Each flight with a track goes through the pre-processing up to the excursion rule
(before_excursions), whose row also holds the sampling interval of the track as read. A
flight kept by the altitude channel and the speed rule then goes through the excursion
rule three times, once with each window, on the same fixes.

    uv run python scripts/preprocessing/excursion_counts.py para
    uv run python scripts/preprocessing/excursion_counts.py hang --sample 200

Data and tracks folders come from configs/download.yaml, the thresholds from
configs/preprocessing.yaml. Saves flights.csv and run.yaml in
derived/preprocessing/excursion/ (scratch/ with --sample).
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
from xc_dynamics.preprocessing.excursion import excursions
from xc_dynamics.preprocessing.flight import before_excursions

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"


def one_flight(
    local_path: str,
    tracks: Path,
    altitude: dict,
    median_max_kmh: float,
    max_kmh: float,
    window_s: float,
    window_short_s: float,
    window_long_s: float,
) -> dict:
    """The counters of the steps of one flight, and the fixes deleted and the splits of the
    excursion rule with each window."""
    try:
        fixes, row = before_excursions(tracks / local_path, altitude, median_max_kmh)
    except Exception as err:  # one broken file must not stop a run over the whole archive
        return {"error": f"{type(err).__name__}: {err}"}
    if not (row["gnss_ok"] and row["speed_ok"]):  # a flight dropped by the pre-processing
        return row
    row["excursion_fixes"] = len(fixes)  # the fixes the excursion rule receives
    keep, split_before = excursions(fixes, max_kmh, window_s)
    row["excursion_deleted"] = int((~keep).sum())
    row["excursion_splits"] = int(split_before.sum())
    # The same rule with half W and with twice W, only to compare.
    keep, split_before = excursions(fixes, max_kmh, window_short_s)
    row["short_deleted"] = int((~keep).sum())
    row["short_splits"] = int(split_before.sum())
    keep, split_before = excursions(fixes, max_kmh, window_long_s)
    row["long_deleted"] = int((~keep).sum())
    row["long_splits"] = int(split_before.sum())
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Fixes deleted and splits of the excursion rule in every flight.")
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
    window_short_s = thresholds["excursion"]["window_short_s"]
    window_long_s = thresholds["excursion"]["window_long_s"]
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
        window_short_s=window_short_s,
        window_long_s=window_long_s,
    )
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(tqdm(pool.map(work, flights.local_path, chunksize=64), total=len(flights)))
    result = pd.DataFrame(rows)
    result.insert(0, "flight_id", flights.flight_id.to_numpy())
    # Counts stay whole numbers: Int64 allows the empty cells of flights stopped early.
    counts = [
        "fixes_read", "altitude_deleted", "clock_deleted", "repeated_deleted", "excursion_fixes",
        "excursion_deleted", "excursion_splits",
        "short_deleted", "short_splits", "long_deleted", "long_splits",
    ]
    result[counts] = result[counts].astype("Int64")

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "preprocessing" / "excursion"
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "flights.csv", index=False)

    errors = int(result["error"].notna().sum()) if "error" in result else 0
    judged = int(result.excursion_fixes.notna().sum())
    # Flights split at least once, with each window.
    split = int(result.excursion_splits.gt(0).sum())
    split_short = int(result.short_splits.gt(0).sum())
    split_long = int(result.long_splits.gt(0).sum())
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {
            "altitude": altitude,
            "speed": {"max_kmh": max_kmh, "median_max_kmh": median_max_kmh},
            "excursion": {
                "window_s": window_s,
                "window_short_s": window_short_s,
                "window_long_s": window_long_s,
            },
        },
        "flights": len(result),
        "unreadable": errors,
        "judged": judged,
        "split": split,
        "split_short": split_short,
        "split_long": split_long,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(result)} flights: {errors} unreadable, {judged} through the excursion rule")
    print(f"split at least once: {split} with {window_s:g} s, "
          f"{split_short} with {window_short_s:g} s, {split_long} with {window_long_s:g} s")
    print(f"saved {out / 'flights.csv'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
