"""Figures of the pre-processing chapter, drawn from the results saved in the data folder
of both disciplines, in thesis/generated/figures/preprocessing/. Each figure marks its
threshold from configs/preprocessing.yaml.

From derived/preprocessing/speed/flights.csv (scripts/preprocessing/flight_speeds.py) and
the catalog, the median step speed of every flight, for speed.median_max_kmh:

    median-speed.pdf               one panel per discipline
    median-speed-para-classes.pdf  one panel per paraglider wing class
    median-speed-hang-classes.pdf  one panel per hang-glider wing class

From derived/preprocessing/speed_histograms/counts.npz
(scripts/preprocessing/speed_histograms.py), the speed of steps and windows, for
speed.max_kmh:

    top-speed.pdf                  window speed by wing class; steps against windows

A figure whose results are not on disk keeps its committed file.

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
FLIGHTS_CSV = Path("derived", "preprocessing", "speed", "flights.csv")  # in the data folder

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

# Top speed figure.
HISTOGRAMS_NPZ = Path("derived", "preprocessing", "speed_histograms", "counts.npz")  # in the data folder
TOP_SPEED_GROUPS = {  # the groups drawn in the upper panels, fastest first
    "para": ["CCC", "D", "C", "B"],
    "hang": ["Rigid class 2", "Rigid class 5", "Class 1", "Sport"],
}
GROUP_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # one per group, in that order
STEP_COLOR, WINDOW_COLOR = "#eb6834", "#2a78d6"
REBIN = 5  # km/h per plotted bin; the saved bins are 1 km/h wide
SPEED_RANGE = (40, 300)  # km/h shown


def read_flights(root: Path, discipline: str) -> pd.DataFrame:
    """Median step speed and wing group of every flight past the altitude channel."""
    # One row per flight, written by scripts/preprocessing/flight_speeds.py; flight_id as
    # text, as in the catalog.
    flights = pd.read_csv(root / FLIGHTS_CSV, dtype={"flight_id": str})
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
    write(fig, name)


def write(fig: plt.Figure, name: str) -> None:
    # No creation date in the PDF, so the same results give the same file.
    fig.savefig(OUT / name, metadata={"CreationDate": None})
    print(f"Wrote {OUT / name}")


def share_per_kmh(counts: np.ndarray) -> np.ndarray:
    """Share of all the values per km/h, in bins of REBIN km/h from 0 to 400 km/h.

    counts holds one value per km/h and, last, the values of 400 km/h and above, which
    count in the total but are not drawn. An empty bin is NaN, so the log scale leaves a gap.
    """
    drawn = counts[:-1].reshape(-1, REBIN).sum(1)  # 400 bins of 1 km/h -> 400 / REBIN bins
    return np.where(drawn > 0, drawn / counts.sum() / REBIN, np.nan)


def top_speed_figure(roots: dict, max_kmh: dict, window_s: float) -> None:
    """Speed over windows of window_s seconds by wing group (upper row), and the speed of
    the steps against that of the windows (lower row), one column per discipline."""
    edges = np.arange(0, 401, REBIN)
    with plt.rc_context({"font.size": 8}):
        fig, axes = plt.subplots(2, 2, figsize=(6.3, 5.4), sharex=True, sharey="row", layout="constrained")
        for col, (d, root) in enumerate(roots.items()):
            z = np.load(root / HISTOGRAMS_NPZ)
            # The group of each wing class in the file, in the same order as its rows.
            groups = np.array([GROUPS[d].get(c, "other") for c in z["wing_classes"]])

            ax = axes[0, col]
            for group, color in zip(TOP_SPEED_GROUPS[d], GROUP_COLORS):
                windows = z["windows"][groups == group].sum(0)  # all the classes of the group
                ax.stairs(share_per_kmh(windows), edges, color=color, linewidth=1.2, label=group)
            ax.set_title(LABEL[d])
            ax.legend(frameon=False, title="wing class")

            ax = axes[1, col]
            ax.stairs(share_per_kmh(z["steps"].sum(0)), edges, color=STEP_COLOR, linewidth=1.2,
                      label="steps")
            ax.stairs(share_per_kmh(z["windows"].sum(0)), edges, color=WINDOW_COLOR, linewidth=1.2,
                      label=f"{window_s:g} s windows")
            ax.legend(frameon=False, title="all wing classes")
            ax.set_xlabel("ground speed (km/h)")

            for ax in axes[:, col]:
                ax.axvline(max_kmh[d], color=INK, linestyle="--", linewidth=0.8)
                ax.set_yscale("log")
                ax.set_xlim(*SPEED_RANGE)
            # x in km/h, y as a fraction of the panel height.
            axes[1, col].text(max_kmh[d] + 4, 0.04, f"{max_kmh[d]:g} km/h", color=INK,
                              transform=axes[1, col].get_xaxis_transform())
        axes[0, 0].set_ylabel(f"{window_s:g} s windows per km/h (share)")
        axes[1, 0].set_ylabel("values per km/h (share)")
        write(fig, "top-speed.pdf")


def median_speed_figures(roots: dict, median_max_kmh: dict) -> None:
    """Median step speed of every flight: by discipline, then by wing group."""
    thresholds = median_max_kmh
    flights = {d: read_flights(root, d) for d, root in roots.items()}

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


def main() -> None:
    config = yaml.safe_load((REPO / "configs" / "download.yaml").read_text(encoding="utf-8"))
    thresholds = yaml.safe_load((REPO / "configs" / "preprocessing.yaml").read_text(encoding="utf-8"))
    roots = {d: Path(config[d]["root"]) for d in LABEL}
    OUT.mkdir(parents=True, exist_ok=True)

    # Each figure is redrawn only if its results are in both data folders: without the disk,
    # or before a run, the committed file stays.
    if all((root / FLIGHTS_CSV).exists() for root in roots.values()):
        median_speed_figures(roots, thresholds["speed"]["median_max_kmh"])
    else:
        print(f"{FLIGHTS_CSV} missing: keeping the committed median-speed figures.")
    if all((root / HISTOGRAMS_NPZ).exists() for root in roots.values()):
        top_speed_figure(roots, thresholds["speed"]["max_kmh"], thresholds["excursion"]["window_s"])
    else:
        print(f"{HISTOGRAMS_NPZ} missing: keeping the committed top-speed figure.")


if __name__ == "__main__":
    main()
