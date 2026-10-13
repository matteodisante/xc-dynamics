"""Speed of the steps and over windows of W seconds in every flight, to choose the top speed
of the excursion rule (speed.max_kmh).

Each flight with a track goes through the pre-processing up to the excursion rule
(before_excursions), so the steps counted are those the rule judges. In the flights kept,
the speed of every step and the speed over every window of excursion.window_s seconds are
counted in two histograms, one pair per wing class.

    uv run python scripts/preprocessing/speed_histograms.py para
    uv run python scripts/preprocessing/speed_histograms.py hang --sample 200

Data and tracks folders come from configs/download.yaml, the thresholds from
configs/preprocessing.yaml. Saves counts.npz and run.yaml in
derived/preprocessing/speed_histograms/ (scratch/ with --sample).
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
from xc_dynamics.preprocessing.flight import before_excursions
from xc_dynamics.preprocessing.speed import step_speed, window_speed

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"

# Bins of the histograms: every 1 km/h up to 400 km/h, then one bin for everything faster.
SPEED_EDGES = np.r_[np.arange(0, 401, 1), np.inf]
CHUNK = 200  # flights per task: each task returns one pair of histograms


def counts(
    paths: list[str], tracks: Path, altitude: dict, median_max_kmh: float, window_s: float
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Histograms of the step speeds and of the window speeds of these flights, the number
    of flights counted, and the number that could not be read."""
    steps = np.zeros(len(SPEED_EDGES) - 1, dtype=np.int64)
    windows = np.zeros(len(SPEED_EDGES) - 1, dtype=np.int64)
    counted = unreadable = 0
    for path in paths:
        try:
            fixes, row = before_excursions(tracks / path, altitude, median_max_kmh)
        except Exception:  # one broken file must not stop a run over the whole archive
            unreadable += 1
            continue
        if not (row["gnss_ok"] and row["speed_ok"]):  # a flight dropped by the pre-processing
            continue
        steps += np.histogram(step_speed(fixes), SPEED_EDGES)[0]
        windows += np.histogram(window_speed(fixes, window_s), SPEED_EDGES)[0]
        counted += 1
    return steps, windows, counted, unreadable


def main() -> None:
    parser = argparse.ArgumentParser(description="Speed of the steps and over windows in every flight.")
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

    # Tasks of at most CHUNK flights, all of one wing class, so that each pair of
    # histograms returned belongs to a single class.
    tasks = []
    for wing_class, group in flights.groupby("wing_class"):
        paths = list(group.local_path)
        for start in range(0, len(paths), CHUNK):
            tasks.append((wing_class, paths[start:start + CHUNK]))

    classes = sorted(flights.wing_class.unique())
    steps = {c: np.zeros(len(SPEED_EDGES) - 1, dtype=np.int64) for c in classes}
    windows = {c: np.zeros(len(SPEED_EDGES) - 1, dtype=np.int64) for c in classes}
    counted = unreadable = 0
    work = partial(counts, tracks=tracks, altitude=altitude, median_max_kmh=median_max_kmh, window_s=window_s)
    with ProcessPoolExecutor(args.workers) as pool, tqdm(total=len(flights), unit="flights") as bar:
        # map returns the results in the order of the tasks.
        results = pool.map(work, [paths for _, paths in tasks])
        for (wing_class, paths), (s, w, n_counted, n_unreadable) in zip(tasks, results):
            steps[wing_class] += s
            windows[wing_class] += w
            counted += n_counted
            unreadable += n_unreadable
            bar.update(len(paths))

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "preprocessing" / "speed_histograms"
    out.mkdir(parents=True, exist_ok=True)
    np.savez(
        out / "counts.npz",
        speed_edges_kmh=SPEED_EDGES,
        wing_classes=np.array(classes),
        steps=np.stack([steps[c] for c in classes]),  # wing class, speed bin
        windows=np.stack([windows[c] for c in classes]),  # wing class, speed bin
    )
    n_steps = int(sum(h.sum() for h in steps.values()))
    n_windows = int(sum(h.sum() for h in windows.values()))
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {
            "altitude": altitude,
            "speed": {"median_max_kmh": median_max_kmh},
            "excursion": {"window_s": window_s},
        },
        "flights": len(flights),
        "unreadable": unreadable,
        "counted": counted,
        "steps": n_steps,
        "windows": n_windows,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(flights)} flights: {unreadable} unreadable, {counted} counted, "
          f"{n_steps} steps, {n_windows} windows")
    print(f"saved {out / 'counts.npz'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
