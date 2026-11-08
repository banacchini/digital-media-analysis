"""Embed user bios locally and save unit-length vectors keyed by `user_key`.

Bios may contain personal data, so the model runs on this machine (no external API) and only the
vectors plus the bio length are written. Bio text is never printed or saved. Output goes to
`data/interim/` (gitignored):

- `bio_embeddings.npy`  float32, shape (n_users_with_bio, dim), rows L2-normalised
- `bio_embeddings_keys.parquet`  columns `user_key`, `bio_len` (characters counted from the text)

Run (needs the `embed` dependency group):

    uv sync --group embed
    uv run python -m rentfriends.embed_bios --users data/raw/users.csv

Empty or whitespace-only bios get no vector (46.6% of profiles, see `docs/codebook.md`).
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

# Multilingual (the sample is mostly Polish) and small enough for a laptop GPU/CPU.
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MAX_CHARS = 2000  # bios are short; guard against pathological rows

Embedder = Callable[[Sequence[str]], np.ndarray]


def clean_bios(users: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per user with a non-empty bio: columns `user_key`, `bio`, `bio_len`."""
    d = users[["user_key", "bio"]].drop_duplicates("user_key").copy()
    d["bio"] = d["bio"].fillna("").astype(str).str.strip()
    d = d[d["bio"] != ""].reset_index(drop=True)
    d["bio_len"] = d["bio"].str.len().astype("int64")
    d["bio"] = d["bio"].str.slice(0, MAX_CHARS)
    return d


def l2_normalise(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=1, keepdims=True)
    return (x / np.where(norm == 0, 1.0, norm)).astype(np.float32)


def sentence_transformer_embedder(
    model_name: str = DEFAULT_MODEL, batch_size: int = 64
) -> Embedder:
    """Return a function texts -> (n, dim) array using a local sentence-transformers model."""
    from sentence_transformers import SentenceTransformer  # heavy, imported lazily

    model = SentenceTransformer(model_name)

    def embed(texts: Sequence[str]) -> np.ndarray:
        return model.encode(
            list(texts), batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True
        )

    return embed


def embed_users(users: pd.DataFrame, embedder: Embedder) -> tuple[np.ndarray, pd.DataFrame]:
    """Embed the bios of `users`; returns (unit vectors, keys frame with `bio_len`)."""
    d = clean_bios(users)
    vecs = l2_normalise(np.asarray(embedder(d["bio"].tolist())))
    if len(vecs) != len(d):
        raise ValueError("embedder returned a different number of vectors than bios")
    return vecs, d[["user_key", "bio_len"]]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--users", type=Path, default=Path("data/raw/users.csv"))
    p.add_argument("--out", type=Path, default=Path("data/interim"))
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--batch-size", type=int, default=64)
    args = p.parse_args(argv)

    users = pd.read_csv(args.users, usecols=["user_key", "bio"], dtype="string")
    vecs, keys = embed_users(users, sentence_transformer_embedder(args.model, args.batch_size))
    args.out.mkdir(parents=True, exist_ok=True)
    np.save(args.out / "bio_embeddings.npy", vecs)
    keys.to_parquet(args.out / "bio_embeddings_keys.parquet", index=False)
    print(f"ok: {vecs.shape[0]} bios embedded, dim {vecs.shape[1]}, model {args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
