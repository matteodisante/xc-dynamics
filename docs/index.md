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
scripts/            one entry point per task: reads configs/, calls src/
src/xc_dynamics/    the logic, one subpackage per function
configs/            settings: data folders, pre-processing thresholds
tests/              same structure as src/
docs/               this documentation
thesis/             the thesis, in LaTeX; build.sh compiles it
thesis/scripts/     write the numbers the text quotes, from saved results
thesis/generated/   what they write: macros and tables
```

[Architecture](architecture.md) shows how these parts depend on each other.

The guides explain how to run each task; the reference describes every function,
generated from the docstrings in the code.
