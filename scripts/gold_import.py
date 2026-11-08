"""Import annotator exports into data/private/gold/labels_long.parquet (standalone script).

Usage: uv run python scripts/gold_import.py --input A=exportA.json --input B=exportB.json \
    --input C=exportC.json
Accepts Label Studio full-JSON exports (*.json) or the filled annotator CSVs (*.csv).
Validates: each annotator has exactly their 50 items, each bio exactly 2 annotators, values 0/1,
no duplicates. Prints only integers. Exit codes: 0 ok, 2 validation errors, 1 other error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

SIGNALS = ("towarzyskie", "spokoj", "rytm", "intencja")
ANNOTATORS = ("A", "B", "C")
YES, NO = {"1", "tak", "yes", "true"}, {"0", "nie", "no", "false"}


def load(path: Path) -> pd.DataFrame:
    if path.suffix.lower() != ".json":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = []
    for t in json.loads(path.read_text(encoding="utf-8")):
        row = {"item_id": t["data"]["item_id"]}
        anns = t.get("annotations") or []
        for r in anns[0].get("result", []) if anns else []:
            ch = r.get("value", {}).get("choices", [])
            if r.get("from_name") in SIGNALS and len(ch) == 1:
                c = str(ch[0]).strip().casefold()
                row[r["from_name"]] = "1" if c in YES else "0" if c in NO else ""
        rows.append(row)
    return pd.DataFrame(rows, columns=["item_id", *SIGNALS]).fillna("")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-dir", default="data/private/gold")
    ap.add_argument("--input", action="append", required=True, metavar="ANNOTATOR=PATH")
    a = ap.parse_args()
    try:
        gold = Path(a.gold_dir)
        master = pd.read_parquet(gold / "gold_master.parquet", columns=["item_id", "annotators"])
        pairs = list(zip(master["item_id"], master["annotators"], strict=True))
        frames = {k: load(Path(p)) for k, _, p in (s.partition("=") for s in a.input)}
        errs = dict.fromkeys(["missing", "unexpected", "duplicates", "bad_values"], 0)
        parts = []
        for ann in ANNOTATORS:
            expected = {i for i, s in pairs if ann in s}
            df = frames.get(ann)
            if df is None:
                errs["missing"] += len(expected)
                continue
            errs["duplicates"] += int(df["item_id"].duplicated().sum())
            errs["unexpected"] += int((~df["item_id"].isin(expected)).sum())
            errs["missing"] += len(expected - set(df["item_id"]))
            df = df[df["item_id"].isin(expected)].drop_duplicates("item_id")
            for s in SIGNALS:
                v = pd.to_numeric(df[s].replace("", None), errors="coerce")
                ok = v.isin([0, 1])
                errs["bad_values"] += int((~ok).sum())
                parts.append(
                    pd.DataFrame(
                        {"item_id": df["item_id"][ok], "annotator": ann, "signal": s,
                         "value": v[ok].astype(int)}
                    )
                )  # fmt: skip
        long = pd.concat(parts, ignore_index=True)
        n_err = sum(errs.values())
        print(f"n_items={long['item_id'].nunique()}\nn_annotations={len(long)}")
        print(f"n_validation_errors={n_err}")
        for k, v in errs.items():
            if v:
                print(f"err_{k}={v}")
        if n_err:
            return 2
        long.to_parquet(gold / "labels_long.parquet", index=False)
    except Exception as e:  # noqa: BLE001 - type only: messages may carry values
        print(f"error_type={type(e).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
