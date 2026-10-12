#!/bin/sh
# Rebuild the thesis: rewrite the numbers and figures in generated/, then compile.
# Without the data disk, dataset.py and preprocessing.py keep the committed files.
set -e
cd "$(dirname "$0")"
uv run python scripts/config.py
uv run python scripts/dataset.py
uv run python scripts/preprocessing.py
latexmk -pdf main.tex
