"""Vertical speed of the steps and over windows of W seconds in every flight, from the GNSS
and from the pressure altitude, to choose the top vertical speed of the vertical excursion
rule.

Each flight with a track goes through the pre-processing up to the vertical excursion rule
(before_vertical), so the steps counted are those the rule will judge. Only the flights
whose barometer is a witness (baro_witness) are counted. The barometer has no GNSS errors,
so its speeds are real vertical motion, and its speed over windows of excursion.window_s
seconds shows where real motion ends. The absolute speeds of the steps and of the windows,
from each channel, go into four histograms per wing class.

    uv run python scripts/preprocessing/vertical_histograms.py para
    uv run python scripts/preprocessing/vertical_histograms.py hang --sample 200

Data and tracks folders come from configs/download.yaml, the thresholds from
configs/preprocessing.yaml. Saves counts.npz and run.yaml in
derived/preprocessing/vertical_histograms/ (scratch/ with --sample).
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
from xc_dynamics.preprocessing.altitude import vertical_speeds, vertical_window_speeds
from xc_dynamics.preprocessing.flight import before_vertical

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"

# Bins of the absolute vertical speed in m/s, centred on every whole m/s up to 100 m/s,
# then one bin for everything faster. IGC altitudes are whole metres, so on steps of 1 s
# the speed is a whole number and falls in the middle of its bin. The first bin, 0 to 0.5,
# is half as wide as the others.
VERTICAL_EDGES = np.r_[0, np.arange(0.5, 101, 1), np.inf]
CHUNK = 200  # flights per task: each task returns one set of histograms
HISTOGRAMS = ["gnss_steps", "baro_steps", "gnss_windows", "baro_windows"]


def counts(
    paths: list[str],
    tracks: Path,
    altitude: dict,
    median_max_kmh: float,
    max_kmh: float,
    window_s: float,
) -> tuple[dict, int, int, int]:
    """The four histograms of the absolute vertical speed in these flights, the number of
    flights counted, of those left out because their barometer is not a witness, and of
    those that could not be read."""
    hist = {name: np.zeros(len(VERTICAL_EDGES) - 1, dtype=np.int64) for name in HISTOGRAMS}
    counted = no_witness = unreadable = 0
    for path in paths:
        try:
            fixes, row = before_vertical(tracks / path, altitude, median_max_kmh, max_kmh, window_s)
        except Exception:  # one broken file must not stop a run over the whole archive
            unreadable += 1
            continue
        if not (row["gnss_ok"] and row["speed_ok"]):  # a flight dropped by the pre-processing
            continue
        if not row["baro_witness"]:  # kept by the pre-processing, but of no use here
            no_witness += 1
            continue
        speeds = (*vertical_speeds(fixes), *vertical_window_speeds(fixes, window_s))
        for name, w in zip(HISTOGRAMS, speeds):
            hist[name] += np.histogram(np.abs(w), VERTICAL_EDGES)[0]
        counted += 1
    return hist, counted, no_witness, unreadable


def main() -> None:
    parser = argparse.ArgumentParser(description="Vertical speed of the steps and over windows in every flight.")
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
    root = args.root or Path(settings["root"])
    tracks = args.tracks or Path(settings["tracks"])
    if not root.is_dir() or not tracks.is_dir():
        sys.exit(f"{root} or {tracks} not found: is the disk mounted?")

    # keep_default_na=False: an empty local_path or wing_class stays "" instead of becoming NaN.
    catalog = pd.read_csv(ffvl.catalog_path(root), dtype=str, keep_default_na=False)
    flights = catalog[catalog.local_path != ""]
    if args.sample:
        flights = flights.sample(args.sample, random_state=0)

    # Tasks of at most CHUNK flights, all of one wing class, so that each set of
    # histograms returned belongs to a single class.
    tasks = []
    for wing_class, group in flights.groupby("wing_class"):
        paths = list(group.local_path)
        for start in range(0, len(paths), CHUNK):
            tasks.append((wing_class, paths[start:start + CHUNK]))

    classes = sorted(flights.wing_class.unique())
    # hist[name][wing class]: one histogram per kind of speed and wing class.
    hist = {name: {c: np.zeros(len(VERTICAL_EDGES) - 1, dtype=np.int64) for c in classes} for name in HISTOGRAMS}
    counted = no_witness = unreadable = 0
    work = partial(
        counts,
        tracks=tracks,
        altitude=altitude,
        median_max_kmh=median_max_kmh,
        max_kmh=max_kmh,
        window_s=window_s,
    )
    with ProcessPoolExecutor(args.workers) as pool, tqdm(total=len(flights), unit="flights") as bar:
        # map returns the results in the order of the tasks.
        results = pool.map(work, [paths for _, paths in tasks])
        for (wing_class, paths), (h, n_counted, n_no_witness, n_unreadable) in zip(tasks, results):
            for name in HISTOGRAMS:
                hist[name][wing_class] += h[name]
            counted += n_counted
            no_witness += n_no_witness
            unreadable += n_unreadable
            bar.update(len(paths))

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "preprocessing" / "vertical_histograms"
    out.mkdir(parents=True, exist_ok=True)
    np.savez(
        out / "counts.npz",
        vertical_edges_ms=VERTICAL_EDGES,
        wing_classes=np.array(classes),
        # Each one: wing class, speed bin.
        **{name: np.stack([hist[name][c] for c in classes]) for name in HISTOGRAMS},
    )
    n_steps = int(sum(h.sum() for h in hist["gnss_steps"].values()))
    n_windows = int(sum(h.sum() for h in hist["gnss_windows"].values()))
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {
            "altitude": altitude,
            "speed": {"max_kmh": max_kmh, "median_max_kmh": median_max_kmh},
            "excursion": {"window_s": window_s},
        },
        "flights": len(flights),
        "unreadable": unreadable,
        "no_witness": no_witness,
        "counted": counted,
        "steps": n_steps,
        "windows": n_windows,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(flights)} flights: {unreadable} unreadable, {no_witness} without a witness, "
          f"{counted} counted, {n_steps} steps, {n_windows} windows")
    print(f"saved {out / 'counts.npz'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
