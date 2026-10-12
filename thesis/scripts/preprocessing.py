"""Figures of the pre-processing chapter: the median step speed of every flight, to choose
the speed thresholds.

Reads derived/speed/flights.csv, written by scripts/preprocessing/flight_speeds.py, and
the catalog of both disciplines, and writes, in thesis/generated/figures/preprocessing/:

    median-speed.pdf               one panel per discipline
    median-speed-para-classes.pdf  one panel per paraglider wing class
    median-speed-hang-classes.pdf  one panel per hang-glider wing class

Each histogram marks the threshold median_max_kmh of configs/preprocessing.yaml.
Without the disk the committed files are kept.

    uv run python thesis/scripts/preprocessing.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from xc_dynamics.download import ffvl

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "thesis" / "generated" / "figures" / "preprocessing"

LABEL = {"para": "Paragliders", "hang": "Hang gliders"}
# Wing class in the catalog -> group in the figures, in panel order; any other class is "other".
GROUPS = {
    "para": {"A ou 1": "A", "B ou 1-2": "B", "C ou 2": "C", "D ou 2-3": "D",
             "CIVL Competition Class": "CCC", "Biplace": "tandem", "Biplace non homologué": "tandem"},
    "hang": {"Delta Class 1": "Class 1", "Delta Class Sport": "Sport",
             "Rigide Class 5": "Rigid class 5", "Rigide Class 2": "Rigid class 2"},
}
MAX_KMH = 200  # right edge of the histograms; faster flights are counted apart
BINS = np.arange(0, MAX_KMH + 2, 2)  # 2 km/h wide
BAR, INK = "#2a78d6", "#52514e"  # bars; threshold line and notes


def read_flights(root: Path, discipline: str) -> pd.DataFrame:
    """Median step speed and wing group of every flight past the altitude channel."""
    # One row per flight, written by scripts/preprocessing/flight_speeds.py; flight_id as
    # text, as in the catalog.
    flights = pd.read_csv(root / "derived" / "speed" / "flights.csv", dtype={"flight_id": str})
    # The catalog, all as text; keep_default_na=False keeps empty cells as "".
    catalog = pd.read_csv(ffvl.catalog_path(root), dtype=str, keep_default_na=False)
    # Add to each flight its wing class, matching the rows by flight_id.
    flights = flights.merge(catalog[["flight_id", "wing_class"]], on="flight_id", how="left")
    # Wing class -> panel group; a class not in GROUPS becomes "other".
    flights["group"] = flights.wing_class.map(GROUPS[discipline]).fillna("other")
    # Drop the flights without a median: stopped at the altitude channel, or with no steps.
    return flights.dropna(subset=["median_kmh"])


def histogram(ax: plt.Axes, speeds: pd.Series, title: str, threshold: float) -> None:
    """Number of flights per 2 km/h of median speed, on a log scale, with the threshold."""
    ax.hist(speeds.clip(upper=MAX_KMH - 1e-9), bins=BINS, color=BAR)  # faster ones in the last bin
    ax.axvline(threshold, color=INK, linestyle="--", linewidth=1)
    ax.set_yscale("log")
    ax.set_xlim(0, MAX_KMH)
    ax.set_title(f"{title} ({len(speeds)} flights)", fontsize="medium")
    faster = (speeds >= MAX_KMH).sum()
    if faster:
        ax.text(0.98, 0.95, f"{faster} above {MAX_KMH} km/h,\nin the last bin", color=INK,
                transform=ax.transAxes, ha="right", va="top", fontsize="small")


def save(fig: plt.Figure, name: str) -> None:
    fig.supxlabel("median step speed of the flight (km/h)", fontsize="medium")
    fig.supylabel("flights", fontsize="medium")
    fig.tight_layout()
    fig.savefig(OUT / name)
    print(f"Wrote {OUT / name}")


def main() -> None:
    config = yaml.safe_load((REPO / "configs" / "download.yaml").read_text(encoding="utf-8"))
    thresholds = yaml.safe_load((REPO / "configs" / "preprocessing.yaml").read_text(encoding="utf-8"))
    thresholds = thresholds["speed"]["median_max_kmh"]
    roots = {d: Path(config[d]["root"]) for d in LABEL}
    # The data folders whose flights.csv does not exist (empty list if both do).
    missing = [r for r in roots.values() if not (r / "derived" / "speed" / "flights.csv").exists()]
    if missing:  # disk not mounted, or a run not done yet
        print(f"no speed results in {missing}: keeping the committed files.")
        return
    flights = {d: read_flights(root, d) for d, root in roots.items()}
    OUT.mkdir(parents=True, exist_ok=True)

    # All flights, one panel per discipline.
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, (d, f) in zip(axes, flights.items()):
        histogram(ax, f.median_kmh, LABEL[d], thresholds[d])
    save(fig, "median-speed.pdf")

    # One panel per wing group, same axes for all.
    for d, f in flights.items():
        groups = list(dict.fromkeys(GROUPS[d].values()))  # fromkeys drops the repeated "tandem"
        if d == "para":  # hang gliders: a single flight has no class, not worth a panel
            groups.append("other")
        rows = (len(groups) + 3) // 4
        fig, axes = plt.subplots(rows, 4, figsize=(12, 3 * rows), sharex=True, sharey=True)
        for ax, group in zip(axes.flat, groups):
            histogram(ax, f.median_kmh[f.group == group], group, thresholds[d])
        for ax in axes.flat[len(groups):]:
            ax.set_visible(False)
        save(fig, f"median-speed-{d}-classes.pdf")


if __name__ == "__main__":
    main()
