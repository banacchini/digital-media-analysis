"""Split bios into the 75-item gold set and the three annotator files (standalone script).

Reads users.parquet and profile_history.parquet, writes to data/private/gold/ (git-ignored):
gold_master.parquet, annotator_{A,B,C}.csv, annotator_{A,B,C}.labelstudio.json.

Never prints bio text: only integers and SHA-256 digests (rule G12). Procedure and the numbers
from the real run: docs/h3b/gold-sampling.md. Exit codes: 0 ok, 2 fewer than 75 candidates, 1 other.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261108
SIGNALS = ("towarzyskie", "spokoj", "rytm", "intencja")
QUOTAS = {"towarzyskie": 8, "spokoj": 8, "rytm": 7, "intencja": 7}
N_RANDOM = 45
N_TOTAL = N_RANDOM + sum(QUOTAS.values())
ANNOTATORS = ("A", "B", "C")
SET_ANNOTATORS = {1: "AB", 2: "AC", 3: "BC"}
STRATA = ("random", *(f"enriched_{s}" for s in SIGNALS))

# Frozen stems used ONLY to enrich the sample (they do not define the signals).
LEXICONS = {
    "towarzyskie": (
        "impre", "party", "parties", "towarzys", "wyjści", "klub", "koncert", "festiwal",
        "goście", "gości", "going out", "friends over", "social", "wychodz", "znajomi",
        "ekstrawert", "extrovert", "outgoing", "nightlife", "bar ",
    ),
    "spokoj": (
        "spok", "cisz", "domator", "domowni", "relaks", "quiet", "calm", "chill", "peaceful",
        "introwert", "homebody", "introvert", "stay in", "staying in", "wieczory w domu",
    ),
    "rytm": (
        "zdaln", "home office", "remote", "wfh", "work from home", "studiuj", "uczelni",
        "egzamin", "nocny", "nocy", "rannym ptak", "night owl", "early bird", "pracuj",
        "praca", "zmian", "nocami", "wcześnie wstaj", "working from home", "my studies",
        "exams", "i study",
    ),
    "intencja": (
        "szukam", "poszukuj", "na stałe", "długoterm", "krótkoterm", "współlokator", "wynajm",
        "wprowadz", "looking for", "flatmate", "roommate", "move in", "moving in", "wynajęt",
        "mieszkani", "pokój", "pokoj", "long term", "long-term", "short term", "short-term",
        "searching for", "i'm looking", "room in",
    ),
}  # fmt: skip

_SOCIAL = (
    r"ig|insta|instagram|snap|snapchat|fb|facebook|tiktok|tt|telegram|tg|whatsapp|wa"
    r"|discord|messenger|signal|x\.com|twitter"
)
_TLDS = r"com|pl|net|org|io|me|co|eu|info|app|ly|gg|tv|xyz|dev|ai|de|uk"
G12 = {  # personal-data screen; a matching text is excluded from the frame
    "phone": re.compile(r"(?<!\d)\+?\d(?:[\s.\-()/]?\d){8,}(?!\d)"),
    "email": re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+", re.I),
    "url": re.compile(r"https?://|www\.", re.I),
    "domain": re.compile(rf"\b[a-z0-9\-]+\.(?:{_TLDS})\b", re.I),
    "handle": re.compile(r"(?<!\w)@\w{2,}"),
    "social": re.compile(
        rf"\b(?:{_SOCIAL})\b\s*(?:[:=@\-]\s*@?[\w.]{{2,}}|\s(?=[\w.]*[\d_.])[\w.]{{3,}})", re.I
    ),
    "long_digits": re.compile(r"\d{6,}"),
}


def norm(t: object) -> str:
    return " ".join(t.split()) if isinstance(t, str) else ""


def digest(items: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(items)).encode("utf-8")).hexdigest()


def build_frame(users: pd.DataFrame, hist: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One normalised, G12-clean text per user (latest non-empty version), no Hyderabad."""
    u, h = users.copy(), hist.copy()
    u["user_key"], h["user_key"] = u["user_key"].astype(str), h["user_key"].astype(str)
    hyd = set(u.loc[u["city"] == "Hyderabad", "user_key"]) | set(
        h.loc[h["city"] == "Hyderabad", "user_key"]
    )
    h = h.sort_values(["day", "version"], kind="stable")
    h["rank"] = range(len(h))
    u["rank"] = len(h) + 1  # current profile is newer than every history version
    v = pd.concat([h[["user_key", "rank", "bio"]], u[["user_key", "rank", "bio"]]])
    v["text"] = v["bio"].map(norm)
    v = v[v["text"] != ""]
    with_bio = v["user_key"].nunique()
    v = v[~v["user_key"].isin(hyd)]
    latest = v.sort_values(["user_key", "rank"]).groupby("user_key").tail(1)
    latest = latest[["user_key", "text"]].sort_values("user_key").reset_index(drop=True)
    dedup = latest.drop_duplicates("text", keep="first").reset_index(drop=True)
    hits = {k: dedup["text"].map(lambda t, p=p: bool(p.search(t))) for k, p in G12.items()}
    flagged = pd.concat(hits, axis=1).any(axis=1)
    counts = {
        "n_users_total": len(set(u["user_key"]) | set(h["user_key"])),
        "n_users_with_bio": int(with_bio),
        "n_hyderabad_users": len(hyd),
        "n_texts_latest": len(latest),
        "n_duplicates_removed": len(latest) - len(dedup),
        **{f"g12_{k}": int(s.sum()) for k, s in hits.items()},
        "g12_excluded_total": int(flagged.sum()),
    }
    frame = dedup[~flagged].reset_index(drop=True)
    counts["n_frame"] = len(frame)
    return frame, counts


def draw(frame: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, dict[str, int]]:
    """45 uniform random first, then enriched by lexicon quotas; shortfalls filled at random."""
    rng = np.random.default_rng(seed)
    f = frame.sort_values("user_key").reset_index(drop=True)
    taken = set(rng.choice(len(f), size=N_RANDOM, replace=False).tolist())
    parts = [f.loc[sorted(taken)].assign(stratum="random", is_fill=False)]
    short = {}
    for sig in SIGNALS:
        pool = [
            i
            for i in range(len(f))
            if i not in taken and any(s in f.at[i, "text"].casefold() for s in LEXICONS[sig])
        ]
        k = min(QUOTAS[sig], len(pool))
        chosen = sorted(rng.choice(pool, size=k, replace=False).tolist()) if k else []
        taken.update(chosen)
        short[sig] = QUOTAS[sig] - k
        parts.append(f.loc[chosen].assign(stratum=f"enriched_{sig}", is_fill=False))
    for sig in SIGNALS:
        if short[sig]:
            pool = [i for i in range(len(f)) if i not in taken]
            chosen = sorted(rng.choice(pool, size=short[sig], replace=False).tolist())
            taken.update(chosen)
            parts.append(f.loc[chosen].assign(stratum=f"enriched_{sig}", is_fill=True))
    return pd.concat(parts, ignore_index=True), short


def assign(sample: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """3 sets of 25 by global round-robin over strata; set 1=A+B, 2=A+C, 3=B+C."""
    rng = np.random.default_rng([seed, 1])
    pieces, counter = [], 0
    for stratum in STRATA:
        part = sample[sample["stratum"] == stratum]
        part = part.iloc[rng.permutation(len(part))].copy()
        part["set_id"] = [(counter + i) % 3 + 1 for i in range(len(part))]
        counter += len(part)
        pieces.append(part)
    m = pd.concat(pieces, ignore_index=True)
    m = m.iloc[rng.permutation(len(m))].reset_index(drop=True)
    m.insert(0, "item_id", [f"g{i + 1:03d}" for i in range(len(m))])
    m["annotators"] = m["set_id"].map(SET_ANNOTATORS)
    orders = {}
    for k, a in enumerate(ANNOTATORS):
        own = m.loc[m["annotators"].str.contains(a), "item_id"].tolist()
        orders[a] = [own[i] for i in np.random.default_rng([seed, 2, k]).permutation(len(own))]
    return m, orders


def write_files(m: pd.DataFrame, orders: dict[str, list[str]], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cols = ["item_id", "user_key", "text", "stratum", "set_id", "annotators", "is_fill"]
    m[cols].to_parquet(out / "gold_master.parquet", index=False)
    text = dict(zip(m["item_id"], m["text"], strict=True))
    for a in ANNOTATORS:
        with open(out / f"annotator_{a}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["item_id", "text", *SIGNALS, "uwagi"])
            for i in orders[a]:
                w.writerow([i, text[i], "", "", "", "", ""])
        tasks = [{"data": {"item_id": i, "text": text[i]}} for i in orders[a]]
        (out / f"annotator_{a}.labelstudio.json").write_text(
            json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8"
        )


def log(values: dict) -> None:
    for k, v in values.items():
        assert isinstance(v, int | str) and (isinstance(v, int) or k.endswith("_sha256")), k
        print(f"{k}={v}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--users", default="data/processed/users.parquet")
    ap.add_argument("--history", default="data/processed/profile_history.parquet")
    ap.add_argument("--out-dir", default="data/private/gold")
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    try:
        users = pd.read_parquet(a.users, columns=["user_key", "city", "bio"])
        hist = pd.read_parquet(a.history, columns=["user_key", "version", "day", "city", "bio"])
        frame, counts = build_frame(users, hist)
        log(counts)
        if len(frame) < N_TOTAL:
            log({"n_required": N_TOTAL, "stopped": 1})
            return 2
        sample, short = draw(frame, a.seed)
        m, orders = assign(sample, a.seed)
        write_files(m, orders, Path(a.out_dir))
        stats = {"seed": a.seed, "n_sample": len(m)}
        stats |= {f"n_{k}": int(n) for k, n in m["stratum"].value_counts().sort_index().items()}
        stats |= {"n_fill": int(m["is_fill"].sum())}
        stats |= {f"shortage_{s}": n for s, n in short.items()}
        stats |= {f"n_set{k}": int(n) for k, n in m["set_id"].value_counts().sort_index().items()}
        stats |= {f"n_annotator_{k}": len(v) for k, v in orders.items()}
        pairs = [f"{u}|{s}" for u, s in zip(m["user_key"], m["stratum"], strict=True)]
        stats["selection_sha256"] = digest(pairs)
        lex = json.dumps(
            {k: list(v) for k, v in LEXICONS.items()}, ensure_ascii=False, sort_keys=True
        )
        stats["lexicon_sha256"] = hashlib.sha256(lex.encode("utf-8")).hexdigest()
        log(stats)
    except Exception as e:  # noqa: BLE001 - type only: messages may carry values
        print(f"error_type={type(e).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
