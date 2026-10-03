# Building the thesis

```bash
thesis/build.sh
```

The script runs, from `thesis/`:

1. `scripts/config.py`: one macro per threshold of `configs/preprocessing.yaml`.
2. `scripts/02_dataset.py`: the numbers and the season tables of chapter 2, from the
   two catalogs of the [download](download.md). Without the data folder it prints a
   warning and leaves the committed files as they are.
3. `latexmk -pdf main.tex`.

!!! note "The analysis is not rerun"
    `build.sh` only reads what is saved. Changing a threshold changes the value printed
    in the text, not the results that depend on it: rerun the analysis first.

## Generated files

All in `thesis/generated/`. Never edit them: the next build overwrites them.

| File | Written by | Holds | Read by |
|---|---|---|---|
| `config.tex` | `config.py` | the thresholds | `main.tex` |
| `02-dataset-values.tex` | `02_dataset.py` | the numbers of chapter 2 | `main.tex` |
| `02-dataset-seasons-para.tex` | `02_dataset.py` | the paraglider season table | `chapters/02-dataset.tex` |
| `02-dataset-seasons-hang.tex` | `02_dataset.py` | the hang-glider season table | `chapters/02-dataset.tex` |

The macro files are read in the preamble of `main.tex`, so every chapter can use them.
A table file holds only the `tabular`: its caption and label stay in the chapter.

## Macro names

- Thresholds: `cfg`, then the path of the key in CamelCase.
  `altitude.gnss_min_range_m` becomes `\cfgAltitudeGnssMinRangeM`. A macro name holds
  only letters, so `config.py` stops if a key contains a digit. A whole number such as
  `30.0` is written `30`.
- Dataset: `Para` (paragliders) or `Hang` (hang gliders), then the quantity:
  `\ParaFlights`, `\HangDownloadedPct`. The full list is in `02-dataset-values.tex`.

## Quoting a new number

- A threshold: add the key to `configs/preprocessing.yaml`, run `build.sh`, write its
  macro in the text.
- A result: the analysis saves it in the data folder; the chapter's script in
  `thesis/scripts/` reads it and writes a macro. A chapter without a script gets one,
  `NN_name.py` writing `generated/NN-name-*.tex`, plus a line in `build.sh`.
