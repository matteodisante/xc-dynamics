"""The thresholds of the analysis, as LaTeX macros.

Every key of the configs below becomes a macro named after its path, with the cfg
prefix: altitude.gnss_min_range_m -> \\cfgAltitudeGnssMinRangeM. The thesis quotes a
threshold only through its macro, so the text cannot disagree with the config.

    uv run python thesis/scripts/config.py
"""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CONFIGS = ["preprocessing.yaml"]  # download.yaml holds machine paths, not thresholds
OUT = REPO / "thesis" / "generated" / "config.tex"


def flatten(config: dict, name: str = "cfg"):
    """Yield (macro name, value) for every leaf of a nested config."""
    for key, value in config.items():
        leaf = name + key.title().replace("_", "")  # gnss_min_range_m -> GnssMinRangeM
        if isinstance(value, dict):
            yield from flatten(value, leaf)
        else:
            yield leaf, value


def main() -> None:
    lines = ["% Written by thesis/scripts/config.py: do not edit.\n"]
    for file in CONFIGS:
        config = yaml.safe_load((REPO / "configs" / file).read_text())
        for name, value in flatten(config):
            if not name.isalpha():
                raise ValueError(f"{name}: a LaTeX macro name can only hold letters")
            if isinstance(value, float) and value.is_integer():
                value = int(value)  # 30.0 -> 30
            lines.append(f"\\newcommand{{\\{name}}}{{{value}}}\n")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(lines))
    print(f"Wrote {len(lines) - 1} macros in {OUT}")


if __name__ == "__main__":
    main()
