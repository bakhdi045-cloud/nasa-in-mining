"""Write the result tables quoted by the documentation from the recorded cases (no number typed by hand).

docs/generated/v2_tables.md        tables of the published v2 case (cases/benguerir/output/case.json)
docs/generated/v1_v2_comparison.md v1 (git commit 1a15171) against v2, computed from both recorded case files
Run: python scripts/report_tables.py [--check]   (--check fails if the files on disk differ)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
V1_COMMIT = "1a15171"
OUT = ROOT / "docs" / "generated"


def pct(v, d=2):
    return "—" if v is None else f"{100 * v:.{d}f} %".replace(".", ",")


def num(v, d=2):
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


def ci(m, f=num, d=2):
    u = (m or {}).get("uncertainty") or {}
    return f"[{f(u['low'], d)} ; {f(u['high'], d)}]" if u.get("kind") == "block_bootstrap_interval" else "non estimé"


def v2_tables(c: dict) -> str:
    main = c["method"]["main_profile"]
    L = [f"# Tableaux v2 — exécution {c['run_id']} (code {c['manifest']['code_commit'][:7]})", "",
         "Produit par `scripts/report_tables.py` depuis `cases/benguerir/output/case.json`.", "",
         "## Paires (profil principal : anneau 1–4 km, quantile 1 %, calibration/évaluation par damier de 1 km)", "",
         "| Fenêtre | Orbite | Jours | État | Seuil | Surface sous seuil | Part [IC 95 %] | Taux témoin évalué | Rapport [IC 95 %] |",
         "|---|---|---|---|---|---|---|---|---|"]
    for p in c["pairs"]:
        m = next((x for x in p["profiles"] if x["id"] == main), None)
        if p["status"] != "ok" or m is None:
            L.append(f"| {p['reference_date']} → {p['secondary_date']} | {p['geometry_id']} | {p['span_days']} | {p['status']} : {'; '.join(p['reasons'])} | — | — | — | — | — |")
            continue
        L.append(f"| {p['reference_date']} → {p['secondary_date']} | {p['geometry_id']} | {p['span_days']} | analysée | {num(m['threshold']['value'], 3)} | "
                 f"{num(m['study_flagged_area_km2']['value'], 3)} km² | {pct(p['statistical']['value'])} {ci(p['statistical'], pct)} | "
                 f"{pct(m['evaluation_rate']['value'])} | {num(m['ratio_to_evaluation_rate']['value'])} {ci(m['ratio_to_evaluation_rate'])} |")
    L += ["", "## Sensibilité au quantile et au témoin (paires de 12 jours)", "",
          "| Profil | Paires au-dessus du témoin | Rapport médian | Paires dont l'IC du rapport dépasse 1 |", "|---|---|---|---|"]
    twelve = [p for p in c["pairs"] if p["status"] == "ok" and p["span_days"] == 12]
    ids = sorted({x["id"] for p in twelve for x in p["profiles"]}, key=lambda s: (s.split("@")[0], float(s.split("@")[1])))
    import statistics
    for pid in ids:
        vals = [next(x for x in p["profiles"] if x["id"] == pid) for p in twelve if any(x["id"] == pid for x in p["profiles"])]
        r = [v["ratio_to_evaluation_rate"]["value"] for v in vals if v["ratio_to_evaluation_rate"]["value"] is not None]
        n_ci = sum(1 for v in vals if ((v["ratio_to_evaluation_rate"].get("uncertainty") or {}).get("low") or 0) > 1)
        L.append(f"| {pid} | {sum(1 for v in vals if v['exceeds_control'])}/{len(vals)} | {num(statistics.median(r)) if r else '—'} | "
                 f"{n_ci if pid == main else 'non calculé'} |")
    L += ["", "## Comparaisons Sentinel-2", "",
          "| Paire | Mode | Scènes (écart avant/après) | Observé par les deux | n11 / n10 / n01 / n00 | P(opt|radar) | P(opt|non radar) | Rapport [IC 95 %] | Jaccard |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in c["pairs"]:
        for o in p["optical"]:
            if o["status"] != "ok":
                continue
            t = o["table"]
            L.append(f"| {p['reference_date']} → {p['secondary_date']} ({p['geometry_id']}) | {o['mode']} | {o['before_datetime'][:10]} (−{num(o['gap_days_before'], 1)} j) / "
                     f"{o['after_datetime'][:10]} (+{num(o['gap_days_after'], 1)} j) | {pct(o['joint_observable_fraction']['value'], 0)} | "
                     f"{t['n11']} / {t['n10']} / {t['n01']} / {t['n00']} | {pct(o['p_optical_given_radar']['value'], 1)} | "
                     f"{pct(o['p_optical_given_not_radar']['value'])} | {num(o['association_ratio']['value'], 1)} {ci(o['association_ratio'], num, 1)} | "
                     f"{num(o['jaccard']['value'], 3)} |")
    L += ["", "## Fenêtres appariées entre orbites", "", "| Paire A | Paire B | Recouvrement | n11 / n10 / n01 / n00 | Rapport [IC 95 %] | Jaccard |",
          "|---|---|---|---|---|---|"]
    for m in c["cross_geometry"]["matches"]:
        t = m["table"]
        L.append(f"| {m['pair_a'][5:]} | {m['pair_b'][5:]} | {num(m['overlap_days'], 1)} j | {t['n11']} / {t['n10']} / {t['n01']} / {t['n00']} | "
                 f"{num(m['association_ratio']['value'], 1)} {ci(m['association_ratio'], num, 1)} | {num(m['jaccard']['value'], 3)} |")
    L += ["", f"Paires sans partenaire : {', '.join(x[5:] for x in c['cross_geometry']['unmatched']) or 'aucune'}.", "",
          "## Répétition (paires de 12 jours)", "",
          "| Orbite | Paires | Observations par pixel | Sous seuil ≥ 1 fois | ≥ moitié des paires | ≥ moitié (paires disjointes) | Jaccard paires voisines / à deux pas | Lacunes |",
          "|---|---|---|---|---|---|---|---|"]
    for g in c["geometries"]:
        for r in g["recurrence"]:
            L.append(f"| {r['geometry_id']} | {len(r['pair_ids'])} | {r['observed_pairs_min']}–{r['observed_pairs_max']} | {num(r['flagged_ever_km2']['value'], 3)} km² | "
                     f"{num(r['flagged_half_or_more_km2']['value'], 3)} km² | {num(r['flagged_half_or_more_disjoint_km2']['value'], 3)} km² | "
                     f"{num(r['jaccard_adjacent_pairs']['value'])} / {num(r['jaccard_pairs_two_apart']['value'])} | "
                     f"{'; '.join(a + ' → ' + b for a, b in r['gaps']) or 'aucune'} |")
    L += ["", "## Zones à vérifier", ""]
    for d in c["dossiers"]:
        L.append(f"- {d['id']} : {num(d['area_km2'], 3)} km², {d['centroid'][1]} N {d['centroid'][0]} E, {d['zone']}, {d['landcover']} ; {json.dumps(d['observation'], ensure_ascii=False)}")
    L += ["", "## Niveaux de preuve", ""]
    for v in c["validation"]:
        L.append(f"- {v['observable']} : **{v['level']}** — critères {', '.join(v['criteria']) or '—'}")
    L += ["", "## Scènes Sentinel-2", "", f"{sum(1 for s in c['optical_scenes'] if s['usable'])} utilisables sur {len(c['optical_scenes'])} lues ; "
          f"recherche : {json.dumps(c['optical_search'], ensure_ascii=False)}", "",
          "| Date | Claire (périmètre) | Claire (témoin) | Utilisable |", "|---|---|---|---|"]
    for s in c["optical_scenes"]:
        L.append(f"| {s['datetime'][:10]} | {pct(s['clear_fraction_study'], 0)} | {pct(s['clear_fraction_control'], 0)} | {'oui' if s['usable'] else 'non'} |")
    return "\n".join(L) + "\n"


def comparison(v1: dict, v2: dict) -> str:
    import statistics
    main = v2["method"]["main_profile"]
    L = ["# Comparaison chiffrée v1 / v2", "",
         f"v1 : `cases/benguerir/output/case.json` au commit {V1_COMMIT} (exécution {v1['manifest']['run_id']}). "
         f"v2 : exécution {v2['run_id']} (code {v2['manifest']['code_commit'][:7]}). Produit par `scripts/report_tables.py`.", "",
         "## Par paire (profil principal de chaque version)", "",
         "| Fenêtre | Orbite | v1 seuil | v2 seuil | v1 surface | v2 surface | v1 rapport au témoin | v2 rapport au taux évalué [IC] | v1 concordance S2 (≤ 8 j) | v2 stricte (≤ 3 j) | v2 exploratoire (≤ 8 j) |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    p1 = {p["pair_id"]: p for p in v1["pairs"]}
    for p in v2["pairs"]:
        a = p1.get(p["pair_id"], {})
        z1 = {m["zone_id"]: m for m in a.get("zones", [])}
        s1 = z1.get("study")
        r1 = (s1["flagged_fraction_of_observable"]["value"] / a["control_flag_rate"]["value"]) if s1 and a.get("control_flag_rate", {}).get("value") else None
        m2 = next((x for x in p["profiles"] if x["id"] == main), None)
        o2 = {o["mode"]: o for o in p["optical"]}
        def opt(o):
            return num(o["association_ratio"]["value"], 1) if o and o["status"] == "ok" else "—"
        L.append(f"| {p['reference_date']} → {p['secondary_date']} | {p['geometry_id']} | {num((a.get('threshold') or {}).get('value'), 3)} | "
                 f"{num(m2['threshold']['value'], 3) if m2 else '—'} | {num(s1['flagged_area_km2']['value'], 3) if s1 else '—'} | "
                 f"{num(m2['study_flagged_area_km2']['value'], 3) if m2 else '—'} | {num(r1)} | "
                 f"{(num(m2['ratio_to_evaluation_rate']['value']) + ' ' + ci(m2['ratio_to_evaluation_rate'])) if m2 else '—'} | "
                 f"{num(((a.get('optical') or {}).get('lift') or {}).get('value'), 1)} | {opt(o2.get('strict'))} | {opt(o2.get('exploratory'))} |")
    lv1 = {v["observable"]: v["level"] for v in v1["validation"]}
    lv2 = {v["observable"]: v["level"] for v in v2["validation"]}
    L += ["", "## Niveaux de preuve", "", f"- v1 : {json.dumps(lv1, ensure_ascii=False)}", f"- v2 : {json.dumps(lv2, ensure_ascii=False)}"]
    f1 = {f["id"]: f["params"] for f in v1["findings"]}
    L += ["", "## Conclusions v1 réexaminées", "",
          f"- v1 F1 (rapport médian au témoin) : {num(f1.get('F1', {}).get('median_ratio'))} ; v2 (12 j, taux évalué) : "
          f"{num(next(f['params']['median_ratio'] for f in v2['findings'] if f['id'] == 'F_rate_12d'))}.",
          f"- v1 F3 (concordance optique médiane, ≤ 8 j) : {num(f1.get('F3', {}).get('median_lift'), 1)} sur {f1.get('F3', {}).get('n_pairs')} paires ; "
          f"v2 stricte : {num(next(f['params']['median_ratio'] for f in v2['findings'] if f['id'] == 'F_optical_strict'), 1)} sur "
          f"{next(f['params']['n_compared'] for f in v2['findings'] if f['id'] == 'F_optical_strict')} paires.",
          f"- v1 F5.1 : zone répétée dans {f1.get('F5.1', {}).get('n_pairs_with_cluster_here', '—')} « paires » (comptage de zones, pas de paires) ; "
          f"v2 : {len(v2['dossiers'])} zone(s) à vérifier par recouvrement géométrique."]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    v2 = json.loads((ROOT / "cases" / "benguerir" / "output" / "case.json").read_text(encoding="utf-8"))
    v1 = json.loads(subprocess.run(["git", "show", f"{V1_COMMIT}:cases/benguerir/output/case.json"], cwd=ROOT,
                                   capture_output=True, check=True).stdout.decode("utf-8"))
    files = {OUT / "v2_tables.md": v2_tables(v2), OUT / "v1_v2_comparison.md": comparison(v1, v2)}
    if args.check:
        bad = [str(p.relative_to(ROOT)) for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if bad:
            sys.exit(f"documentation tables out of date: {bad}; run python scripts/report_tables.py")
        print("documentation tables are up to date")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for p, text in files.items():
        p.write_text(text, encoding="utf-8", newline="\n")
        print("written", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
