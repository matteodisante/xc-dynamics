# Data folder

Every file the code writes or reads outside the repository: where it is, how much space
it takes, which script writes it and which read it, and what is inside. Each discipline
has two folders, set in `configs/download.yaml` or passed as `--root` and `--tracks`:

- the **data folder** (`root`): flight lists, catalog and results;
- the **tracks folder** (`tracks`): the IGC files, read-only for everything but the download.

Here the tracks folder is the data folder of the
[XC Thermal Viewer](https://github.com/matteodisante/xc-thermal-viewer), so the archive is
not stored twice. Saved paths are relative to these folders, so the files stay valid
wherever the disk is mounted.

!!! note "Sizes and examples"
    Sizes are those of 15 October 2026: downloads and new runs change them. In the
    examples the personal fields (pilot, club, identifiers) are replaced by placeholders,
    since this site is public; everything else is copied from the files.

## Layout

On the disk `SSD_DATA` (279 GiB, about half used), with the space each part takes:

```text
SSD_DATA/
├── paragliders/ffvl_cfd_igc/                 data folder, paragliders        390 MB
│   ├── raw/raw_xml/<year>.xml                flight lists, one per season    170 MB
│   ├── catalog/catalog.csv                   one row per flight               79 MB
│   ├── derived/<area>/<result>/              results the thesis reads         58 MB
│   └── scratch/<area>/<result>/              trials, same layout, never read   3 MB
├── hang_gliders/delta_cfd_igc/               data folder, hang gliders        26 MB
│   └── ...                                   same layout: lists 9 MB, catalog 3 MB, results 6 MB
└── xc-viewer-data/
    ├── paragliders/raw/igc/<season>/<date>_<flight_id>.igc
    │                                         tracks folder: 186 052 tracks    72 GB
    └── hang_gliders/raw/igc/<season>/<date>_<flight_id>.igc
                                              tracks folder: 6 716 tracks     2.0 GB
```

The tracks hold 65 GB and 1.7 GB of data; they take more on disk because the disk
allocates space in fixed blocks, and a small file fills its last block only in part. The
totals of the data folders include a few files of the old repository, and the viewer
folders hold the viewer's own files: see [Files not used here](#files-not-used-here).

Results are grouped by [area](architecture.md#areas), then named by what they hold.

## Files

| File | Written by | Holds | Read by |
|---|---|---|---|
| `raw/raw_xml/<year>.xml` | `scripts/download/download_ffvl.py` | the flight list of a season, as the CFD serves it | `download_ffvl.py` |
| `catalog/catalog.csv` | `scripts/download/download_ffvl.py` | one row per flight | `flight_speeds.py`, `speed_histograms.py`, `excursion_counts.py`, `vertical_histograms.py`, `vertical_counts.py`, `thesis/scripts/dataset.py`, `thesis/scripts/preprocessing.py` |
| `raw/igc/<season>/*.igc` (tracks folder) | `scripts/download/download_ffvl.py` | the track of a flight | `flight_speeds.py`, `speed_histograms.py`, `excursion_counts.py`, `vertical_histograms.py`, `vertical_counts.py`, through the catalog's `local_path` |
| `derived/preprocessing/speed/flights.csv` | `scripts/preprocessing/flight_speeds.py` | one row per flight: the counters and verdicts of the pre-processing steps, the median and 90th percentile of its step speed | `thesis/scripts/preprocessing.py` |
| `derived/preprocessing/speed/run.yaml` | `scripts/preprocessing/flight_speeds.py` | the record of the run | you, before the thesis uses the result |
| `derived/preprocessing/speed_histograms/counts.npz` | `scripts/preprocessing/speed_histograms.py` | for each wing class, the number of steps and of windows of `excursion.window_s` seconds per km/h of speed, with the bin edges | `thesis/scripts/preprocessing.py` |
| `derived/preprocessing/speed_histograms/run.yaml` | `scripts/preprocessing/speed_histograms.py` | the record of the run | you, before the thesis uses the result |
| `derived/preprocessing/excursion/flights.csv` | `scripts/preprocessing/excursion_counts.py` | one row per flight: the sampling interval of the track as read, the counters and verdicts of the steps before the excursion rule, the fixes the rule receives, and the fixes it deletes and the splits it makes with `excursion.window_s`, `excursion.window_short_s` and `excursion.window_long_s` | `thesis/scripts/dataset.py`, `thesis/scripts/preprocessing.py` |
| `derived/preprocessing/excursion/run.yaml` | `scripts/preprocessing/excursion_counts.py` | the record of the run | you, before the thesis uses the result |
| `derived/preprocessing/vertical_histograms/counts.npz` | `scripts/preprocessing/vertical_histograms.py` | for each wing class, the number of steps and of windows of `excursion.window_s` seconds per m/s of absolute vertical speed, from the GNSS and from the pressure altitude, in the flights whose barometer is a witness | `thesis/scripts/preprocessing.py` |
| `derived/preprocessing/vertical_histograms/run.yaml` | `scripts/preprocessing/vertical_histograms.py` | the record of the run | you, before the thesis uses the result |
| `derived/preprocessing/vertical/flights.csv` | `scripts/preprocessing/vertical_counts.py` | one row per flight: the counters and verdicts of the steps before the vertical excursion rule, the fixes the rule receives, the fixes it deletes and the splits it makes, and the same on the pressure altitude of the witness flights | `thesis/scripts/preprocessing.py` |
| `derived/preprocessing/vertical/run.yaml` | `scripts/preprocessing/vertical_counts.py` | the record of the run | you, before the thesis uses the result |

What each file holds, column by column, is in [Formats](#formats).

## Formats

### Flight list

`raw/raw_xml/<year>.xml`, one file per season, named after its first year: the flights
declared in that season, saved as the CFD serves them at
`https://parapente.ffvl.fr/cfd/liste/<year>?xml=1` (hang gliders: `delta.ffvl.fr`) and
never replaced. One `<flight>` element per flight, whose attributes become the columns of
the [catalog](#catalog). The start of a list, with some attributes left out and the
attributes of the flight on several lines for legibility:

```xml
<ffvldata url="https://parapente.ffvl.fr/cfd/liste/2024" comment="generated from www.ffvl.fr" ...>
<cfdflightlist nb_flights="10906">
<flights>
<flight id="20123456" date="2025-03-31" pilot="NAME SURNAME" club="CLUB NAME"
  flight_type="Dist 3 pts" distance="96.52" points="96.52" duration="12320" speed="28.203895"
  takeOff="St Marc d'Ouilly" landing="La Petite Claye (prés D576)" depNum="14"
  aile="Boomerang 12" aile_class="CIVL Competition Class"
  flight_link="https://parapente.ffvl.fr/cfd/liste/vol/20123456"
  pilot_link="https://parapente.ffvl.fr/pilote/1234/2025" igc_tracklog="123456"
  igc_tracklog_link="https://parapente.ffvl.fr/sites/parapente.ffvl.fr/files/igcfiles/2025-03-31-igcfile-1234-123456.igc" .../>
```

### Catalog

`catalog/catalog.csv`: one row per flight of all the saved lists, written by
`download_ffvl.py` from the lists and the tracks on disk. Comma-separated, with a header;
an empty cell is a missing value.

| Column | Meaning | From the XML |
|---|---|---|
| `flight_id` | CFD number of the flight; its page is `https://parapente.ffvl.fr/cfd/liste/vol/<flight_id>` (or `delta.ffvl.fr`) | `id` |
| `season`, `season_year` | the season, `2024-2025`, and its first year, `2024` | the list it comes from |
| `date` | date of the flight, `YYYY-MM-DD`; can be incomplete (`2000-00-00`) or empty | `date` |
| `pilot`, `club` | the pilot and their club | `pilot`, `club` |
| `flight_type` | scoring category of the declared route | `flight_type` |
| `distance_km`, `points` | scored distance (km) and CFD score | `distance`, `points` |
| `duration_s`, `speed` | duration (s) and speed (km/h) as declared; 0 or empty when not given | `duration`, `speed` |
| `takeoff`, `landing`, `dept` | take-off and landing sites, French department number | `takeOff`, `landing`, `depNum` |
| `wing`, `wing_class` | glider model and class (thesis, section Glider categories) | `aile`, `aile_class` |
| `flight_link`, `pilot_link` | pages of the flight and of the pilot | same names |
| `igc_link`, `tracklog_id` | URL and number of the track; `igc_link` is empty when the flight has none | `igc_tracklog_link`, `igc_tracklog` |
| `local_path` | the track on disk, relative to the tracks folder; empty when not downloaded | none |

```text
flight_id,season,season_year,date,pilot,flight_type,distance_km,points,duration_s,speed,takeoff,landing,dept,club,wing,wing_class,flight_link,igc_link,tracklog_id,pilot_link,local_path
20123456,2024-2025,2024,2025-03-31,NAME SURNAME,Dist 3 pts,96.52,96.52,12320,28.203895,St Marc d'Ouilly,La Petite Claye (prés D576),14,CLUB NAME,Boomerang 12,CIVL Competition Class,https://parapente.ffvl.fr/cfd/liste/vol/20123456,https://parapente.ffvl.fr/sites/parapente.ffvl.fr/files/igcfiles/2025-03-31-igcfile-1234-123456.igc,123456,https://parapente.ffvl.fr/pilote/1234/2025,raw/igc/2024-2025/2025-03-31_20123456.igc
```

### Track

`raw/igc/<season>/<date>_<flight_id>.igc` in the tracks folder: the track as uploaded to
the CFD, an IGC file of the FAI standard. Plain text, one record per line, whose first
letter gives its type: `A` the recorder, `H` a header (date, pilot, glider, recorder,
altitude datum), `B` a fix.
[`read_igc`][xc_dynamics.preprocessing.igc.read_igc] reads only the `B` records. The start
of a track, with some headers left out:

```text
AXTR0A8689C64730
HFDTE310325
HFPLTPILOTINCHARGE:NAME SURNAME
HFGTYGLIDERTYPE:GIN Bonanza 3
HFDTM100GPSDATUM:WGS84
HFFTYFRTYPE:XC_Tracer_Maxx_II
HFALG:GEO
B1044004852956N00026682WA0004800189
B1044014852958N00026682WA0005000190
B1044024852960N00026681WA0005100191
```

`HFDTE` gives the date (31 March 2025), `HFALG` the datum of the GNSS altitude (`GEO`,
the geoid). A `B` record has fixed columns; anything after the GNSS altitude is ignored:

```text
B 104400 4852956N 00026682W A 00048 00189
  │      │        │         │ │     └ GNSS altitude: 189 m
  │      │        │         │ └ pressure altitude: 48 m
  │      │        │         └ validity: A for a 3D fix, V without one
  │      │        └ longitude: 0° 26.682' W
  │      └ latitude: 48° 52.956' N
  └ UTC time: 10:44:00
```

### Per-flight tables

`derived/preprocessing/speed/flights.csv`, written by `flight_speeds.py`,
`derived/preprocessing/excursion/flights.csv`, written by `excursion_counts.py`, and
`derived/preprocessing/vertical/flights.csv`, written by `vertical_counts.py`: one row per
flight with a track, in the order of the catalog. All start with the columns of
[`before_horizontal`][xc_dynamics.preprocessing.flight.before_horizontal], and each adds
its own. A cell is empty when the flight stopped before the step that fills it, and an
unreadable file gets only `flight_id` and `error`.

| Column | Meaning | speed | excursion | vertical |
|---|---|:-:|:-:|:-:|
| `flight_id` | as in the catalog | ✓ | ✓ | ✓ |
| `error` | why the file could not be read; the column exists only if some file could not | ✓ | ✓ | ✓ |
| `fixes_read` | `B` records read | ✓ | ✓ | ✓ |
| `sampling_s` | sampling interval of the track as read, s ([`sampling_interval`][xc_dynamics.preprocessing.sampling.sampling_interval]) | ✓ | ✓ | ✓ |
| `gnss_present`, `baro_present` | share of the fixes read with a GNSS or a pressure altitude | ✓ | ✓ | ✓ |
| `gnss_range_m`, `baro_range_m` | highest minus lowest altitude of that channel, m | ✓ | ✓ | ✓ |
| `gnss_ok` | kept by the altitude channel | ✓ | ✓ | ✓ |
| `baro_witness` | the barometer passes the same test, and its range is within `altitude.baro_witness_range_tolerance` of the GNSS range | ✓ | ✓ | ✓ |
| `altitude_deleted` | fixes deleted because they have no GNSS altitude | ✓ | ✓ | ✓ |
| `clock_deleted`, `repeated_deleted` | fixes deleted by the clock and the repeated-position rules | ✓ | ✓ | ✓ |
| `median_kmh` | median step speed, km/h | ✓ | ✓ | ✓ |
| `speed_ok` | kept by the fast-track rule | ✓ | ✓ | ✓ |
| `steps`, `p90_kmh` | number of steps and 90th percentile of their speed, km/h | ✓ | | |
| `horizontal_fixes` | fixes the horizontal excursion rule receives | | ✓ | |
| `horizontal_deleted`, `horizontal_splits` | fixes it deletes and splits it makes with `excursion.window_s` | | ✓ | ✓ |
| `short_deleted`, `short_splits` | the same with `excursion.window_short_s` | | ✓ | |
| `long_deleted`, `long_splits` | the same with `excursion.window_long_s` | | ✓ | |
| `vertical_fixes` | fixes the vertical excursion rule receives | | | ✓ |
| `vertical_deleted`, `vertical_splits` | fixes it deletes and splits it makes on the GNSS altitude | | | ✓ |
| `baro_fixes`, `baro_deleted`, `baro_splits` | the same on the pressure altitude, in the witness flights only | | | ✓ |

The start of `excursion/flights.csv`. The third flight fails the altitude channel and the
fourth the fast-track rule, so the cells of the steps they do not reach are empty:

```text
flight_id,fixes_read,sampling_s,gnss_present,gnss_range_m,baro_present,baro_range_m,gnss_ok,baro_witness,altitude_deleted,clock_deleted,repeated_deleted,median_kmh,speed_ok,horizontal_fixes,horizontal_deleted,horizontal_splits,short_deleted,short_splits,long_deleted,long_splits
20123456,2334,5.0,0.987146529562982,3068.0,1.0,2945.0,True,True,30,0,4,29.96217307778665,True,2300,0,0,0,0,0,0
20123457,4224,2.0,0.9955018939393939,742.0,0.9992897727272727,716.0,True,True,19,0,24,22.81868431909124,True,4181,0,0,0,0,0,0
20123458,425,31.0,0.0,0.0,0.0,0.0,False,False,,,,,,,,,,,,
20123459,500,1.0,1.0,1551.0,1.0,1551.0,True,True,0,0,1,280.8930657606387,False,,,,,,,
```

### Speed histograms

`derived/preprocessing/speed_histograms/counts.npz`: a NumPy archive of four arrays,
read with `np.load`, with one row per wing class of the catalog and one column per speed
bin.

| Array | Shape and type | Holds |
|---|---|---|
| `speed_edges_kmh` | 402, float | bin edges: 0 to 400 km/h by 1 km/h, then infinity |
| `wing_classes` | one per class, text | the wing class of each row, as in the catalog; `''` for none |
| `steps` | classes × 401, integer | steps between fixes in each bin |
| `windows` | classes × 401, integer | windows of `excursion.window_s` seconds in each bin |

```python
>>> z = np.load("counts.npz")
>>> z["wing_classes"][:3]
array(['', '0', 'A ou 1'], dtype='<U24')
>>> z["steps"].shape  # paragliders: 12 wing classes
(12, 401)
```

### Vertical speed histograms

`derived/preprocessing/vertical_histograms/counts.npz`: a NumPy archive of six arrays,
read with `np.load`, with one row per wing class of the catalog and one column per bin of
absolute vertical speed. Only the flights whose barometer is a witness are counted.

| Array | Shape and type | Holds |
|---|---|---|
| `vertical_edges_ms` | 103, float | bin edges: 0, then 0.5 to 100.5 m/s by 1 m/s, then infinity; every bin but the first and the last is centred on a whole m/s |
| `wing_classes` | one per class, text | the wing class of each row, as in the catalog; `''` for none |
| `gnss_steps`, `baro_steps` | classes × 102, integer | steps between fixes in each bin, from the GNSS and from the pressure altitude |
| `gnss_windows`, `baro_windows` | classes × 102, integer | windows of `excursion.window_s` seconds in each bin, from each channel |

### Run record

`run.yaml`, next to every result: which code produced it, on which machine and with which
thresholds, so it can be checked before the thesis uses it (see
[Running on another machine](guides/other-machine.md#how-it-stays-consistent)). Every
script writes the fields up to `thresholds`; the counts after them depend on the script.
The record of `excursion_counts.py` for paragliders:

```yaml
command: scripts/preprocessing/excursion_counts.py para
commit: 3f0276aeda52b895b16312877b94965b8af46b48
uncommitted_changes: false
machine: HOST.local
system: macOS-26.6.2-arm64-arm-64bit
python: 3.12.13
started: '2026-10-15T15:24:00+02:00'
discipline: para
root: /Volumes/SSD_DATA/paragliders/ffvl_cfd_igc
tracks: /Volumes/SSD_DATA/xc-viewer-data/paragliders
sample: null
thresholds:
  altitude:
    gnss_present_min: 0.95
    gnss_min_range_m: 30.0
    baro_witness_present_min: 0.95
    baro_witness_min_range_m: 30.0
    baro_witness_range_tolerance: 0.1
  speed:
    max_kmh: 100.0
    median_max_kmh: 70.0
  excursion:
    window_s: 20.0
    window_short_s: 10.0
    window_long_s: 40.0
flights: 186052
unreadable: 0
judged: 185321
split: 1663
split_short: 3685
split_long: 776
finished: '2026-10-15T15:45:44+02:00'
```

## Files not used here

The disk also holds files that no code of this repository writes or reads:

- `catalog/catalog.old.csv` (87 MB for paragliders, 4 MB for hang gliders): the catalog
  of the old repository, soaring-anomalous-transport, kept when the catalog was rebuilt.
  It has two more columns, `downloaded` and `file_size`.
- `catalog/seasons_index.csv`: one row per season of the old download, with its URLs and
  counts (`season_year`, `season`, `list_url`, `xml_url`, `n_flights`, `n_with_igc`,
  `n_downloaded`).
- `logs/download.log` and `logs/failures.csv`: the log of the old download and the tracks
  it failed to fetch (`flight_id`, `season`, `igc_link`, `error`).
- `catalog/` and `derived/` in the tracks folders: the viewer's own files, 50 GB for
  paragliders (43 GB of them in `derived/fixes.parquet`) and 1 GB for hang gliders.
- files whose name starts with `._`: metadata that macOS writes on this disk.

## Results and trials

A full run writes in `derived/`, and a new run overwrites the previous one: its `run.yaml`
says which commit produced it. A run with `--sample` writes the same files in `scratch/`,
which nothing reads and which can be deleted at any time.

## Adding a result

A script that saves a result writes it in `derived/<area>/<result>/`, next to a
`run.yaml`; its files get a row in the table of [Files](#files) and their format in
[Formats](#formats).
