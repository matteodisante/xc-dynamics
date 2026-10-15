# Downloading the data

The flights come from the CFD (Coupe Fédérale de Distance) of the French free-flight
federation (FFVL). For every season the CFD publishes the list of declared flights, each
with its GPS track in IGC format: paragliders on `parapente.ffvl.fr`, hang gliders on
`delta.ffvl.fr`.

## Usage

```bash
uv run python scripts/download/download_ffvl.py para    # paragliders
uv run python scripts/download/download_ffvl.py hang    # hang gliders
```

For each season the script downloads the flight list if it is not on disk, then the
tracks that are not on disk. At the end it rebuilds the catalog from all the saved lists.

A run can be stopped and restarted at any time: files already on disk are skipped, and
a file appears on disk only once it is complete. Tracks that fail are reported and tried
again at the next run.

## Settings

`configs/download.yaml` holds the settings that depend on the machine:

| Key | Meaning |
|---|---|
| `workers` | number of parallel downloads |
| `para.root`, `hang.root` | data folder: flight lists, catalog, results |
| `para.tracks`, `hang.tracks` | tracks folder, the one that holds `raw/igc/` |
| `para.seasons`, `hang.seasons` | seasons to download, e.g. `1999-2025` |

A season is named by its start year: `2024` is the season from 1 September 2024 to
31 August 2025.

These options override the settings for a single run:

| Option | Effect |
|---|---|
| `--seasons 2024`, `--seasons 2010-2015` | seasons to process |
| `--root PATH` | data folder |
| `--tracks PATH` | tracks folder |
| `--limit N` | at most N tracks per season, for tests |

!!! note "Updating a season"
    A saved flight list is never downloaded again, so a run cannot overwrite the archive.
    To update a season, usually the current one, delete its list and run the script again.
    Any list found in `raw/raw_xml/` is used, including one saved by hand from a browser.

## Output

The flight lists (`raw/raw_xml/<year>.xml`) and the catalog (`catalog/catalog.csv`, one
row per flight of the saved lists) go in the data folder, the tracks
(`raw/igc/<season>/<date>_<flight_id>.igc`) in the tracks folder. The two folders can be
the same; here the tracks folder is the data folder of the
[XC Thermal Viewer](https://github.com/matteodisante/xc-thermal-viewer), so the archive
is not stored twice.
Every file, with its columns and an example: [Data folder](../data.md).
