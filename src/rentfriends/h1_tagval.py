"""Impact of the tag validation decisions on H1 (agent task Z5).

Builds variants of the H1 dataset with a different raw -> canonical mapping, tag categories,
tag merges and D13/D15 settings, WITHOUT touching `h1.py`, `dataset_h1.py` or the data
contract. The variant builder calls `dataset_h1.build_h1_dataset` itself, swapping the four
decision inputs (mapping/categories, D13 imputation, D15 polarity pairs) for the duration of
the call, so the baseline is the very same code path as the contract file.

Only tags and aggregates are handled here; bios and user keys are never output.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pandas as pd

from rentfriends import dataset_h1 as d1
from rentfriends.dataset_h1 import parse_raw_interests

PLACEHOLDER_LIFESTYLE_CODE = "OUT"  # codebook gives no meaning for lifestyle codes S/M/W
PolarityPairs = list[tuple[set[str], set[str]]]
D13Map = dict[str, tuple[str, str]]


# --- decision inputs ----------------------------------------------------------------------
def load_merge_map(path: str | Path) -> dict[str, str]:
    """`canonical_before -> canonical_after`; chains and self-merges are errors."""
    df = pd.read_csv(path, dtype=str)
    df["canonical_before"] = df["canonical_before"].str.strip()
    df["canonical_after"] = df["canonical_after"].str.strip()
    merge = dict(zip(df["canonical_before"], df["canonical_after"], strict=True))
    if len(merge) != len(df):
        raise ValueError("duplicate canonical_before in merge map")
    bad = [t for t in merge.values() if t in merge]
    if bad or any(b == a for b, a in merge.items()):
        raise ValueError(f"merge map has chains or self-merges: {sorted(set(bad))}")
    return merge


def load_consensus_a(path: str | Path, baseline: Mapping[str, str]) -> dict[str, str]:
    """Raw -> canonical overrides: rows where the consensus differs from the agent mapping.

    A consensus of `brak` is not an override (the baseline treatment of the raw string stays).
    """
    df = pd.read_csv(path, dtype=str)
    out: dict[str, str] = {}
    for raw, final in zip(df["raw_tag"], df["konsensus"], strict=True):
        if final != "brak" and baseline.get(raw, raw) != final:
            out[raw] = final
    return out


def load_consensus_b(path: str | Path) -> dict[str, str]:
    """Canonical tag -> category (`konsensus` column)."""
    df = pd.read_csv(path, dtype=str)
    return dict(zip(df["canonical_tag"], df["konsensus"], strict=True))


def effective_mapping(
    base: Mapping[str, str],
    raw_universe: set[str],
    raw_override: Mapping[str, str] | None,
    merge: Mapping[str, str] | None,
) -> dict[str, str]:
    """raw -> canonical: base mapping, then consensus override, then merge (in that order).

    Raw strings without an entry keep the H1 behaviour (they pass through as their own tag),
    but are listed explicitly so that a merge also applies to a pass-through tag.
    """
    out: dict[str, str] = {}
    for raw in set(base) | raw_universe | set(raw_override or {}):
        canon = (raw_override or {}).get(raw, base.get(raw, raw))
        out[raw] = (merge or {}).get(canon, canon)
    return out


# --- D13 re-pointing and D15 remapping -------------------------------------------------------
def rekey_d13_map(d13: D13Map, merge: Mapping[str, str]) -> tuple[D13Map, list[dict]]:
    """Point D13 keys at the merge target; a clash of different codes on one target is an error."""
    new: D13Map = {}
    report: list[dict] = []
    for tag, (field, code) in d13.items():
        target = merge.get(tag, tag)
        if target != tag:
            report.append({"tag": tag, "target": target, "field": field, "code": code})
        if target in new and new[target] != (field, code):
            raise ValueError(f"D13 clash on {target}: {new[target]} vs {(field, code)}")
        new.setdefault(target, (field, code))
    return new, report


def remap_polarity_pairs(
    pairs: PolarityPairs, merge: Mapping[str, str]
) -> tuple[PolarityPairs, list[dict]]:
    """Apply the merge to the D15 polarity groups and report every touched group.

    Reported per pair side: removed tags that are in the group (and whether their target was
    already there), and merge sources outside the group whose target is inside (the group then
    covers more holders; this CHANGES the conflicts). A target on both sides is an error.
    """
    new_pairs: PolarityPairs = []
    report: list[dict] = []
    for i, (pos, neg) in enumerate(pairs):
        sides = []
        for label, side in (("pos", pos), ("neg", neg)):
            renamed = {merge.get(t, t) for t in side}
            for src, target in merge.items():
                if src in side:
                    report.append(
                        {
                            "pair": i,
                            "side": label,
                            "kind": "removed_tag_in_group",
                            "tag": src,
                            "target": target,
                            "target_already_in_group": target in side,
                        }
                    )
                elif target in side:
                    report.append(
                        {
                            "pair": i,
                            "side": label,
                            "kind": "source_outside_group_target_inside",
                            "tag": src,
                            "target": target,
                            "target_already_in_group": True,
                        }
                    )
            sides.append(renamed)
        clash = sides[0] & sides[1]
        if clash:
            raise ValueError(f"polarity pair {i}: {sorted(clash)} ends up on both sides")
        new_pairs.append((sides[0], sides[1]))
    return new_pairs, report


def make_d13_imputation(d13: D13Map | None):
    """Drop-in for `apply_d13_tag_imputation`; `None` disables the imputation."""

    def apply(df: pd.DataFrame, lifestyle_tags_col: str = "lifestyle_tags") -> pd.DataFrame:
        res = df.copy()
        for tag, (field, code) in (d13 or {}).items():
            if field in res.columns:
                has_tag = res[lifestyle_tags_col].apply(lambda tags, t=tag: t in tags)
                res.loc[res[field].isna() & has_tag, field] = code
        return res

    return apply


def make_conflict_fn(pairs: PolarityPairs):
    """Drop-in for `compute_lifestyle_tag_conflict` with explicit polarity pairs."""

    def conflict(tags_a: list[str], tags_b: list[str]) -> int:
        a, b = d1.as_tag_set(tags_a), d1.as_tag_set(tags_b)
        return int(any((a & p and b & n) or (a & n and b & p) for p, n in pairs))

    return conflict


# --- variant builder ----------------------------------------------------------------------
@contextlib.contextmanager
def _patched(mapping, categories, linked, d13_fn, conflict_fn) -> Iterator[None]:
    with (
        mock.patch.object(d1, "load_tag_mappings", lambda *_a, **_k: (mapping, categories, linked)),
        mock.patch.object(d1, "apply_d13_tag_imputation", d13_fn),
        mock.patch.object(d1, "compute_lifestyle_tag_conflict", conflict_fn),
    ):
        yield


def build_h1_variant(
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
    *,
    raw_to_canonical_override: Mapping[str, str] | None = None,
    category_override: Mapping[str, str] | None = None,
    tag_merge: Mapping[str, str] | None = None,
    d13_map: D13Map | None = None,
    polarity_pairs: PolarityPairs | None = None,
) -> pd.DataFrame:
    """H1 dataset under alternative tag decisions (defaults reproduce the contract dataset).

    `d13_map=None` -> the project D13 map; pass `{}` to switch the imputation off.
    """
    docs = Path(docs_dir)
    base_map, categories, linked = d1.load_tag_mappings(
        docs / "interests_mapping.csv", docs / "tag_category_proposal.csv"
    )
    universe: set[str] = set()
    for name in ("users", "profile_history"):
        interests = pd.read_parquet(Path(data_dir) / f"{name}.parquet", columns=["interests"])
        for raw in interests["interests"]:
            universe.update(parse_raw_interests(raw))
    mapping = effective_mapping(base_map, universe, raw_to_canonical_override, tag_merge)
    categories = {**categories, **(category_override or {})}
    d13 = d1.TAG_TO_STRUCTURED_FIELD_MAP if d13_map is None else d13_map
    pairs = d1.POLARITY_PAIRS if polarity_pairs is None else polarity_pairs
    with _patched(mapping, categories, linked, make_d13_imputation(d13), make_conflict_fn(pairs)):
        return d1.build_h1_dataset(data_dir=data_dir, docs_dir=docs_dir)


# --- scenarios ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    use_a: bool = False
    use_b: bool = False
    merge: bool = False
    d13: str = "agent"  # agent | off | placeholder_fill
    diagnostic: bool = False


SCENARIOS = (
    Scenario("i", "(i) mapowanie agenta (baseline)"),
    Scenario("ii", "(ii) konsensus A+B", use_a=True, use_b=True),
    Scenario("iii", "(iii) konsensus tylko A", use_a=True),
    Scenario("iv", "(iv) konsensus tylko B", use_b=True),
    Scenario("v", "(v) agent, D13 wyłączone", d13="off"),
    Scenario("vi", "(vi) konsensus A+B + scalenia", use_a=True, use_b=True, merge=True),
    # Diagnostics for the going_out_friends -> often_out D13 question. The `lifestyle` field has
    # no documented code, so a PLACEHOLDER code fills it from often_out (+ often_outside before
    # the merge). Compare vi_fill vs vi to get the fill effect after the merge and ii_fill vs ii
    # for the fill effect without it; the difference is what the merge enables.
    Scenario(
        "ii_fill",
        "(diag) konsensus A+B, kod zastępczy `lifestyle` z often_out",
        use_a=True,
        use_b=True,
        d13="placeholder_fill",
        diagnostic=True,
    ),
    Scenario(
        "vi_fill",
        "(diag) (vi) + kod zastępczy `lifestyle` z often_out",
        use_a=True,
        use_b=True,
        merge=True,
        d13="placeholder_fill",
        diagnostic=True,
    ),
)


def scenario_inputs(
    sc: Scenario,
    *,
    consensus_a: Mapping[str, str],
    consensus_b: Mapping[str, str],
    merge: Mapping[str, str],
) -> tuple[dict, dict]:
    """Keyword arguments for `build_h1_variant` and the audit trail of the D13/D15 re-pointing."""
    d13: D13Map = dict(d1.TAG_TO_STRUCTURED_FIELD_MAP)
    if sc.d13 == "placeholder_fill":
        fill_tags = ["often_out"] if sc.merge else ["often_out", "often_outside"]
        d13.update({t: ("lifestyle", PLACEHOLDER_LIFESTYLE_CODE) for t in fill_tags})
    if sc.d13 == "off":
        d13 = {}
    pairs: PolarityPairs = [(set(p), set(n)) for p, n in d1.POLARITY_PAIRS]
    audit: dict = {}
    if sc.merge:
        d13, audit["d13_rekey"] = rekey_d13_map(d13, merge)
        pairs, audit["polarity_remap"] = remap_polarity_pairs(pairs, merge)
    kwargs = {
        "raw_to_canonical_override": consensus_a if sc.use_a else None,
        "category_override": consensus_b if sc.use_b else None,
        "tag_merge": merge if sc.merge else None,
        "d13_map": d13,
        "polarity_pairs": pairs,
    }
    return kwargs, audit


# --- metrics ------------------------------------------------------------------------------
BLOCKS = ("age", "interests", "lifestyle")
LSF_COLS = [f"lsf_{f}" for f in d1.LIFESTYLE_STRUCTURED_FIELDS] + ["smoking_direction"]


def with_city_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """The two columns `h1.load_h1_data` adds before fitting."""
    out = df.copy()
    out["city_same"] = (out["same_city"] == "same").astype(float)
    out["city_diff"] = (out["same_city"] == "different").astype(float)
    return out


def _sets_differ(a: pd.Series, b: pd.Series) -> pd.Series:
    return pd.Series([x != y for x, y in zip(a, b, strict=True)], index=a.index)


def changed_shares(base: pd.DataFrame, other: pd.DataFrame, mask: pd.Series) -> dict[str, float]:
    """Share of swipes (rows in `mask`) whose tag-derived features differ from `base`."""
    keys = ["user_key", "target_user_key", "day"]
    if not base[keys].equals(other[keys]):
        raise ValueError("variant datasets are not row-aligned with the baseline")
    interests = _sets_differ(base["interests_set_sender"], other["interests_set_sender"]) | (
        _sets_differ(base["interests_set_receiver"], other["interests_set_receiver"])
    )
    fields = pd.concat([base[c].ne(other[c]) for c in LSF_COLS], axis=1).any(axis=1)
    tags = base["lifestyle_shared_tags_n"].ne(other["lifestyle_shared_tags_n"]) | base[
        "lifestyle_tag_conflict"
    ].ne(other["lifestyle_tag_conflict"])
    out = {
        "interests_set": interests,
        "lifestyle_field": fields,
        "interests_or_field": interests | fields,
        "lifestyle_tags": tags,
        "lifestyle_tag_conflict": base["lifestyle_tag_conflict"].ne(
            other["lifestyle_tag_conflict"]
        ),
        "lifestyle_shared_tags_n": base["lifestyle_shared_tags_n"].ne(
            other["lifestyle_shared_tags_n"]
        ),
        "conflict_gained": base["lifestyle_tag_conflict"].lt(other["lifestyle_tag_conflict"]),
        "conflict_lost": base["lifestyle_tag_conflict"].gt(other["lifestyle_tag_conflict"]),
        "lsf_lifestyle": base["lsf_lifestyle"].ne(other["lsf_lifestyle"]),
        "lsf_noise_level": base["lsf_noise_level"].ne(other["lsf_noise_level"]),
    }
    return {k: float(v[mask].mean()) for k, v in out.items()}


def fit_metrics(df: pd.DataFrame) -> dict:
    """Pooled logit with the main H1 specification: block increments over the 6 orderings."""
    from rentfriends import h1, h1_audit

    data = with_city_dummies(df)
    res = h1.fit_h1_logit_models(data)
    inc = h1_audit.block_increments_from_fit(res).set_index("block")
    mean = {b: float(inc.loc[b, "dll_mean"]) for b in BLOCKS}
    sample = h1.prepare_h1_sample(data)
    total = sum(mean.values())
    return {
        "n_sample": int(res["data_len"]),
        "dll_mean": mean,
        "dll_first": {b: float(inc.loc[b, "dll_first"]) for b in BLOCKS},
        "dll_last": {b: float(inc.loc[b, "dll_last"]) for b in BLOCKS},
        "ranking": sorted(BLOCKS, key=lambda b: -mean[b]),
        "age_share_of_total": mean["age"] / total,
        "lifestyle_share_of_total": mean["lifestyle"] / total,
        "interests_share_of_total": mean["interests"] / total,
        "lifestyle_to_interests_ratio": mean["lifestyle"] / mean["interests"],
        "jaccard_right": float(sample.loc[sample["y_right"] == 1, "interests_jaccard"].mean()),
        "jaccard_left": float(sample.loc[sample["y_right"] == 0, "interests_jaccard"].mean()),
    }


def _flat(m: dict) -> dict[str, float]:
    out = {f"dll_mean_{b}": m["dll_mean"][b] for b in BLOCKS}
    out.update(
        n_sample=m["n_sample"],
        age_share_of_total=m["age_share_of_total"],
        lifestyle_share_of_total=m["lifestyle_share_of_total"],
        interests_share_of_total=m["interests_share_of_total"],
        lifestyle_to_interests_ratio=m["lifestyle_to_interests_ratio"],
        jaccard_right=m["jaccard_right"],
        jaccard_left=m["jaccard_left"],
    )
    return out


def metric_delta(m: dict, ref: dict) -> dict[str, float]:
    a, b = _flat(m), _flat(ref)
    return {k: a[k] - b[k] for k in a}


# --- driver -------------------------------------------------------------------------------
def run_impact(
    data_dir: str | Path = "data/processed",
    docs_dir: str | Path = "docs",
    tagval_dir: str | Path = "data/tagval",
    merge_map: str | Path = "docs/tag-validation/tag_merge_map.csv",
    out_json: str | Path = "reports/tag-validation/impact.json",
) -> dict:
    """Run scenarios (i)-(vi) plus the two D13 diagnostics and write impact.json."""
    import json

    from rentfriends import h1
    from rentfriends.tagval_prep import PROPOSAL_SHA256, sha256_file

    data_path, docs_path, tv = Path(data_dir), Path(docs_dir), Path(tagval_dir)
    frozen = {
        "proposal": docs_path / "tag_category_proposal.csv",
        "mapping": docs_path / "interests_mapping.csv",
        "contract": data_path / "h1_analysis_dataset.parquet",
    }
    before = {k: sha256_file(p) for k, p in frozen.items()}
    if before["proposal"] != PROPOSAL_SHA256:
        raise RuntimeError("frozen proposal hash mismatch")

    base_map, _, _ = d1.load_tag_mappings(
        docs_path / "interests_mapping.csv", docs_path / "tag_category_proposal.csv"
    )
    consensus_a = load_consensus_a(tv / "consensus_A.csv", base_map)
    consensus_b = load_consensus_b(tv / "consensus_B.csv")
    merge = load_merge_map(merge_map)
    proposal = pd.read_csv(docs_path / "tag_category_proposal.csv")
    agent_cat = dict(
        zip(proposal["canonical_tag"], proposal["proposed_category_claude"], strict=True)
    )

    datasets: dict[str, pd.DataFrame] = {}
    audits: dict[str, dict] = {}
    for sc in SCENARIOS:
        kwargs, audits[sc.key] = scenario_inputs(
            sc, consensus_a=consensus_a, consensus_b=consensus_b, merge=merge
        )
        datasets[sc.key] = build_h1_variant(data_path, docs_path, **kwargs)

    # Separate output files; the contract file is never written.
    datasets["ii"].to_parquet(data_path / "h1_analysis_dataset_consensus.parquet", index=False)
    datasets["vi"].to_parquet(
        data_path / "h1_analysis_dataset_consensus_merged.parquet", index=False
    )

    base = datasets["i"]
    required = h1._spec_required_cols(h1.H1Spec())
    mask = with_city_dummies(base)[required].notna().all(axis=1)
    metrics = {k: fit_metrics(df) for k, df in datasets.items()}

    scen_out = {}
    for sc in SCENARIOS:
        m = metrics[sc.key]
        scen_out[sc.key] = {
            "label": sc.label,
            "diagnostic": sc.diagnostic,
            **m,
            "same_ranking_as_baseline": m["ranking"] == metrics["i"]["ranking"],
            "share_changed_vs_baseline": changed_shares(base, datasets[sc.key], mask),
            "delta_vs_baseline": metric_delta(m, metrics["i"]),
        }

    def shares(a: str, b: str) -> dict[str, float]:
        return changed_shares(datasets[a], datasets[b], mask)

    d_dict = metric_delta(metrics["vi"], metrics["ii"])
    fill_pre = metric_delta(metrics["ii_fill"], metrics["ii"])
    fill_post = metric_delta(metrics["vi_fill"], metrics["vi"])
    going_out = {
        "note": "placeholder code for the `lifestyle` field; the codebook defines none",
        "dictionary_effect_vi_minus_ii": d_dict,
        "d13_real_map_lsf_lifestyle_changed_share_ii_vs_vi": shares("ii", "vi")["lsf_lifestyle"],
        "fill_effect_without_merge_ii_fill_minus_ii": fill_pre,
        "fill_effect_with_merge_vi_fill_minus_vi": fill_post,
        "fill_effect_enabled_by_merge": {k: fill_post[k] - fill_pre[k] for k in fill_post},
        "lsf_lifestyle_changed_share_ii_fill_vs_ii": shares("ii_fill", "ii")["lsf_lifestyle"],
        "lsf_lifestyle_changed_share_vi_fill_vs_vi": shares("vi_fill", "vi")["lsf_lifestyle"],
        "lsf_lifestyle_changed_share_vi_fill_vs_ii_fill": shares("vi_fill", "ii_fill")[
            "lsf_lifestyle"
        ],
    }
    a_ii, b_vi = datasets["ii"][mask], datasets["vi"][mask]
    c_a, c_b = a_ii["lifestyle_tag_conflict"], b_vi["lifestyle_tag_conflict"]
    n_a, n_b = a_ii["lifestyle_shared_tags_n"], b_vi["lifestyle_shared_tags_n"]
    polarity_effect = {
        "note": "ii -> vi on the H1 sample: D15 conflict and shared lifestyle tag count",
        "n_swipes": int(mask.sum()),
        "conflict_gained_n": int((c_a < c_b).sum()),
        "conflict_lost_n": int((c_a > c_b).sum()),
        "conflict_rate_ii": float(c_a.mean()),
        "conflict_rate_vi": float(c_b.mean()),
        "shared_tags_up_n": int((n_a < n_b).sum()),
        "shared_tags_down_n": int((n_a > n_b).sum()),
        "shared_tags_mean_ii": float(n_a.mean()),
        "shared_tags_mean_vi": float(n_b.mean()),
    }
    after = {k: sha256_file(p) for k, p in frozen.items()}
    out = {
        "frozen_files_unchanged": before == after,
        "baseline_n_rows": len(base),
        "decisions": {
            "n_raw_overrides_consensus_a": len(consensus_a),
            "n_category_changes_vs_agent_claude": sum(
                consensus_b[t] != agent_cat[t] for t in agent_cat
            ),
            "categories_agent_vs_consensus_of_merged_tags": {
                t: [agent_cat.get(t), consensus_b.get(t)]
                for t in sorted(set(merge) | set(merge.values()))
            },
            "merge": merge,
        },
        "audit_vi": audits["vi"],
        "polarity_effect_ii_to_vi": polarity_effect,
        "scenarios": scen_out,
        "going_out_friends_to_often_out": going_out,
    }
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(out_json).with_suffix(".md").write_text(render_impact_md(out), encoding="utf-8")
    return out


# --- report -------------------------------------------------------------------------------
PL = {"age": "wiek", "lifestyle": "styl życia", "interests": "zainteresowania"}


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


def _num(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def render_impact_md(res: dict) -> str:
    """Markdown report; every number is read from `res` (the content of impact.json)."""
    sc = res["scenarios"]
    main = [k for k, v in sc.items() if not v["diagnostic"]]
    base = sc["i"]
    lines = [
        "# Walidacja tagów: wpływ decyzji na H1 (Z5)",
        "",
        "Liczby pochodzą z `impact.json`. Specyfikacja jak w głównej analizie H1 (pooled logit, "
        "te same kontrole); ΔLL bloku = średnia po 6 kolejnościach wejścia bloków. "
        f"Referencja: jeden recenzent, runda 1 (patrz `docs/tag-validation/decisions.md`). "
        f"Kontrakt danych, mapowanie i propozycja bez zmian: "
        f"{'tak' if res['frozen_files_unchanged'] else 'NIE'}.",
        "",
        "## Pytanie: czy wniosek H1 zmienia się przy mapowaniu konsensusu?",
        "",
    ]
    same = all(sc[k]["same_ranking_as_baseline"] for k in main)
    rank = " > ".join(PL[b] for b in base["ranking"])
    ages = [sc[k]["age_share_of_total"] for k in main]
    lines.append(
        f"**Kolejność bloków {'nie zmienia się' if same else 'ZMIENIA SIĘ'}** w scenariuszach "
        f"(i)–(vi): w baseline {rank} (ΔLL {_num(base['dll_mean']['age'], 1)} / "
        f"{_num(base['dll_mean']['lifestyle'], 1)} / {_num(base['dll_mean']['interests'], 1)}). "
        f"Udział wieku w sumie ΔLL wynosi {_pct(min(ages))}–{_pct(max(ages))} (baseline "
        f"{_pct(base['age_share_of_total'])})."
    )
    r = [sc[k]["lifestyle_to_interests_ratio"] for k in main]
    lines += [
        "",
        f"Zmienia się **odstęp między stylem życia a zainteresowaniami**: stosunek ΔLL stylu życia "
        f"do zainteresowań spada z {_num(base['lifestyle_to_interests_ratio'])} (baseline) do "
        f"{_num(sc['ii']['lifestyle_to_interests_ratio'])} w (ii) i "
        f"{_num(sc['vi']['lifestyle_to_interests_ratio'])} w (vi) (zakres w (i)–(vi): "
        f"{_num(min(r))}–{_num(max(r))}). ΔLL zainteresowań rośnie z "
        f"{_num(base['dll_mean']['interests'])} do {_num(sc['ii']['dll_mean']['interests'])} "
        f"w (ii), a stylu życia spada z {_num(base['dll_mean']['lifestyle'])} do "
        f"{_num(sc['ii']['dll_mean']['lifestyle'])} w (ii) i "
        f"{_num(sc['vi']['dll_mean']['lifestyle'])} w (vi).",
        "",
        "## Scenariusze",
        "",
        "| Scenariusz | n próby | swipe'y ze zmianą zainteresowań "
        "| swipe'y ze zmianą pola stylu życia | ΔLL wiek | ΔLL zainteresowania "
        "| ΔLL styl życia | Jaccard zainteresowań, prawe | Jaccard zainteresowań, lewe "
        "| kolejność |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for v in sc.values():
        ch = v["share_changed_vs_baseline"]
        lines.append(
            f"| {v['label']} | {v['n_sample']} | {_pct(ch['interests_set'])} | "
            f"{_pct(ch['lifestyle_field'])} | {_num(v['dll_mean']['age'])} | "
            f"{_num(v['dll_mean']['interests'])} | {_num(v['dll_mean']['lifestyle'])} | "
            f"{_num(v['jaccard_right'], 4)} | {_num(v['jaccard_left'], 4)} | "
            f"{' > '.join(PL[b] for b in v['ranking'])} |"
        )
    lines += [
        "",
        "Zmiana liczona względem baseline na swipe'ach próby H1 (n = "
        f"{base['n_sample']}); pole stylu życia: statusy zgodności siedmiu pól i kierunek palenia. "
        "Zmiana wartości pola bez zmiany statusu zgodności nie jest widoczna.",
        "",
        "Zmiany względem baseline (Δ):",
        "",
        "| Scenariusz | Δ ΔLL wiek | Δ ΔLL zainteresowania | Δ ΔLL styl życia "
        "| Δ Jaccard prawe | Δ Jaccard lewe |",
        "|---|---|---|---|---|---|",
    ]
    for k, v in sc.items():
        if k == "i":
            continue
        d = v["delta_vs_baseline"]
        lines.append(
            f"| {v['label']} | {_num(d['dll_mean_age'])} | {_num(d['dll_mean_interests'])} | "
            f"{_num(d['dll_mean_lifestyle'])} | {_num(d['jaccard_right'], 4)} | "
            f"{_num(d['jaccard_left'], 4)} |"
        )
    v5 = sc["v"]
    lines += [
        "",
        f"W (v) próba kurczy się do {v5['n_sample']} swipe'ów "
        f"(−{base['n_sample'] - v5['n_sample']}), bo bez uzupełniania pól tagami "
        f"{_pct(v5['share_changed_vs_baseline']['lifestyle_field'])} "
        "swipe'ów zmienia status zgodności któregoś pola.",
        "",
        "## Scalenia (vi): D13 i D15",
        "",
    ]
    rk = res["audit_vi"]["d13_rekey"]
    lines.append(
        f"Klucze D13 przepięte na tag docelowy: {len(rk)} ("
        + ", ".join(f"{x['tag']} → {x['target']} ({x['field']}={x['code']})" for x in rk)
        + "). Kody tych kluczy są identyczne, więc przepięcie nie zmienia uzupełniania."
    )
    pr = res["audit_vi"]["polarity_remap"]
    lines += ["", f"Pary polaryzacji (D15) dotknięte scaleniami: {len(pr)} wpisów."]
    for x in pr:
        what = (
            "usuwany tag jest w grupie"
            if x["kind"] == "removed_tag_in_group"
            else "tag spoza grupy trafia do niej przez cel scalenia"
        )
        lines.append(
            f"- grupa {x['pair']}, strona {x['side']}: `{x['tag']}` → `{x['target']}` ({what}; "
            f"cel już w grupie: {'tak' if x['target_already_in_group'] else 'nie'})."
        )
    pe = res["polarity_effect_ii_to_vi"]
    lines += [
        "",
        f"Skutek (ii → vi) na próbie H1 (n = {pe['n_swipes']}): konflikt D15 przybywa w "
        f"{pe['conflict_gained_n']} swipe'ach i ubywa w {pe['conflict_lost_n']} (odsetek "
        f"konfliktów {_pct(pe['conflict_rate_ii'])} → {_pct(pe['conflict_rate_vi'])}). "
        f"Liczba wspólnych tagów stylu życia rośnie w {pe['shared_tags_up_n']} swipe'ach i maleje "
        f"w {pe['shared_tags_down_n']} (średnia {_num(pe['shared_tags_mean_ii'], 3)} → "
        f"{_num(pe['shared_tags_mean_vi'], 3)}).",
        "",
        "## going_out_friends → often_out: efekt słownika vs efekt uzupełniania pól",
        "",
    ]
    g = res["going_out_friends_to_often_out"]
    de, fp, fq, fe = (
        g["dictionary_effect_vi_minus_ii"],
        g["fill_effect_without_merge_ii_fill_minus_ii"],
        g["fill_effect_with_merge_vi_fill_minus_vi"],
        g["fill_effect_enabled_by_merge"],
    )
    lines += [
        "- **Przy obecnej mapie D13 efekt uzupełniania wynosi 0:** "
        f"`TAG_TO_STRUCTURED_FIELD_MAP` nie "
        f"zawiera `often_out` ani `going_out_friends`, a kody pola `lifestyle` (S/M/W) nie mają "
        f"znaczenia w codebooku. Status zgodności pola `lifestyle` zmienia się w "
        f"{_pct(g['d13_real_map_lsf_lifestyle_changed_share_ii_vs_vi'])} swipe'ów "
        "między (ii) a (vi). "
        "Pole „brak → lifestyle” w propozycji (`proposed_linked_field`) nie jest używane w budowie "
        "zbioru H1.",
        f"- **Efekt słownika (vi − ii):** ΔLL wiek {_num(de['dll_mean_age'])}, zainteresowania "
        f"{_num(de['dll_mean_interests'])}, styl życia {_num(de['dll_mean_lifestyle'])}.",
        "- **Diagnostyka z kodem zastępczym** (`"
        + PLACEHOLDER_LIFESTYLE_CODE
        + "` uzupełnia `lifestyle` "
        "z `often_out`, przed scaleniem także z `often_outside`; to założenie, nie dane): "
        "status pola `lifestyle` zmienia się w "
        f"{_pct(g['lsf_lifestyle_changed_share_ii_fill_vs_ii'])} swipe'ów bez scalenia, w "
        f"{_pct(g['lsf_lifestyle_changed_share_vi_fill_vs_vi'])} ze scaleniem; "
        f"{_pct(g['lsf_lifestyle_changed_share_vi_fill_vs_ii_fill'])} swipe'ów zmienia status "
        "wyłącznie przez to, że `going_out_friends` zaczyna uzupełniać pole.",
        f"- Efekt uzupełniania na ΔLL stylu życia: {_num(fp['dll_mean_lifestyle'])} bez scalenia, "
        f"{_num(fq['dll_mean_lifestyle'])} ze scaleniem; różnicę wynikającą ze scalenia daje "
        f"{_num(fe['dll_mean_lifestyle'])} (wiek {_num(fe['dll_mean_age'])}, zainteresowania "
        f"{_num(fe['dll_mean_interests'])}).",
        "",
        "## Zastrzeżenia",
        "",
        "- Referencja to jeden recenzent bez testu powtórnego; zmiany kategorii B przesunęły część "
        f"tagów ({res['decisions']['n_category_changes_vs_agent_claude']} różnic względem Claude) "
        f"i {res['decisions']['n_raw_overrides_consensus_a']} mapowań surowych (A).",
        "- Nie ma przedziałów ufności dla różnic między scenariuszami; to są różnice punktowe "
        "na tej samej próbie, nie testy.",
        "- Tekst H1 nie został zmieniony; decyzja o v1 należy do zespołu.",
        "",
    ]
    return "\n".join(lines)
