"""Download paraglider (para) or hang-glider (delta) flights from the FFVL CFD.

For each season: download the flight list if it is missing, then the missing tracks.
Finally rebuild the catalog. Rerun at any time: what is already on disk is skipped.
A saved flight list is never downloaded again; to update a season, delete its XML.

    uv run python scripts/download_ffvl.py para
    uv run python scripts/download_ffvl.py delta --seasons 2024 --root /tmp/test --limit 5

Data folders, seasons and parallel downloads are set in configs/download.yaml.
"""

import argparse
import sys
from pathlib import Path

import yaml
from tqdm import tqdm

from xc_dynamics.download import ffvl

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "download.yaml"


def parse_seasons(text: str) -> range:
    """'2024' or '2010-2015' -> season start years."""
    first, _, last = text.partition("-")
    return range(int(first), int(last or first) + 1)


def download_season(
    discipline: str, root: Path, year: int, workers: int, limit: int | None
) -> None:
    """Download the season's flight list if missing, then its missing tracks."""
    label = ffvl.season_label(year)
    if not ffvl.xml_path(root, year).exists():
        try:
            ffvl.fetch_xml(discipline, root, year)
        except RuntimeError as err:
            print(f"{label}: no flight list ({err})")
            return
    tracks = ffvl.missing_tracks(root, year)
    if limit:
        tracks = dict(list(tracks.items())[:limit])
    for error in tqdm(ffvl.download_tracks(tracks, workers), total=len(tracks), desc=label):
        if error:
            tqdm.write(f"  failed: {error}")


def write_catalog(root: Path) -> None:
    """Rebuild the catalog from the saved flight lists and write it to disk."""
    catalog = ffvl.build_catalog(root)
    path = ffvl.catalog_path(root)
    path.parent.mkdir(exist_ok=True)
    catalog.to_csv(path, index=False)
    print(f"{path}: {len(catalog)} flights")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download flights from the FFVL CFD.")
    parser.add_argument("discipline", choices=["para", "delta"])
    parser.add_argument("--seasons", help="2024 or 2010-2015 (default: from the config)")
    parser.add_argument("--root", type=Path, help="data folder (default: from the config)")
    parser.add_argument("--limit", type=int, help="max tracks per season, for tests")
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG.read_text())
    settings = config[args.discipline]
    root = args.root or Path(settings["root"])
    years = parse_seasons(str(args.seasons or settings["seasons"]))  # YAML reads 2024 as int
    if not root.parent.is_dir():  # otherwise we'd create folders under /Volumes
        sys.exit(f"{root.parent} not found: is the disk mounted?")

    for year in years:
        download_season(args.discipline, root, year, config["workers"], args.limit)
    write_catalog(root)


if __name__ == "__main__":
    main()
