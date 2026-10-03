#!/bin/sh
# Rebuild the thesis: rewrite the numbers in generated/, then compile.
# Without the data disk, 02_dataset.py keeps the committed numbers.
set -e
cd "$(dirname "$0")"
uv run python scripts/config.py
uv run python scripts/02_dataset.py
latexmk -pdf main.tex
