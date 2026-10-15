# xc-dynamics

Code for a master's thesis on the cross-country flights of paragliders and hang gliders.

## Installation

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:matteodisante/xc-dynamics.git
cd xc-dynamics
uv sync
```

## Repository layout

```text
src/xc_dynamics/    the logic, one subpackage per area
scripts/            one entry point per task, one folder per area: reads configs/, calls src/
configs/            settings, one file per area: data folders, pre-processing thresholds
tests/              same structure as src/
docs/               this documentation
thesis/             the thesis, in LaTeX; build.sh compiles it
thesis/scripts/     write the numbers and figures of the text, from saved results
thesis/generated/   what they write: macros and tables in tex/, figures in figures/
```

## Where to look

- [Architecture](architecture.md): how these parts depend on each other.
- [Data folder](data.md): every file on disk, who writes it, who reads it, what is inside.
- [Pre-processing](preprocessing.md): from each step of the thesis chapter to its code
  and thresholds.
- Guides: [downloading the data](guides/download.md),
  [building the thesis](guides/thesis.md), [running on another machine](guides/other-machine.md).
- [Reference](reference/download.md): every function, from the docstrings in the code.
