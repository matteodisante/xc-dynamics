"""Figures and table of the pre-processing chapter, figures in
thesis/generated/figures/preprocessing/. Most come from the results saved in the data
folder of both disciplines, and a figure marks its threshold from
configs/preprocessing.yaml; the diagrams of the excursion rule come from synthetic tracks.

From derived/preprocessing/speed/flights.csv (scripts/preprocessing/flight_speeds.py) and
the catalog, the median step speed of every flight, for speed.median_max_kmh:

    median-speed.pdf               one panel per discipline
    median-speed-para-classes.pdf  one panel per paraglider wing class
    median-speed-hang-classes.pdf  one panel per hang-glider wing class

From derived/preprocessing/speed_histograms/counts.npz
(scripts/preprocessing/speed_histograms.py), the speed of steps and windows, for
speed.max_kmh:

    top-speed.pdf                  window speed by wing class; steps against windows

From derived/preprocessing/vertical_histograms/counts.npz
(scripts/preprocessing/vertical_histograms.py), the vertical speed of steps and windows
from both altitude channels, in the flights whose barometer is a witness, for
vertical.max_ms:

    vertical-speed.pdf             barometer window speed by wing class; both channels,
                                   steps and windows

From two synthetic tracks judged by the excursion rule itself, with excursion.window_s:

    excursion-rule.pdf             a block that comes back; a jump that does not
    excursion-real-flight.pdf      real flight faster than the top speed, split or not

From derived/preprocessing/excursion/flights.csv (scripts/preprocessing/excursion_counts.py),
the flights split and the fixes deleted by the excursion rule with half W, W and twice W,
in thesis/generated/tex/:

    preprocessing-excursion.tex    body of the table, one row per window

From derived/preprocessing/vertical/flights.csv (scripts/preprocessing/vertical_counts.py),
the flights split and the fixes deleted by the vertical excursion rule on the GNSS altitude
and, in the witness flights, on the pressure altitude, in thesis/generated/tex/:

    preprocessing-vertical.tex     body of the table, one row per discipline and altitude

A figure or table whose results are not on disk keeps its committed file.

    uv run python thesis/scripts/preprocessing.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from xc_dynamics.download import ffvl
from xc_dynamics.preprocessing.excursion import horizontal_excursions
from xc_dynamics.preprocessing.speed import EARTH_RADIUS_M

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

# Vertical speed figure: same wing groups and colours as the top speed figure.
VERTICAL_NPZ = Path("derived", "preprocessing", "vertical_histograms", "counts.npz")  # in the data folder
GNSS_COLOR, BARO_COLOR = "#eb6834", "#2a78d6"
VERTICAL_RANGE = (0, 80)  # m/s shown

# Excursion tables.
EXCURSION_CSV = Path("derived", "preprocessing", "excursion", "flights.csv")  # in the data folder
VERTICAL_CSV = Path("derived", "preprocessing", "vertical", "flights.csv")  # in the data folder
TEX = REPO / "thesis" / "generated" / "tex"

# Excursion rule figure: synthetic tracks along one coordinate, judged by the rule itself.
SCHEME_SPEED = 5.0  # m/s, the speed of the glider
SCHEME_MAX_SPEED = 12.0  # m/s, a top speed low enough for the cone to show
BURST_SPEED = 25.0  # m/s, real flight faster than that top speed
METRES_PER_DEGREE = EARTH_RADIUS_M * np.pi / 180  # along a meridian
DELETED_COLOR, CUT_COLOR, CONE_COLOR = "#eb6834", "#c0392b", "#dce6f5"


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


def share_per_ms(counts: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Share of all the values per m/s in each bin of the saved edges.

    The last bin, up to infinity, counts in the total but is not drawn. Bins differ in
    width (the first is half as wide), so each count is divided by its own. An empty bin is
    NaN, so the log scale leaves a gap.
    """
    drawn = counts[:-1]
    return np.where(drawn > 0, drawn / counts.sum() / np.diff(edges[:-1]), np.nan)


def vertical_speed_figure(roots: dict, max_ms: dict, window_s: float) -> None:
    """Barometer speed over windows of window_s seconds by wing group (upper row), and both
    altitude channels on steps and on windows (lower row), one column per discipline."""
    with plt.rc_context({"font.size": 8}):
        fig, axes = plt.subplots(2, 2, figsize=(6.3, 5.4), sharex=True, sharey="row", layout="constrained")
        for col, (d, root) in enumerate(roots.items()):
            z = np.load(root / VERTICAL_NPZ)
            edges = z["vertical_edges_ms"]
            # The group of each wing class in the file, in the same order as its rows.
            groups = np.array([GROUPS[d].get(c, "other") for c in z["wing_classes"]])

            ax = axes[0, col]
            for group, color in zip(TOP_SPEED_GROUPS[d], GROUP_COLORS):
                baro = z["baro_windows"][groups == group].sum(0)  # all the classes of the group
                ax.stairs(share_per_ms(baro, edges), edges[:-1], color=color, linewidth=1.2, label=group)
            ax.set_title(LABEL[d])
            ax.legend(frameon=False, title="wing class")

            ax = axes[1, col]
            curves = [  # array, colour, line style, label
                ("gnss_steps", GNSS_COLOR, ":", "GNSS, steps"),
                ("baro_steps", BARO_COLOR, ":", "barometer, steps"),
                ("gnss_windows", GNSS_COLOR, "-", f"GNSS, {window_s:g} s windows"),
                ("baro_windows", BARO_COLOR, "-", f"barometer, {window_s:g} s windows"),
            ]
            for name, color, style, label in curves:
                ax.stairs(share_per_ms(z[name].sum(0), edges), edges[:-1], color=color, linestyle=style,
                          linewidth=1.2, label=label)
            ax.legend(frameon=False, title="all wing classes")
            ax.set_xlabel("absolute vertical speed (m/s)")

            for ax in axes[:, col]:
                ax.axvline(max_ms[d], color=INK, linestyle="--", linewidth=0.8)
                ax.set_yscale("log")
                ax.set_xlim(*VERTICAL_RANGE)
            # x in m/s, y as a fraction of the panel height.
            axes[1, col].text(max_ms[d] + 1, 0.04, f"{max_ms[d]:g} m/s", color=INK,
                              transform=axes[1, col].get_xaxis_transform())
        axes[0, 0].set_ylabel(f"barometer, {window_s:g} s windows per m/s (share)")
        axes[1, 0].set_ylabel("values per m/s (share)")
        write(fig, "vertical-speed.pdf")


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


def draw_rule(ax: plt.Axes, t: np.ndarray, x: np.ndarray, window_s: float) -> tuple:
    """Judge the track x(t), in metres along one coordinate, with the excursion rule; draw
    the fixes kept and deleted, the anchor and its cone. Return keep, split_before and the
    index of the anchor."""
    # The positions as fixes along a meridian, x metres north of 45 N.
    fixes = pd.DataFrame({"t": t, "lat": 45 + x / METRES_PER_DEGREE, "lon": 6.0})
    keep, split_before = horizontal_excursions(fixes, 3.6 * SCHEME_MAX_SPEED, window_s)  # m/s -> km/h
    # The block opens at the first fix deleted or split from the track; the anchor is the
    # fix before it.
    a = np.flatnonzero(~keep | split_before)[0] - 1
    # Cone: the positions reachable from the anchor, |x - x_a| <= v_max (t - t_a).
    reach = SCHEME_MAX_SPEED * (t[a:] - t[a])
    ax.fill_between(t[a:], x[a] - reach, x[a] + reach, color=CONE_COLOR, linewidth=0)
    ax.plot(t[keep], x[keep], "o", color="grey", markersize=2.5)
    ax.plot(t[~keep], x[~keep], "x", color=DELETED_COLOR, markersize=5)
    ax.plot(t[a], x[a], "o", color=BAR, markersize=5)
    ax.annotate("anchor", (t[a], x[a]), (t[a] - 9, x[a] + 110),
                arrowprops={"arrowstyle": "-", "color": INK})
    ax.set_xlabel("time (s)")
    return keep, split_before, a


def excursion_rule_figure(window_s: float) -> None:
    """The excursion rule on two synthetic tracks along one coordinate, one fix per second:
    a block that comes back (left) and a jump that does not (right)."""
    t = np.arange(12 + window_s + 15)  # long enough to show the whole window after fix 12
    with plt.rc_context({"font.size": 8}):
        fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.8), sharey=True, layout="constrained")

        # (a) Three fixes off the track, then back on it.
        x = SCHEME_SPEED * t
        x[12:15] = 220
        keep, _, a = draw_rule(axes[0], t, x, window_s)
        k = a + 1 + np.argmax(keep[a + 1:])  # the first fix kept after the anchor: the return
        axes[0].plot(t[k], x[k], "o", markerfacecolor="none", markeredgecolor=BAR, markersize=7)
        axes[0].annotate("first fix back\nin the cone", (t[k], x[k]), (t[k] + 6, x[k] - 70),
                         arrowprops={"arrowstyle": "-", "color": INK})
        axes[0].text(t[a] + 5, 220, "deleted", color=DELETED_COLOR, va="center")
        axes[0].set_title("(a) the block comes back: deleted")
        axes[0].set_ylabel("position (m)")

        # (b) From fix 12 on, the track is 420 m further and stays there.
        x = SCHEME_SPEED * t
        x[12:] += 420
        _, split_before, a = draw_rule(axes[1], t, x, window_s)
        j = np.flatnonzero(split_before)[0]  # the first fix of the new segment
        axes[1].axvspan(t[j], t[j] + window_s, color="0.92", zorder=0)
        axes[1].axvline((t[j - 1] + t[j]) / 2, color=CUT_COLOR, linewidth=1)
        axes[1].text(t[j] + 1, 650, f"W = {window_s:g} s", color=INK)
        axes[1].text(t[j] + 1, 330, "split: a new\nsegment starts here", color=CUT_COLOR)
        axes[1].set_title("(b) no return within W: split")

        axes[0].set_ylim(-30, 700)
        for ax in axes:
            ax.set_xlim(t[0] - 1, t[-1] + 1)
        write(fig, "excursion-rule.pdf")


def real_flight_figure(window_s: float) -> None:
    """Real flight faster than the top speed, on synthetic tracks along one coordinate, one
    fix per second: a short burst that the rule does not split (left), and a burst that
    lasts most of the window and is split (right)."""
    t = np.arange(12 + window_s + 15)  # long enough to show the whole window after fix 12
    titles = [r"(a) $u_a\leq v_{\max}$: no split", r"(b) $u_a>v_{\max}$: split"]
    with plt.rc_context({"font.size": 8}):
        fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.8), sharey=True, layout="constrained")
        for ax, burst, title in zip(axes, [3, 15], titles):
            # Steps at SCHEME_SPEED, except `burst` steps at BURST_SPEED from fix 11 on.
            steps = np.full(len(t) - 1, SCHEME_SPEED)
            steps[11:11 + burst] = BURST_SPEED
            x = np.r_[0, np.cumsum(steps)]
            keep, split_before, a = draw_rule(ax, t, x, window_s)

            # The block opens at the fix after the anchor; the rule waits window_s from there.
            ax.axvspan(t[a + 1], t[a + 1] + window_s, color="0.92", zorder=0)
            # The window of length window_s from the anchor ends at fix l (Equation
            # window-speed); the slope of the dashed line is the window speed u_a.
            l = np.searchsorted(t, t[a] + window_s)
            ax.plot([t[a], t[l]], [x[a], x[l]], "--", color=INK, linewidth=1)
            ax.plot(t[l], x[l], "s", color=INK, markersize=4)
            ax.text(t[l] + 1, x[l] - 10, r"$\ell$", color=INK, va="top")
            ax.set_title(title)

            if split_before.any():
                # Split between the anchor and the block.
                ax.axvline((t[a] + t[a + 1]) / 2, color=CUT_COLOR, linewidth=1)
            else:
                k = a + 1 + np.argmax(keep[a + 1:])  # the first fix kept after the anchor
                ax.plot(t[k], x[k], "o", markerfacecolor="none", markeredgecolor=BAR, markersize=7)

        axes[0].set_ylabel("position (m)")
        axes[0].set_ylim(-30, 600)
        for ax in axes:
            ax.set_xlim(t[0] - 1, t[-1] + 1)
        write(fig, "excursion-real-flight.pdf")


def excursion_table(roots: dict, excursion: dict) -> None:
    """Body of the excursion table: one row per window and, for each discipline, the share
    of flights split at least once and the share of fixes deleted."""
    # Prefix of the columns in flights.csv -> window in seconds, in the order of the rows.
    windows = {
        "short": excursion["window_short_s"],
        "horizontal": excursion["window_s"],
        "long": excursion["window_long_s"],
    }
    # Only the flights that went through the rule: the others have no horizontal_fixes.
    flights = {}
    for d, root in roots.items():
        flights[d] = pd.read_csv(root / EXCURSION_CSV).dropna(subset=["horizontal_fixes"])

    header = ""
    for d, f in flights.items():
        header += f" & \\multicolumn{{2}}{{c}}{{{LABEL[d]} (\\num{{{len(f)}}} flights)}}"
    lines = [
        "% Written by thesis/scripts/preprocessing.py: do not edit.\n",
        "\\begin{tabular}{@{}rrrrr@{}}\n",
        "\\toprule\n",
        header + " \\\\\n",
        "\\cmidrule(lr){2-3}\\cmidrule(l){4-5}\n",
        "$W$ (s) & Flights split (\\%) & Fixes deleted (\\%) & Flights split (\\%) & Fixes deleted (\\%) \\\\\n",
        "\\midrule\n",
    ]
    for prefix, window_s in windows.items():
        row = f"{window_s:g}"
        for f in flights.values():
            split = 100 * f[f"{prefix}_splits"].gt(0).mean()
            deleted = 100 * f[f"{prefix}_deleted"].sum() / f.horizontal_fixes.sum()
            row += f" & {split:.2f} & {deleted:.3f}"
        lines.append(row + " \\\\\n")
    lines += ["\\bottomrule\n", "\\end{tabular}\n"]
    TEX.mkdir(parents=True, exist_ok=True)
    (TEX / "preprocessing-excursion.tex").write_text("".join(lines))
    print(f"Wrote {TEX / 'preprocessing-excursion.tex'}")


def vertical_table(roots: dict) -> None:
    """Body of the vertical excursion table: for each discipline, the rule on the GNSS
    altitude of every flight and on the pressure altitude of the witness flights, with the
    flights judged, the share split at least once and the share of fixes deleted."""
    # Prefix of the columns in flights.csv -> altitude, in the order of the rows.
    altitudes = {"vertical": "GNSS", "baro": "pressure"}
    lines = [
        "% Written by thesis/scripts/preprocessing.py: do not edit.\n",
        "\\begin{tabular}{@{}llrrr@{}}\n",
        "\\toprule\n",
        "& Altitude & Flights & Flights split (\\%) & Fixes deleted (\\%) \\\\\n",
        "\\midrule\n",
    ]
    for d, root in roots.items():
        flights = pd.read_csv(root / VERTICAL_CSV)
        for prefix, altitude in altitudes.items():
            # Only the flights the rule ran on: the others have no fixes counted.
            f = flights.dropna(subset=[f"{prefix}_fixes"])
            split = 100 * f[f"{prefix}_splits"].gt(0).mean()
            deleted = 100 * f[f"{prefix}_deleted"].sum() / f[f"{prefix}_fixes"].sum()
            label = LABEL[d] if prefix == "vertical" else ""
            lines.append(f"{label} & {altitude} & \\num{{{len(f)}}} & {split:.2f} & {deleted:.3f} \\\\\n")
    lines += ["\\bottomrule\n", "\\end{tabular}\n"]
    TEX.mkdir(parents=True, exist_ok=True)
    (TEX / "preprocessing-vertical.tex").write_text("".join(lines))
    print(f"Wrote {TEX / 'preprocessing-vertical.tex'}")


def main() -> None:
    config = yaml.safe_load((REPO / "configs" / "download.yaml").read_text(encoding="utf-8"))
    thresholds = yaml.safe_load((REPO / "configs" / "preprocessing.yaml").read_text(encoding="utf-8"))
    roots = {d: Path(config[d]["root"]) for d in LABEL}
    OUT.mkdir(parents=True, exist_ok=True)

    # Drawn from synthetic tracks: need no data.
    excursion_rule_figure(thresholds["excursion"]["window_s"])
    real_flight_figure(thresholds["excursion"]["window_s"])

    # Each figure or table is redrawn only if its results are in both data folders: without
    # the disk, or before a run, the committed file stays.
    if all((root / FLIGHTS_CSV).exists() for root in roots.values()):
        median_speed_figures(roots, thresholds["speed"]["median_max_kmh"])
    else:
        print(f"{FLIGHTS_CSV} missing: keeping the committed median-speed figures.")
    if all((root / HISTOGRAMS_NPZ).exists() for root in roots.values()):
        top_speed_figure(roots, thresholds["speed"]["max_kmh"], thresholds["excursion"]["window_s"])
    else:
        print(f"{HISTOGRAMS_NPZ} missing: keeping the committed top-speed figure.")
    if all((root / VERTICAL_NPZ).exists() for root in roots.values()):
        vertical_speed_figure(roots, thresholds["vertical"]["max_ms"], thresholds["excursion"]["window_s"])
    else:
        print(f"{VERTICAL_NPZ} missing: keeping the committed vertical-speed figure.")
    if all((root / EXCURSION_CSV).exists() for root in roots.values()):
        excursion_table(roots, thresholds["excursion"])
    else:
        print(f"{EXCURSION_CSV} missing: keeping the committed excursion table.")
    if all((root / VERTICAL_CSV).exists() for root in roots.values()):
        vertical_table(roots)
    else:
        print(f"{VERTICAL_CSV} missing: keeping the committed vertical excursion table.")


if __name__ == "__main__":
    main()
