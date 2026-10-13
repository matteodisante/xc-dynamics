"""Speed and straightness of the steps of every flight, to choose the top speed of the
excursion rule (speed.max_kmh).

Each flight with a track goes through the steps written so far (reading, altitude channel,
clock, repeated positions, fast tracks). In the flights kept, every step that lasts at most
straightness.dt_max_s is counted in a 2D histogram of its speed and straightness, one
histogram per wing class.

    uv run python scripts/preprocessing/step_straightness.py para
    uv run python scripts/preprocessing/step_straightness.py hang --sample 200

Data and tracks folders come from configs/download.yaml, the thresholds from
configs/preprocessing.yaml. Saves counts.npz and run.yaml in
derived/preprocessing/straightness/ (scratch/ with --sample).
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
from xc_dynamics.preprocessing.speed import step_speed, step_straightness

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"

# Bins of the histogram: speed every 2 km/h up to 400 km/h, then one bin for every faster
# step; straightness every 0.02 from 0 to 1.
SPEED_EDGES = np.r_[np.arange(0, 402, 2), np.inf]
STRAIGHTNESS_EDGES = np.linspace(0, 1, 51)
CHUNK = 200  # flights per task: each task returns a single histogram


def counts(
    paths: list[str], tracks: Path, altitude: dict, median_max_kmh: float, dt_max_s: float
) -> tuple[np.ndarray, int, int]:
    """Histogram of speed (rows) and straightness (columns) of the steps of these flights,
    the number of flights counted, and the number that could not be read."""
    total = np.zeros((len(SPEED_EDGES) - 1, len(STRAIGHTNESS_EDGES) - 1), dtype=np.int64)
    counted = unreadable = 0
    for path in paths:
        try:
            fixes, row = preprocess(tracks / path, altitude, median_max_kmh)
        except Exception:  # one broken file must not stop a run over the whole archive
            unreadable += 1
            continue
        if not (row["gnss_ok"] and row["speed_ok"]):  # a flight dropped by the pre-processing
            continue
        speed = step_speed(fixes)
        straightness = step_straightness(fixes)
        dt = np.diff(fixes["t"].to_numpy())
        # Short steps only, and not the first and last step, whose straightness is NaN.
        keep = (dt <= dt_max_s) & ~np.isnan(straightness)
        # Rounding can give 1 + 1e-16 on a straight line, which would fall outside the last bin.
        straightness = np.minimum(straightness[keep], 1)
        hist, _, _ = np.histogram2d(speed[keep], straightness, [SPEED_EDGES, STRAIGHTNESS_EDGES])
        total += hist.astype(np.int64)
        counted += 1
    return total, counted, unreadable


def main() -> None:
    parser = argparse.ArgumentParser(description="Speed and straightness of the steps of every flight.")
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
    dt_max_s = thresholds["straightness"]["dt_max_s"]
    root = args.root or Path(settings["root"])
    tracks = args.tracks or Path(settings["tracks"])
    if not root.is_dir() or not tracks.is_dir():
        sys.exit(f"{root} or {tracks} not found: is the disk mounted?")

    # keep_default_na=False: an empty local_path or wing_class stays "" instead of becoming NaN.
    catalog = pd.read_csv(ffvl.catalog_path(root), dtype=str, keep_default_na=False)
    flights = catalog[catalog.local_path != ""]
    if args.sample:
        flights = flights.sample(args.sample, random_state=0)

    # Tasks of at most CHUNK flights, all of one wing class, so that each histogram
    # returned belongs to a single class.
    tasks = []
    for wing_class, group in flights.groupby("wing_class"):
        paths = list(group.local_path)
        for start in range(0, len(paths), CHUNK):
            tasks.append((wing_class, paths[start:start + CHUNK]))

    classes = sorted(flights.wing_class.unique())
    total = {c: np.zeros((len(SPEED_EDGES) - 1, len(STRAIGHTNESS_EDGES) - 1), dtype=np.int64) for c in classes}
    counted = unreadable = 0
    work = partial(counts, tracks=tracks, altitude=altitude, median_max_kmh=median_max_kmh, dt_max_s=dt_max_s)
    with ProcessPoolExecutor(args.workers) as pool, tqdm(total=len(flights), unit="flights") as bar:
        # map returns the results in the order of the tasks.
        results = pool.map(work, [paths for _, paths in tasks])
        for (wing_class, paths), (hist, n_counted, n_unreadable) in zip(tasks, results):
            total[wing_class] += hist
            counted += n_counted
            unreadable += n_unreadable
            bar.update(len(paths))

    # A full run is a result; a sample is only a trial, so it never lands in derived/.
    out = root / ("scratch" if args.sample else "derived") / "preprocessing" / "straightness"
    out.mkdir(parents=True, exist_ok=True)
    np.savez(
        out / "counts.npz",
        speed_edges_kmh=SPEED_EDGES,
        straightness_edges=STRAIGHTNESS_EDGES,
        wing_classes=np.array(classes),
        counts=np.stack([total[c] for c in classes]),  # wing class, speed bin, straightness bin
    )
    steps = int(sum(h.sum() for h in total.values()))
    record |= {
        "discipline": args.discipline,
        "root": str(root),
        "tracks": str(tracks),
        "sample": args.sample,
        "thresholds": {
            "altitude": altitude,
            "speed": {"median_max_kmh": median_max_kmh},
            "straightness": {"dt_max_s": dt_max_s},
        },
        "flights": len(flights),
        "unreadable": unreadable,
        "counted": counted,
        "steps": steps,
        "finished": now(),
    }
    (out / "run.yaml").write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    print(f"{len(flights)} flights: {unreadable} unreadable, {counted} counted, {steps} steps")
    print(f"saved {out / 'counts.npz'} and {out / 'run.yaml'}")


if __name__ == "__main__":  # needed on Windows, where every process restarts this file
    main()
