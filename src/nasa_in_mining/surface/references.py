"""Independent reference protocol: sampling frame, blind annotation tasks and evaluation with explicit refusals.

Purpose: evaluate whether flagged backscatter changes correspond to a *visible* surface change on dated optical
imagery (or site observations), at a unit larger than the effective resolution, with the reviewer blind to radar.
The sampling is drawn once, from a recorded seed, before any annotation. Inclusion probabilities are recorded and
used as weights. Units that share the same optical pair are one group: they are not independent.

Nothing here simulates a review: annotations come from a file filled by a person (`source: human`). Proposals by an
agent or by an algorithm (`source: agent` / `automated`) are counted and reported but never support an effective
reference. Without enough annotated units the evaluation returns `insufficient_reference` with what is missing.
"""
from __future__ import annotations

import numpy as np

from ..mining.contract import MIN_REFERENCE_GROUPS, MIN_REFERENCE_UNITS_PER_CLASS, ReferenceEvidence

STRATA = ("flagged_study", "unflagged_study", "flagged_control", "unflagged_control", "not_observable")
LABELS = ("change_visible", "no_change_visible", "indeterminate")
SOURCES = ("human", "agent", "automated")
UNIT_CELLS = 3          # 3 x 3 analysis cells = 60 m


def _block_sum(a: np.ndarray, k: int) -> np.ndarray:
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    return a[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3))


def frame(flagged: np.ndarray, valid: np.ndarray, study: np.ndarray, control: np.ndarray, k: int = UNIT_CELLS) -> dict:
    """Classify every k x k block lying wholly in the study or the control into a stratum (or 'excluded').

    flagged: bool; valid: bool (cells observed on both dates). Returns {stratum: array of (row, col) block indices}.
    A block is `flagged` when at least half of its cells are valid and flagged cells make half of the valid ones;
    `unflagged` when all its cells are valid and none flagged; `not_observable` when fewer than a third are valid;
    anything between is excluded (recorded, not sampled).
    """
    n = k * k
    v = _block_sum(valid.astype("int32"), k)
    f = _block_sum((flagged & valid).astype("int32"), k)
    ins = _block_sum(study.astype("int32"), k) == n
    inc = _block_sum(control.astype("int32"), k) == n
    out = {}
    for region, inside in (("study", ins), ("control", inc)):
        out[f"flagged_{region}"] = np.argwhere(inside & (v >= n // 2 + 1) & (f * 2 >= v) & (f > 0))
        out[f"unflagged_{region}"] = np.argwhere(inside & (v == n) & (f == 0))
    out["not_observable"] = np.argwhere((ins | inc) & (v * 3 < n))
    return out


def draw(frames: dict[str, dict], per_stratum: int, seed: int) -> tuple[list[dict], dict]:
    """Stratified simple random sample without replacement within (window, stratum).

    frames: {window_id: {stratum: array of block indices, '_group': optical group key}}.
    Returns (units, counts); each unit carries its inclusion probability.
    """
    rng = np.random.default_rng(seed)
    units, counts = [], {s: {"frame": 0, "sampled": 0} for s in STRATA}
    windows = sorted(frames)
    for s in STRATA:
        quota = max(1, int(np.ceil(per_stratum / max(1, len([w for w in windows if len(frames[w][s])])))))
        for w in windows:
            blocks = frames[w][s]
            n = len(blocks)
            counts[s]["frame"] += n
            if n == 0:
                continue
            take = min(quota, n)
            idx = rng.choice(n, size=take, replace=False)
            counts[s]["sampled"] += take
            for i in sorted(idx):
                r, c = (int(x) for x in blocks[i])
                units.append({"unit_id": f"{w}:{s}:{r}_{c}", "window_id": w, "stratum": s, "block_row": r, "block_col": c,
                              "group": frames[w]["_group"], "inclusion_probability": take / n, "stratum_frame_size": n})
    return units, counts


def evaluate(units: list[dict], annotations: list[dict], min_per_class: int = MIN_REFERENCE_UNITS_PER_CLASS,
             min_groups: int = MIN_REFERENCE_GROUPS, reps: int = 2000, seed: int = 0) -> dict:
    """Weighted evaluation of flagged vs unflagged units against annotated visible change.

    Only `source == "human"` annotations made blind to the radar count. Refuses (status `insufficient_reference`)
    when a class has too few determinate units or when too few independent groups stand behind them.
    """
    by_id = {u["unit_id"]: u for u in units}
    ann = {}
    ignored = {"unknown_unit": 0, "not_human": 0, "not_blind": 0, "bad_label": 0}
    for a in annotations:
        u = by_id.get(a.get("unit_id"))
        if u is None:
            ignored["unknown_unit"] += 1
        elif a.get("label") not in LABELS:
            ignored["bad_label"] += 1
        elif a.get("source") != "human":
            ignored["not_human"] += 1
        elif not a.get("blind_to_radar"):
            ignored["not_blind"] += 1
        else:
            ann[a["unit_id"]] = a
    n_ann = len(ann)
    res: dict = {"n_annotated_counted": n_ann, "ignored": ignored,
                 "n_indeterminate": sum(1 for a in ann.values() if a["label"] == "indeterminate")}
    det = {i: a for i, a in ann.items() if a["label"] != "indeterminate"}

    def cls(i):
        s = by_id[i]["stratum"]
        return "flagged" if s.startswith("flagged") else "unflagged" if s.startswith("unflagged") else None
    f_ids = [i for i in det if cls(i) == "flagged"]
    u_ids = [i for i in det if cls(i) == "unflagged"]
    groups = {by_id[i]["group"] for i in det}
    missing = []
    if len(f_ids) < min_per_class:
        missing.append(f"flagged_determinate_units>={min_per_class} (have {len(f_ids)})")
    if len(u_ids) < min_per_class:
        missing.append(f"unflagged_determinate_units>={min_per_class} (have {len(u_ids)})")
    if len(groups) < min_groups:
        missing.append(f"independent_groups>={min_groups} (have {len(groups)})")
    res.update(n_flagged_determinate=len(f_ids), n_unflagged_determinate=len(u_ids), n_groups=len(groups))
    if missing:
        return {**res, "status": "insufficient_reference", "missing": missing, "metrics": None}

    def est(ids_):
        w = np.array([1.0 / by_id[i]["inclusion_probability"] for i in ids_])
        y = np.array([1.0 if det[i]["label"] == "change_visible" else 0.0 for i in ids_])
        return float((w * y).sum() / w.sum()), w, y
    p_f, _, _ = est(f_ids)
    p_u, _, _ = est(u_ids)
    nf = sum({by_id[i]["window_id"] + by_id[i]["stratum"]: by_id[i]["stratum_frame_size"] for i in f_ids}.values())
    nu = sum({by_id[i]["window_id"] + by_id[i]["stratum"]: by_id[i]["stratum_frame_size"] for i in u_ids}.values())

    def metrics(pf, pu):
        tp, fn = nf * pf, nu * pu
        return {"precision": pf, "miss_rate_among_unflagged": pu,
                "recall": tp / (tp + fn) if (tp + fn) else None}
    m = metrics(p_f, p_u)
    rng = np.random.default_rng(seed)
    gl = sorted(groups)
    by_group = {g: [i for i in det if by_id[i]["group"] == g and cls(i)] for g in gl}
    draws = []
    for _ in range(reps):
        pick = rng.choice(len(gl), size=len(gl), replace=True)
        ids_ = [i for k in pick for i in by_group[gl[k]]]
        fi, ui = [i for i in ids_ if cls(i) == "flagged"], [i for i in ids_ if cls(i) == "unflagged"]
        if not fi or not ui:
            continue
        draws.append((est(fi)[0], est(ui)[0]))
    ci = None
    if len(draws) > 0.9 * reps:
        d = np.array(draws)
        ci = {"precision": [float(np.quantile(d[:, 0], 0.025)), float(np.quantile(d[:, 0], 0.975))],
              "miss_rate_among_unflagged": [float(np.quantile(d[:, 1], 0.025)), float(np.quantile(d[:, 1], 0.975))],
              "resampled_unit": "independent group (optical pair)", "n_groups": len(gl)}
    return {**res, "status": "evaluated", "missing": [], "metrics": m, "intervals": ci,
            "indeterminate_rate": res["n_indeterminate"] / n_ann if n_ann else None,
            "scope": "visible surface change on dated optical imagery at 60 m units, units sampled from the recorded frame; "
                     "not an operational attribution and not a validation of the mine boundary"}


def to_reference_evidence(result: dict, meta: dict, units: list[dict], observable: str) -> ReferenceEvidence | None:
    """Structured reference from an evaluation and the metadata declared with the annotation file."""
    if result.get("status") != "evaluated":
        return None
    nf, nu = result["n_flagged_determinate"], result["n_unflagged_determinate"]
    return ReferenceEvidence(
        id=meta.get("reference_id", "R1"), kind="dated_imagery_annotation", observable=observable,
        source=meta.get("source", ""), reviewer=meta.get("reviewer"), reviewer_independent=bool(meta.get("reviewer_independent")),
        blind_to_radar=True, method=meta.get("method"), rights=meta.get("rights"), date_start=meta.get("date_start"),
        date_end=meta.get("date_end"), geometry_ref=meta.get("geometry_ref"), n_units_flagged=nf, n_units_unflagged=nu,
        n_units_indeterminate=result["n_indeterminate"], n_independent_groups=result["n_groups"],
        sampling_probabilities_recorded=all("inclusion_probability" in u for u in units),
        evaluation={"precision": result["metrics"]["precision"], "miss_rate_among_unflagged":
                    result["metrics"]["miss_rate_among_unflagged"]}, limits=[result["scope"]])
