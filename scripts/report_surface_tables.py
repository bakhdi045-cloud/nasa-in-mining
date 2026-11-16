"""Markdown tables of a recorded surface study, computed from its study.json (never typed by hand).

Run: python scripts/report_surface_tables.py [--run <run_id>]  ->  docs/generated/surface_tables.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "benguerir-surface-study"


def f(v, d=2):
    return "—" if v is None else f"{v:.{d}f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    args = ap.parse_args()
    folder = CASE / "runs" / args.run if args.run else CASE / "output"
    s = json.loads((folder / "study.json").read_text(encoding="utf-8"))
    o = [f"# Tables de l'étude de surface — exécution {s['run_id']}", "",
         "Générées par `scripts/report_surface_tables.py` à partir de `study.json` ; aucun nombre n'est saisi à la main.", ""]
    o += ["## Dates et lots", "", "| Lot | Collection / CRID | Acquisitions | Utilisables | Fenêtres | Calculées | Lacunes |", "|---|---|---:|---:|---:|---:|---|"]
    for b in s["batches"]:
        gaps = "; ".join(f"{g['between'][0]} → {g['between'][1]} ({g['span_days']} j)" for g in b["gaps"]) or "—"
        o.append(f"| {b['batch_id']} | {b['collection']} / {b['crid']} | {b['n_acquisitions']} | {b['n_usable']} | {b['n_windows']} | {b['n_windows_computed']} | {gaps} |")
    o += ["", "## Fenêtres (HH, observable principal)", "",
          "| Fenêtre | Orbite | Durée | Δ périmètre (dB) | Δ périmètre − témoin (dB) | Couples de référence | σ témoin (dB) | Fraction signalée périmètre | témoin | Rapport (IC 95 %) | Dév. |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for w in s["windows"]:
        p = next(x for x in w["pols"] if x["pol"] == "HH")
        st = next((z for z in p["zones"] if z["zone_id"] == "study"), None)
        fl = p["flags"]
        u = fl and fl["ratio"].get("uncertainty")
        ic = f"[{f(u['low'])} ; {f(u['high'])}]" if u and u.get("kind") == "block_bootstrap_interval" else ""
        sg = p["baseline"].get("sigma_db")
        o.append(f"| {w['before_date']} → {w['after_date']}{' (rejetée)' if w['status'] == 'rejected' else ''} | {w['direction']} | {w['span_days']} | "
                 f"{f(st and st['aggregate_db']['value'])} | {f(p['study_minus_control_db']['value'])} | {p['baseline']['n_pairs'] if p['baseline']['status'] == 'ok' else p['baseline']['status']} | "
                 f"{f(sg and sg['value'])} | {f(fl and fl['study_fraction']['value'], 4)} | {f(fl and fl['control_fraction']['value'], 4)} | "
                 f"{f(fl and fl['ratio']['value'])} {ic} | {'oui' if w['development_window'] else ''} |")
    zids = [c["zone_id"] for c in s["conclusions"]]
    o += ["", "## Δγ⁰ HH agrégé par zone et par fenêtre (dB, puissance linéaire avant conversion)", "",
          "| Fenêtre | Orbite | Durée | " + " | ".join(zids) + " |", "|---|---|---:|" + "---:|" * len(zids)]
    for w in s["windows"]:
        p = next(x for x in w["pols"] if x["pol"] == "HH")
        z = {x["zone_id"]: x["aggregate_db"]["value"] for x in p["zones"]}
        o.append(f"| {w['before_date']} → {w['after_date']} | {w['direction']} | {w['span_days']} | " + " | ".join(f(z.get(i)) for i in zids) + " |")
    o += ["", "## Appui optique par couple Sentinel-2 distinct", "", "| Mode | Comparaisons radar | Couples optiques distincts | Couples avec IC > 1 |", "|---|---:|---:|---:|"]
    for e in s["evidence"]["optical"]:
        o.append(f"| {e['mode']} | {e['n_radar_comparisons']} | {e['n_unique_optical_pairs']} | {e['n_groups_ci_above_1']} |")
    o += ["", "| Groupe | Avant | Après | Fenêtres radar |", "|---|---|---|---|"]
    for e in s["evidence"]["optical"]:
        for g in e["groups"]:
            o.append(f"| {g['group_id']} | {g['before_item']} | {g['after_item']} | {', '.join(g['pair_ids'])} |")
    o += ["", "## Conclusion par zone", "", "| Zone | Surface (km²) | Radar | Fenêtres au-dessus du témoin | Fraction signalée médiane | Δ médian vs témoin (dB) | Optique | Couples optiques jugés / élevés | Sélection |", "|---|---:|---|---:|---:|---:|---|---:|---|"]
    for c in s["conclusions"]:
        r, op = c["radar_params"], c["optical_params"]
        o.append(f"| {c['zone_id']} | {f(c['area_km2'], 3)} | {c['radar_variation']} | {r['n_windows_elevated']}/{r['n_windows_with_baseline']} | {f(r['median_flagged_fraction'], 4)} | "
                 f"{f(r['median_study_minus_control_db'])} | {c['optical_visible_change']} | {op['n_distinct_optical_pairs_elevated']}/{op['n_distinct_optical_pairs_assessed']} | {r['selection']} |")
    ref = s["references"]
    o += ["", "## Références indépendantes", "", f"État : **{ref['status']}** ; annotations comptées : {ref['n_annotated']} ; unités tirées : {ref['n_units_sampled']} ; manque : {', '.join(ref['missing']) or 'rien'}.", ""]
    out = ROOT / "docs" / "generated" / "surface_tables.md"
    out.write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
    print("written", out)


if __name__ == "__main__":
    main()
