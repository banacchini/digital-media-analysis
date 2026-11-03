"""Convert the raw CSV exports to the parquet tables the analysis notebooks read.

Reads `data/raw/{users,swipes,profile_history}.csv` and writes
`data/processed/{name}.parquet`. Only the columns needed for H2 are kept, so `bio` and
`interests` are never loaded (see `data/README.md`). Identifiers stay strings, `day` and
`version` become integers, and the script stops with a clear message when a column is missing
or a value is unexpected. It prints shapes and counts only, never rows.

Usage (from the repository root):

    python -m rentfriends.csv_to_parquet
    python -m rentfriends.csv_to_parquet --raw data/raw --out data/processed users swipes
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DIRECTIONS = {"left", "right"}


@dataclass(frozen=True)
class TableSpec:
    """Columns to keep for one table, split by the dtype they are stored as."""

    text: tuple[str, ...]
    integer: tuple[str, ...] = ()

    @property
    def columns(self) -> list[str]:
        return [*self.text, *self.integer]


SPECS: dict[str, TableSpec] = {
    "users": TableSpec(text=("user_key", "sex", "age_band", "city")),
    "swipes": TableSpec(
        text=("user_key", "target_type", "target_user_key", "direction"),
        integer=("day",),
    ),
    "profile_history": TableSpec(
        text=("user_key", "sex", "age_band", "city"),
        integer=("version", "day"),
    ),
}


class ConversionError(ValueError):
    """Raised when a CSV does not match the expected schema."""


def convert_table(name: str, csv_path: Path, out_path: Path) -> tuple[int, int]:
    """Convert one CSV to parquet and return its (rows, columns)."""
    spec = SPECS[name]
    if not csv_path.exists():
        raise ConversionError(f"{name}: file not found: {csv_path}")

    header = pd.read_csv(csv_path, nrows=0).columns
    missing = [c for c in spec.columns if c not in header]
    if missing:
        raise ConversionError(
            f"{name}: missing columns {missing}. The CSV has {len(header)} columns: {list(header)}"
        )

    df = pd.read_csv(
        csv_path,
        usecols=spec.columns,
        dtype=dict.fromkeys(spec.text, "string"),
    )[spec.columns]

    for col in spec.integer:
        n_null = int(df[col].isna().sum())
        if n_null:
            raise ConversionError(f"{name}.{col}: {n_null} empty values, expected whole numbers")
        numeric = pd.to_numeric(df[col], errors="coerce")
        n_bad = int(numeric.isna().sum())
        if n_bad:
            raise ConversionError(f"{name}.{col}: {n_bad} values are not numbers")
        df[col] = numeric.astype("int64")

    if name == "swipes":
        unexpected = df.loc[~df["direction"].isin(DIRECTIONS), "direction"]
        if len(unexpected):
            counts = unexpected.fillna("<empty>").value_counts().to_dict()
            raise ConversionError(
                f"swipes.direction: expected {sorted(DIRECTIONS)}, found other values: {counts}"
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return df.shape


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw"), help="folder with CSV files")
    parser.add_argument(
        "--out", type=Path, default=Path("data/processed"), help="folder for parquet files"
    )
    parser.add_argument(
        "tables",
        nargs="*",
        choices=list(SPECS),
        help="tables to convert (default: all)",
    )
    args = parser.parse_args(argv)

    failed = False
    for name in args.tables or list(SPECS):
        try:
            rows, cols = convert_table(name, args.raw / f"{name}.csv", args.out / f"{name}.parquet")
        except ConversionError as err:
            print(f"ERROR {err}")
            failed = True
        else:
            print(f"ok    {name}: {rows} rows, {cols} columns -> {args.out / f'{name}.parquet'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
