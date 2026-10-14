# Building the thesis

```bash
thesis/build.sh
```

The script runs, from `thesis/`:

1. `scripts/config.py`: one macro per threshold of `configs/preprocessing.yaml`.
2. `scripts/dataset.py`: the numbers and the season tables of the dataset chapter, from
   the two catalogs of the [download](download.md), and the sampling-interval figure.
3. `scripts/preprocessing.py`: the figures and the excursion table of the pre-processing
   chapter, from the results of the pre-processing scripts (see [Data folder](../data.md)).
4. `latexmk -pdf main.tex`.

Without the data folder, steps 2 and 3 print a warning and leave the committed files as
they are.

!!! note "The analysis is not rerun"
    `build.sh` only reads what is saved. Changing a threshold changes the value printed
    in the text, not the results that depend on it: rerun the analysis first.

## Names and order of the chapters

Files are named after the subject of their chapter, never after its number:
`chapters/preprocessing.tex`, `scripts/preprocessing.py`,
`generated/figures/preprocessing/`. The order of the chapters, and so their numbers, is
set in one place only: the list of `\input{chapters/...}` in `main.tex`. Moving a
chapter means moving one line there.

## Generated files

All in `thesis/generated/`, `.tex` files in `tex/` and figures in `figures/<chapter>/`.
Never edit them: the next build overwrites them. They are committed, so the thesis
compiles on a machine without the data folder.

| File | Written by | Holds | Read by |
|---|---|---|---|
| `tex/config.tex` | `config.py` | the thresholds | `main.tex` |
| `tex/dataset-values.tex` | `dataset.py` | the numbers of the dataset chapter | `main.tex` |
| `tex/dataset-seasons-para.tex` | `dataset.py` | the paraglider season table | `chapters/dataset.tex` |
| `tex/dataset-seasons-hang.tex` | `dataset.py` | the hang-glider season table | `chapters/dataset.tex` |
| `tex/preprocessing-excursion.tex` | `preprocessing.py` | the flights split and the fixes deleted by the excursion rule with W, half W and twice W | `chapters/preprocessing.tex` |
| `figures/dataset/sampling-interval.pdf` | `dataset.py` | the share of the tracks per sampling interval | `chapters/dataset.tex` |
| `figures/preprocessing/median-speed*.pdf` | `preprocessing.py` | the median speed of every flight, by discipline and by wing class | `chapters/preprocessing.tex` |
| `figures/preprocessing/top-speed.pdf` | `preprocessing.py` | the speed of steps and over windows, by wing class | `chapters/preprocessing.tex` |
| `figures/preprocessing/excursion-rule.pdf` | `preprocessing.py` | the excursion rule on two synthetic tracks; drawn without the data folder | `chapters/preprocessing.tex` |
| `figures/preprocessing/excursion-real-flight.pdf` | `preprocessing.py` | real flight faster than the top speed, split or not; drawn without the data folder | `chapters/preprocessing.tex` |

The macro files are read in the preamble of `main.tex`, so every chapter can use them.
A table file holds only the `tabular`: its caption and label stay in the chapter.

## Macro names

- Thresholds: `cfg`, then the path of the key in CamelCase.
  `altitude.gnss_min_range_m` becomes `\cfgAltitudeGnssMinRangeM`. A macro name holds
  only letters, so `config.py` stops if a key contains a digit. A whole number such as
  `30.0` is written `30`.
- Dataset: `Para` (paragliders) or `Hang` (hang gliders), then the quantity:
  `\ParaFlights`, `\HangDownloadedPct`. The full list is in `tex/dataset-values.tex`.

## Quoting a new number

- A threshold: add the key to `configs/preprocessing.yaml`, run `build.sh`, write its
  macro in the text.
- A result: the analysis saves it in the data folder; the chapter's script in
  `thesis/scripts/` reads it and writes a macro or a figure. A chapter without a script
  gets one, `<subject>.py` writing `generated/tex/<subject>-*.tex` and
  `generated/figures/<subject>/`, plus a line in `build.sh`.
