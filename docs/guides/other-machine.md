# Running on another machine

The analysis is developed on one machine, the hub, where the thesis is built. A long run
can happen on any other machine, macOS, Linux or Windows. The external disk carries the
data both ways; the other machine gets the code from GitHub and never pushes.

## How it stays consistent

- **Paths.** Saved files hold paths relative to the data folders (the catalog's
  `local_path`), so they work wherever the disk is mounted. Every script takes the
  folders on the command line, `--root` and `--tracks`.
- **Record.** A script that computes results, such as `flight_speeds.py`, saves a
  `run.yaml` next to them (the download does not): command, git commit,
  whether the code had uncommitted changes, machine, system, start and end time, and the
  thresholds it used.
- **Results and trials.** A full run writes in `derived/` of the data folder: these are the
  results the thesis reads. A trial (`--sample`) writes in `scratch/`, which nothing in the
  thesis reads and which can be deleted at any time.
- **Thesis.** Figures, tables and macros are made only on the hub, by `thesis/scripts/`,
  from what is in `derived/`. So it does not matter where a run happened.

## Setting up the machine

Once:

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). On Windows, in
   PowerShell:
   ```
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   On macOS and Linux:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Get the code (on Windows, in Git Bash) and its dependencies:
   ```bash
   git clone https://github.com/matteodisante/xc-dynamics.git
   cd xc-dynamics
   uv sync
   ```
   `uv sync` also installs the right version of Python.

## Running

1. On the hub, commit and push the code to run.
2. On the other machine, `git pull`. Do not edit files there: the run would be recorded
   with uncommitted changes, and they could not be pushed back.
3. Connect the disk and find where it is mounted: `/Volumes/SSD_DATA` on macOS, a drive
   letter on Windows (the partition named SSD_DATA). On Windows write paths as `X:/...`;
   Python does not understand the Git Bash form `/x/...`.
4. Try a sample first, then run on everything:
   ```bash
   uv run python scripts/preprocessing/flight_speeds.py hang --sample 200 \
       --root X:/hang_gliders/delta_cfd_igc --tracks X:/xc-viewer-data/hang_gliders
   uv run python scripts/preprocessing/flight_speeds.py hang \
       --root X:/hang_gliders/delta_cfd_igc --tracks X:/xc-viewer-data/hang_gliders
   ```
   A script uses every processor by default; `--workers N` leaves some free.

The folders on the disk, relative to its root:

| Discipline | `--root` | `--tracks` |
|---|---|---|
| para | `paragliders/ffvl_cfd_igc` | `xc-viewer-data/paragliders` |
| hang | `hang_gliders/delta_cfd_igc` | `xc-viewer-data/hang_gliders` |

## Back on the hub

Open the `run.yaml` next to the results, for instance
`derived/preprocessing/speed/run.yaml`, and check that:

- `commit` is the one pushed in step 1;
- `uncommitted_changes` is `false`;
- `sample` is empty, for a run the thesis will use.

Then build the thesis as usual (see [Building the thesis](thesis.md)).
