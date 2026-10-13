# Data folder

Every file the code writes or reads outside the repository, with the script that writes
it and the scripts that read it. Each discipline has two folders, set in
`configs/download.yaml` or passed as `--root` and `--tracks`:

- the **data folder** (`root`): flight lists, catalog and results;
- the **tracks folder** (`tracks`): the IGC files, read-only for everything but the download.

Here the tracks folder is the data folder of the
[XC Thermal Viewer](https://github.com/matteodisante/xc-thermal-viewer), so the archive is
not stored twice. Saved paths are relative to these folders, so the files stay valid
wherever the disk is mounted.

## Layout

```text
data folder
├── raw/raw_xml/<year>.xml                  flight list of a season
├── catalog/catalog.csv                     one row per flight
├── derived/<area>/<result>/                results the thesis reads
└── scratch/<area>/<result>/                trials, same layout, never read

tracks folder
└── raw/igc/<season>/<date>_<flight_id>.igc one track per flight
```

Results are grouped by [area](architecture.md#areas), then named by what they hold.

## Files

| File | Written by | Holds | Read by |
|---|---|---|---|
| `raw/raw_xml/<year>.xml` | `scripts/download/download_ffvl.py` | the flight list of a season, as the CFD serves it | `download_ffvl.py` |
| `catalog/catalog.csv` | `scripts/download/download_ffvl.py` | one row per flight, see [Catalog](guides/download.md#catalog) | `flight_speeds.py`, `thesis/scripts/dataset.py`, `thesis/scripts/preprocessing.py` |
| `raw/igc/<season>/*.igc` (tracks folder) | `scripts/download/download_ffvl.py` | the track of a flight | `flight_speeds.py`, through the catalog's `local_path` |
| `derived/preprocessing/speed/flights.csv` | `scripts/preprocessing/flight_speeds.py` | one row per flight: the counters and verdicts of the pre-processing steps, the median and 90th percentile of its step speed | `thesis/scripts/preprocessing.py` |
| `derived/preprocessing/speed/run.yaml` | `scripts/preprocessing/flight_speeds.py` | the [record](guides/other-machine.md#how-it-stays-consistent) of the run | you, before the thesis uses the result |
## Results and trials

A full run writes in `derived/`, and a new run overwrites the previous one: its `run.yaml`
says which commit produced it. A run with `--sample` writes the same files in `scratch/`,
which nothing reads and which can be deleted at any time.

## Adding a result

A script that saves a result writes it in `derived/<area>/<result>/`, next to a
`run.yaml`, and its files get a row in the table above.
