"""Numbers of chapter 2: flights per season and the counts quoted in the text.

Reads the two catalogs written by scripts/download_ffvl.py and writes, in
thesis/generated/:

    02-dataset-values.tex        macros quoted in the text, e.g. \\ParaFlights
    02-dataset-seasons-para.tex  body of the paraglider season table
    02-dataset-seasons-hang.tex  same for hang gliders

Without the disk the committed files are kept.

    uv run python thesis/scripts/02_dataset.py
"""

from pathlib import Path

import pandas as pd
import yaml

from xc_dynamics.download import ffvl

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "thesis" / "generated"
HEADER = "% Written by thesis/scripts/02_dataset.py: do not edit.\n"

# Discipline in configs/download.yaml -> macro prefix.
PREFIX = {"para": "Para", "delta": "Hang"}


def per_season(catalog: pd.DataFrame) -> pd.DataFrame:
    """Flights, flights with a track and downloaded tracks, one row per season."""
    return catalog.groupby("season").agg(
        flights=("flight_id", "size"),
        with_track=("igc_link", "count"),  # count skips the empty cells
        downloaded=("local_path", "count"),
    )


def pct(part: float, whole: float) -> float:
    return 100 * part / whole


def dashes(season: str) -> str:
    """'1999-2000' -> '1999--2000'."""
    return season.replace("-", "--")


def table(seasons: pd.DataFrame) -> str:
    """LaTeX tabular as text: a row per season, then the total, with the % downloaded."""
    rows = seasons.copy()
    rows.loc["Total"] = rows.sum()
    lines = [
        HEADER,
        "\\begin{tabular}{@{}lrrrr@{}}\n",
        "\\toprule\n",
        "Season & Flights & With track & Downloaded & Downloaded (\\% of tracks) \\\\\n",
        "\\midrule\n",
    ]
    for season, r in rows.iterrows():
        if season == "Total":
            lines.append("\\midrule\n")
        share = f"{pct(r.downloaded, r.with_track):.1f}" if r.with_track else "--"
        lines.append(
            f"{dashes(season)} & \\num{{{r.flights}}} & \\num{{{r.with_track}}} & "
            f"\\num{{{r.downloaded}}} & {share} \\\\\n"
        )
    lines += ["\\bottomrule\n", "\\end{tabular}\n"]
    return "".join(lines)


def macros(prefix: str, catalog: pd.DataFrame, seasons: pd.DataFrame) -> dict:
    """Numbers quoted in the text, as {macro name: value}."""
    flights, with_track, downloaded = seasons.sum()
    # Incomplete dates, such as 0000-00-00 or 2000-00-00, are not calendar dates.
    undated = pd.to_datetime(catalog["date"], format="%Y-%m-%d", errors="coerce").isna()
    share = undated.groupby(catalog["season"]).mean()
    p = prefix
    return {
        f"{p}Seasons": len(seasons),
        f"{p}SeasonFirst": dashes(seasons.index[0]),
        f"{p}SeasonLast": dashes(seasons.index[-1]),
        f"{p}Flights": flights,
        f"{p}WithTrack": with_track,
        f"{p}WithTrackPct": f"{pct(with_track, flights):.1f}",
        f"{p}Downloaded": downloaded,
        f"{p}DownloadedPct": f"{pct(downloaded, with_track):.1f}",  # of the tracks
        f"{p}Undated": undated.sum(),
        f"{p}UndatedPct": f"{pct(undated.sum(), flights):.2g}",
        # The season that loses the largest share of its flights to a date cut.
        f"{p}UndatedWorstSeason": dashes(share.idxmax()) if undated.any() else "--",
        f"{p}UndatedWorstPct": f"{100 * share.max():.2g}",
    }


def main() -> None:
    config = yaml.safe_load((REPO / "configs" / "download.yaml").read_text())
    values, tables = {}, {}
    # For each discipline: read the catalog, then compute its macros and its table.
    for discipline, prefix in PREFIX.items():
        path = ffvl.catalog_path(Path(config[discipline]["root"]))
        # No catalog (disk not mounted): write nothing, so the committed files stay.
        if not path.exists():
            print(f"{path} not found (is the disk mounted?): keeping the committed files.")
            return
        catalog = pd.read_csv(path, dtype=str)  # empty cells are read as missing
        seasons = per_season(catalog)
        values |= macros(prefix, catalog, seasons)
        tables[prefix.lower()] = table(seasons)

    # All macros go in one file, each table in its own.
    OUT.mkdir(exist_ok=True)
    lines =[HEADER] + [f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in values.items()]
    (OUT / "02-dataset-values.tex").write_text("".join(lines))
    for name, text in tables.items():
        (OUT / f"02-dataset-seasons-{name}.tex").write_text(text)
    print(f"Wrote {len(values)} macros and {len(tables)} tables in {OUT}")


if __name__ == "__main__":
    main()
