"""Findings, evidence levels and next checks derived from recorded results by explicit rules (v2).

Rules (also in docs/METHOD.md):
- a statement's direction is computed from the data (e.g. inner ring lower / higher / similar), never assumed;
- a level of evidence is reached only through stated criteria with intervals, never from a median ratio alone;
- the maturity of a satellite product never validates the study;
- spectral readings are hypotheses; LOS is reported, not interpreted.
"""
from __future__ import annotations

import numpy as np

from .contract import Finding, NextCheck, ValidationItem
from .evidence import optical_evidence

MIN_STRICT_FOR_ASSOCIATION = 3
MIN_MATCHED_FOR_CROSSCHECK = 3


def _ci_low(m) -> float | None:
    u = getattr(m, "uncertainty", None)
    return u.low if (u is not None and u.kind == "block_bootstrap_interval") else None


def _median(xs):
    xs = [x for x in xs if x is not None]
    return float(np.median(xs)) if xs else None


def derive(case_parts: dict, cfg: dict) -> tuple[list[Finding], list[ValidationItem], list[NextCheck]]:
    pairs, cross, los, recur = case_parts["pairs"], case_parts["cross"], case_parts["los"], case_parts["recurrence"]
    dossiers, scenes = case_parts["dossiers"], case_parts["scenes"]
    main_id = cfg["main_profile"]
    ok = [p for p in pairs if p.status == "ok"]
    findings: list[Finding] = []

    def prof(p, pid):
        return next((x for x in p.profiles if x.id == pid), None)

    for span in sorted({p.span_days for p in ok}):
        sel = [p for p in ok if p.span_days == span]
        ratios = [prof(p, main_id).ratio_to_evaluation_rate for p in sel]
        rv = [r.value for r in ratios if r.value is not None]
        n_exceed = sum(1 for p in sel if prof(p, main_id).exceeds_control)
        n_ci = sum(1 for r in ratios if (_ci_low(r) or 0) > 1)
        findings.append(Finding(id=f"F_rate_{span}d", kind="study_vs_control",
                                params={"span_days": span, "n_pairs": len(sel), "n_exceed": n_exceed, "n_exceed_ci": n_ci,
                                        "min_ratio": min(rv) if rv else None, "median_ratio": _median(rv),
                                        "max_ratio": max(rv) if rv else None, "profile": main_id},
                                evidence=[p.pair_id for p in sel], limit_keys=["limit.threshold_is_selection"]))

    twelve = [p for p in ok if p.span_days == cfg["recurrence_span_days"]]
    if twelve:
        rows = []
        for q in cfg["quantiles"]:
            pid = f"ring@{q}"
            vals = [prof(p, pid) for p in twelve if prof(p, pid)]
            rows.append([q, sum(1 for v in vals if v.exceeds_control), len(vals),
                         _median([v.ratio_to_evaluation_rate.value for v in vals])])
        jac_lo = _median([p.zone_stability["jaccard_vs_q0.005"].value for p in twelve if "jaccard_vs_q0.005" in p.zone_stability])
        jac_hi = _median([p.zone_stability["jaccard_vs_q0.05"].value for p in twelve if "jaccard_vs_q0.05" in p.zone_stability])
        findings.append(Finding(id="F_threshold", kind="threshold_sensitivity",
                                params={"rows": rows, "median_jaccard_low": jac_lo, "median_jaccard_high": jac_hi},
                                evidence=[p.pair_id for p in twelve], limit_keys=["limit.threshold_is_selection"]))
        crow = []
        for c in case_parts["controls"]:
            pid = f"{c}@{cfg['main_quantile']}"
            vals = [prof(p, pid) for p in twelve if prof(p, pid)]
            if vals:
                crow.append([c, sum(1 for v in vals if v.exceeds_control), len(vals),
                             _median([v.ratio_to_evaluation_rate.value for v in vals])])
        findings.append(Finding(id="F_controls", kind="control_sensitivity", params={"rows": crow},
                                evidence=[p.pair_id for p in twelve], limit_keys=["limit.control_not_proven_stable"]))

        def frac(p, zid):
            z = next((m for m in p.zones if m.zone_id == zid), None)
            return None if z is None else z.flagged_fraction.value
        io = [(frac(p, "control_1_2km"), frac(p, "control_2_4km")) for p in twelve]
        io = [(a, b) for a, b in io if a is not None and b is not None]
        if io:
            lower = sum(1 for a, b in io if a < b)
            direction = "lower" if lower == len(io) else "higher" if lower == 0 else "mixed"
            findings.append(Finding(id="F_rings", kind="inner_vs_outer_ring",
                                    params={"direction": direction, "n_lower": lower, "n_pairs": len(io),
                                            "median_inner": _median([a for a, _ in io]),
                                            "median_outer": _median([b for _, b in io])},
                                    evidence=[p.pair_id for p in twelve]))
        pv = [(frac(p, "panels_outside"), prof(p, main_id).evaluation_rate.value) for p in twelve]
        pv = [(a, b) for a, b in pv if a is not None and b is not None]
        if pv:
            findings.append(Finding(id="F_panels", kind="panels_vs_control",
                                    params={"n_above": sum(1 for a, b in pv if a > b), "n_pairs": len(pv),
                                            "median_panels": _median([a for a, _ in pv]),
                                            "median_control": _median([b for _, b in pv])},
                                    evidence=[p.pair_id for p in twelve], limit_keys=["limit.perimeter_2020_not_legal"]))

    for mode in ("strict", "exploratory"):
        comps = [(p, c) for p in ok for c in p.optical if c.mode == mode]
        okc = [(p, c) for p, c in comps if c.status == "ok"]
        ev = next(e for e in optical_evidence(pairs) if e.mode == mode)
        params = {"mode": mode, "n_pairs": len(comps), "n_compared": len(okc),
                  "n_unique_optical_pairs": ev.n_unique_optical_pairs, "n_groups_ci_above_1": ev.n_groups_ci_above_1,
                  "optical_pairs": [[g.before_item, g.after_item, len(g.pair_ids)] for g in ev.groups],
                  "n_ci_above_1": sum(1 for _, c in okc if (_ci_low(c.association_ratio) or 0) > 1),
                  "median_p_opt_given_radar": _median([c.p_optical_given_radar.value for _, c in okc]),
                  "median_p_opt_given_not_radar": _median([c.p_optical_given_not_radar.value for _, c in okc]),
                  "median_ratio": _median([c.association_ratio.value for _, c in okc]),
                  "median_share_explained": _median([c.share_of_optical_change_in_radar_flags.value for _, c in okc]),
                  "max_gap_days": comps[0][1].max_gap_days if comps else None}
        findings.append(Finding(id=f"F_optical_{mode}", kind="optical_association", params=params,
                                evidence=[p.pair_id for p, _ in okc] or [p.pair_id for p, _ in comps],
                                limit_keys=["limit.optical_is_cross_sensor"]))

    if cross.status == "ok":
        findings.append(Finding(id="F_cross", kind="cross_geometry",
                                params={"n_matched": len(cross.matches), "n_unmatched": len(cross.unmatched),
                                        "median_jaccard": cross.median_jaccard.value,
                                        "n_ci_above_1": sum(1 for m in cross.matches if (_ci_low(m.association_ratio) or 0) > 1),
                                        "median_ratio": _median([m.association_ratio.value for m in cross.matches])},
                                evidence=[m.pair_a for m in cross.matches] + [m.pair_b for m in cross.matches]))

    for r in recur:
        a, b = r.jaccard_adjacent_pairs.value, r.jaccard_pairs_two_apart.value
        if a is not None and b is not None:
            findings.append(Finding(id=f"F_adjacent_{r.geometry_id}", kind="shared_acquisition",
                                    params={"geometry": r.geometry_id, "jaccard_adjacent": a, "jaccard_two_apart": b,
                                            "elevated": a > 1.5 * b if b else a > 0},
                                    evidence=r.pair_ids))

    rejected = [p for p in pairs if p.status != "ok"]
    if rejected:
        findings.append(Finding(id="F_rejected", kind="pairs_not_used",
                                params={"n": len(rejected), "reasons": sorted({r for p in rejected for r in p.reasons})},
                                evidence=[p.pair_id for p in rejected], limit_keys=["limit.no_data_is_not_no_change"]))
    long_ = [p for p in ok if p.span_days != cfg["recurrence_span_days"]]
    if long_:
        findings.append(Finding(id="F_long", kind="long_span_pairs",
                                params={"n": len(long_), "spans": sorted({p.span_days for p in long_}),
                                        "windows": [f"{p.reference_date}/{p.secondary_date}" for p in long_]},
                                evidence=[p.pair_id for p in long_]))
    comp = [lp for lp in los if lp.status == "computed"]
    if comp:
        findings.append(Finding(id="F_los", kind="los_reported",
                                params={"n_pairs": len(comp), "n_within_3sigma": sum(1 for lp in comp if lp.within_3sigma),
                                        "min_sigma_cm": min(lp.control_sigma_cm.value for lp in comp),
                                        "max_sigma_cm": max(lp.control_sigma_cm.value for lp in comp)},
                                evidence=[lp.pair_id for lp in comp], limit_keys=["limit.los_not_interpreted"]))
    usable = [s for s in scenes if s.usable]
    findings.append(Finding(id="F_scenes", kind="optical_coverage",
                            params={"n_read": len(scenes), "n_usable": len(usable),
                                    "last_usable": max((s.datetime[:10] for s in usable), default=None)},
                            evidence=[]))
    if dossiers:
        findings.append(Finding(id="F_dossiers", kind="verification_zones", params={"n": len(dossiers)},
                                evidence=[d.id for d in dossiers]))

    # ---------------------------------------------------------------- evidence levels (explicit criteria)
    fs = next((f for f in findings if f.id == "F_optical_strict"), None)
    fc = next((f for f in findings if f.id == "F_cross"), None)
    level, crit, evidence = "not_computed", [], []
    if ok:
        level = "computed"
        evidence += ["evidence.reproducible_run", "evidence.quality_control", "evidence.threshold_and_control_sensitivity"]
    c_cross = bool(fc and fc.params["n_ci_above_1"] >= MIN_MATCHED_FOR_CROSSCHECK)
    crit.append(f"criterion.cross_geometry:{fc.params['n_ci_above_1'] if fc else 0}/{MIN_MATCHED_FOR_CROSSCHECK}")
    if ok and c_cross:
        level = "internally_cross_checked"
        evidence.append("evidence.cross_geometry")
    # the criterion counts independent optical pairs, not radar comparisons that reuse the same two scenes
    c_opt = bool(fs and fs.params["n_groups_ci_above_1"] >= MIN_STRICT_FOR_ASSOCIATION)
    crit.append(f"criterion.strict_optical_pairs:{fs.params['n_groups_ci_above_1'] if fs else 0}/{MIN_STRICT_FOR_ASSOCIATION}")
    if ok and c_cross and c_opt:
        level = "associated_with_independent_observation"
        evidence.append("evidence.optical_association")
    validation = [
        ValidationItem(observable="low_coherence_location", level=level, criteria=crit, evidence_keys=evidence,
                       missing_keys=["missing.field_truth", "missing.validated_products", "missing.recent_perimeter"]),
        ValidationItem(observable="los_displacement", level="computed" if comp else "not_computed",
                       criteria=["criterion.los_deferred"], evidence_keys=["evidence.control_noise"] if comp else [],
                       missing_keys=["missing.sign_check", "missing.gnss_or_levelling", "missing.iono_tropo_correction"]),
        ValidationItem(observable="cause_of_change", level="not_computed", criteria=[], evidence_keys=[],
                       missing_keys=["missing.field_truth", "missing.operations_calendar"]),
    ]

    # ---------------------------------------------------------------- next checks
    checks = [NextCheck(id=f"N_{d.id}", kind="verify_zone",
                        params={"lon": d.centroid[0], "lat": d.centroid[1], "dossier": d.id}, because=[d.id])
              for d in dossiers]
    fp = next((f for f in findings if f.id == "F_panels"), None)
    if fp and fp.params["n_above"] > fp.params["n_pairs"] / 2:
        checks.append(NextCheck(id="N_perimeter", kind="document_recent_perimeter", params={}, because=["F_panels"]))
    if fs and fs.params["n_compared"] < len(ok):
        checks.append(NextCheck(id="N_optical", kind="find_optical_for_uncovered_pairs",
                                params={"n_uncovered": len(ok) - fs.params["n_compared"]}, because=["F_optical_strict"]))
    if comp:
        checks.append(NextCheck(id="N_los", kind="verify_los_before_interpretation", params={}, because=["F_los"]))
    checks.append(NextCheck(id="N_validated", kind="rerun_with_validated_products", params={"collection": "NISAR_L2_GUNW_V1"},
                            because=["limit.provisional_products"]))
    return findings, validation, checks
