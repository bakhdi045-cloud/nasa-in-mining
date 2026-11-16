"""Independent supports behind a case: optical comparisons counted per distinct optical pair, structured references.

Several radar pairs can be compared with the same two Sentinel-2 scenes (an ascending and a descending pair
covering the same dates, for instance). They share their optical reference: they are one temporal support, not
several. `optical_evidence` groups the recorded comparisons by (before scene, after scene) and counts a group as
supporting only when at least one of its comparisons has a bootstrap interval entirely above 1.
"""
from __future__ import annotations

from .contract import EvidenceSummary, MiningCase, OpticalEvidence, OpticalGroup, PairResult


def _ci_low(m) -> float | None:
    u = getattr(m, "uncertainty", None)
    return u.low if (u is not None and u.kind == "block_bootstrap_interval") else None


def optical_evidence(pairs: list[PairResult]) -> list[OpticalEvidence]:
    out = []
    for mode in ("strict", "exploratory"):
        comps = [(p, c) for p in pairs if p.status == "ok" for c in p.optical if c.mode == mode]
        okc = [(p, c) for p, c in comps if c.status == "ok" and c.before_item and c.after_item]
        groups: dict[tuple[str, str], list] = {}
        for p, c in okc:
            groups.setdefault((c.before_item, c.after_item), []).append((p, c))
        glist = []
        for i, ((b, a), items) in enumerate(sorted(groups.items(), key=lambda kv: kv[1][0][1].before_datetime or ""), 1):
            c0 = items[0][1]
            glist.append(OpticalGroup(group_id=f"O{i}_{mode}", before_item=b, after_item=a,
                                      before_datetime=c0.before_datetime, after_datetime=c0.after_datetime,
                                      pair_ids=[p.pair_id for p, _ in items],
                                      n_ci_above_1=sum(1 for _, c in items if (_ci_low(c.association_ratio) or 0) > 1)))
        out.append(OpticalEvidence(mode=mode, n_radar_comparisons=len(okc), n_attempted=len(comps),
                                   n_unique_optical_pairs=len(glist),
                                   n_groups_ci_above_1=sum(1 for g in glist if g.n_ci_above_1 > 0), groups=glist))
    return out


def build(pairs: list[PairResult], references=None, derived_at_read: bool = False) -> EvidenceSummary:
    return EvidenceSummary(derived_at_read=derived_at_read, optical=optical_evidence(pairs),
                           references=list(references or []))


def with_evidence(case: MiningCase) -> MiningCase:
    """Case as read: a case recorded before schema 2.1 gets its evidence block computed from its own comparisons.
    Nothing recorded is changed; `derived_at_read` says the block was not written by the pipeline."""
    if case.evidence is not None:
        return case
    return case.model_copy(update={"evidence": build(case.pairs, derived_at_read=True)})
