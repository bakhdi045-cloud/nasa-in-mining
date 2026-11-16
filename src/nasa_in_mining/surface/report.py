"""Printable HTML report of a SurfaceStudy (French), generated only from the validated study object.

Every figure printed here is a field of study.json; the report states what is measured, what is associated with an
independent observation, what is documented and what stays undetermined. It never calls the study validated.
"""
from __future__ import annotations

from html import escape as e
from pathlib import Path

from .contract import SurfaceStudy

CSS = """
:root{color-scheme:light;--ink:#1d2433;--mut:#5b6577;--line:#d7dce5;--acc:#8a4b12;--bg:#fff}
body{font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif;color:var(--ink);background:var(--bg);margin:0 auto;max-width:980px;padding:24px 16px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 8px;border-bottom:2px solid var(--line);padding-bottom:4px}h3{font-size:15px;margin:18px 0 4px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}th,td{border:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}th{background:#f3f5f9}
.note{background:#fbf4ea;border-left:4px solid var(--acc);padding:8px 12px;margin:10px 0}.mut{color:var(--mut)}
figure{margin:8px 0;display:inline-block;width:32%;vertical-align:top}figure img{width:100%;border:1px solid var(--line)}figcaption{font-size:12px;color:var(--mut)}
@media print{body{max-width:none;padding:0}h2{break-after:avoid}table,figure{break-inside:avoid}}
"""
LEVEL = {"measured": "mesurée", "insufficient_baseline": "référence temporelle insuffisante", "unavailable": "indisponible"}
OPT = {"corroborated_two_or_more_optical_pairs": "visible sur au moins deux couples optiques distincts",
       "one_optical_pair": "visible sur un seul couple optique", "not_elevated": "non visible (taux non supérieur au témoin)",
       "not_observable": "non observable (nuages ou recouvrement insuffisant)", "not_assessed": "non évalué (aucun couple optique)"}


LIMITS_FR = {
    "limit.gcov_provisional": "Produits GCOV provisoires (CRID P05023) : la collection validée ne couvre pas la période principale.",
    "limit.calibration_before_2026_11_12": "Environ 30 % des données de certains modes acquises avant le 12 novembre 2026 ont des résidus radiométriques d'environ 1 dB ; le RCID n'est pas dans les métadonnées du produit (le nom 4005 / DHDH est cohérent avec une famille de modes concernée) : l'applicabilité n'a pas pu être vérifiée. Les valeurs absolues peuvent être décalées ; la soustraction du témoin en annule une partie.",
    "limit.no_noise_correction": "Le produit n'applique pas la correction du bruit : les pixels proches du plancher de bruit sont exclus, surtout en HV.",
    "limit.effective_resolution": "La grille de 10 m (20 m ici) n'est pas la résolution effective : le nombre de vues médian est d'environ 5 et l'étalement empirique du témoin sert de précision de travail.",
    "limit.perimeter_historical": "Le périmètre est la carte OSM de 2020 : ni concession, ni limite d'exploitation actuelle ; sa revue humaine est en attente.",
    "limit.no_independent_reference": "Aucune référence indépendante n'a été évaluée : pas de précision, pas de validation, pas de vérité terrain.",
    "limit.optical_dependency": "Les comparaisons Sentinel-2 réutilisent des couples de scènes : elles ne sont pas des confirmations indépendantes. Le recoupement entre capteurs observe aussi les mêmes propriétés persistantes du terrain.",
    "limit.not_attribution": "Une variation radar n'est pas une cause : humidité, végétation, rugosité, opérations et calibration restent possibles.",
    "limit.development_windows": "Les fenêtres du 17–29 juin et du 16–28 août ont déjà été examinées dans l'étude v2 : données de développement, pas un échantillon d'évaluation indépendant.",
    "limit.interval_conditional": "Les intervalles par blocs sont conditionnels au protocole : ils ne couvrent ni le choix du témoin, ni le seuil, ni la géométrie, ni l'interprétation.",
    "limit.p05036_separate": "La période du 25 octobre au 6 novembre (CRID P05036) est analysée séparément et n'est jamais mêlée à P05023 ni à l'autre orbite.",
    "limit.instrument_gap": "Aucune donnée n'a été collectée par la plateforme du 27 juillet au 10 août 2026 : la lacune reste visible et n'est pas interpolée.",
    "limit.no_data_is_not_no_change": "Une donnée absente ou une référence insuffisante n'est ni zéro ni « stable ».",
    "limit.not_ore_or_hazard": "Ni minerai, ni teneur, ni volume, ni production, ni danger de digue, ni vitesse annuelle, ni déplacement vertical ne sont déduits de ces résultats.",
}
STATE_FR = {"historical_map": "carte historique", "draft_interpretation": "interprétation provisoire",
            "remote_sensing_reviewed": "revu sur imagerie datée", "operator_confirmed": "confirmé par l'opérateur"}
REF_FR = {"awaiting_annotations": "en attente d'annotations", "annotated_insufficient": "annotations insuffisantes", "evaluated": "évaluées"}
STRATA_FR = {"flagged_study": "signalées dans le périmètre", "unflagged_study": "non signalées dans le périmètre", "flagged_control": "signalées dans le témoin",
             "unflagged_control": "non signalées dans le témoin", "not_observable": "non observables"}
MISSING_FR = {"annotations_filled_by_an_independent_person": "annotations renseignées par une personne indépendante",
              "annotation_meta": "fichier de métadonnées de l'annotation (relecteur, méthode, droits)"}
REASON_FR = {"outside_acquisition": "hors de l'acquisition", "not_fully_focused": "non focalisé (masque produit)", "instrument_anomaly": "anomalie instrumentale",
             "invalid_value": "valeur invalide", "near_noise_floor": "proche du plancher de bruit", "insufficient_subpixel_coverage": "sous-pixels insuffisants",
             "date_not_available": "date non disponible", "incompatible_grid": "grille incompatible", "insufficient_coverage": "couverture insuffisante"}
MODE_FR = {"strict": "stricte (≤ 3 j)", "exploratory": "exploratoire (≤ 8 j)"}
LAYER_FR = {"layer.quality": "Qualité : raisons de non-observation", "layer.delta_db": "Δγ⁰ HH (dB)", "layer.flags_temporal": "Signalement par rapport à la référence temporelle"}


def _f(v, d=2, unit=""):
    return "—" if v is None else f"{v:.{d}f}{unit}"


def _m(m, d=2, unit=""):
    return "<span class='mut'>n. d.</span>" if m.value is None else _f(m.value, d, unit)


def write(folder: Path, s: SurfaceStudy) -> str:
    comp = [w for w in s.windows if w.status == "computed"]
    pilot = next((w for w in s.windows if w.development_window and w.after_date == "2026-08-28"), None)
    h = [f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>Étude de changements de surface — Benguerir</title><style>{CSS}</style></head><body>",
         f"<h1>Étude de changements de surface — mine OCP Benguerir</h1><p class='mut'>Exécution {e(s.run_id)} · protocole {e(s.protocol.version)} "
         f"(figé le {e(s.protocol.frozen_utc[:10])}) · données NISAR L2 GCOV (gamma-0), Sentinel-2 L2A</p>",
         "<div class='note'><b>Niveau de présentation : étude exploratoire calculée, avec associations entre observations et limites explicites.</b> "
         "Aucune référence indépendante n'a encore été évaluée ; l'étude n'est pas validée. Les produits NISAR utilisés sont provisoires ou antérieurs "
         "au 12 novembre 2026.</div>"]
    b = s.boundary
    h += ["<h2>1. Périmètre</h2>",
          f"<p>État : <b>{e(STATE_FR[b.state])}</b> ({'revue humaine en attente' if b.review_status == 'pending_human_review' else 'revue enregistrée'}). "
          f"Source : {e(b.source)} ({e((b.source_date or '')[:10])}), {b.area_km2:.3f} km². Ce n'est ni une concession, ni une zone autorisée, ni une limite d'exploitation. "
          "Incertitude de position : non estimée. Les installations, excavations, verses et bassins ne sont pas séparés.</p>"]
    h += ["<h2>2. Dates et qualité</h2><table><tr><th>Géométrie</th><th>Lot</th><th>Collection / CRID</th><th>Dates utilisables</th><th>Dates rejetées</th><th>Lacunes</th></tr>"]
    for bt in s.batches:
        rej = [a.time_utc[:10] + " (" + ", ".join(REASON_FR.get(r, r) for r in a.reasons) + ")" for a in s.acquisitions if a.status == "rejected" and a.geometry_id == bt.geometry_id and a.crid == bt.crid]
        gaps = "; ".join(f"{g['between'][0]} → {g['between'][1]} ({g['span_days']} j{', lacune instrument documentée' if g['documented_instrument_gap'] else ''})" for g in bt.gaps) or "—"
        h.append(f"<tr><td>{e(bt.geometry_id)} {e(bt.direction)}</td><td>{e(bt.role)}</td><td>{e(bt.collection)} / {e(bt.crid)}</td>"
                 f"<td>{bt.n_usable}/{bt.n_acquisitions}</td><td>{e('; '.join(rej)) or '—'}</td><td>{e(gaps)}</td></tr>")
    h.append("</table><p class='mut'>Chaque pixel porte des raisons de non-observation (bits) : hors acquisition, non focalisé, anomalie instrumentale, valeur invalide, "
             "proche du plancher de bruit, couverture insuffisante des sous-pixels. Les couches sont exportées en GeoTIFF (<code>rasters/quality_*.tif</code>).</p>")
    h += ["<h2>3. Variation de rétrodiffusion</h2><p>Observable principal : Δγ⁰ (HH) = 10·log₁₀(γ⁰ après / γ⁰ avant), moyenne en puissance linéaire avant conversion en dB, "
          "grille de 20 m (échantillons natifs de 10 m). Le signalement compare un couple à la médiane de couples homogènes de même durée qui ne partagent aucune acquisition ; "
          "sinon : « référence temporelle insuffisante ».</p>",
          "<table><tr><th>Fenêtre</th><th>Orbite</th><th>Durée</th><th>Δ périmètre − témoin (dB)</th><th>Référence</th><th>Rapport signalé (IC 95 %)</th><th>Dév.</th></tr>"]
    for w in s.windows:
        p = next((x for x in w.pols if x.pol == "HH"), None)
        if p is None:
            continue
        ratio, ic = "—", ""
        if p.flags and p.flags.ratio.value is not None:
            u = p.flags.ratio.uncertainty
            ratio = _f(p.flags.ratio.value, 2)
            ic = f" [{_f(u.low, 2)} ; {_f(u.high, 2)}]" if u and u.kind == "block_bootstrap_interval" else " (intervalle non estimé)"
        status = {"ok": f"{p.baseline.n_pairs} couples", "insufficient_baseline": "insuffisante", "not_applicable": "—"}[p.baseline.status]
        h.append(f"<tr><td>{e(w.before_date)} → {e(w.after_date)}{' <i>(rejetée)</i>' if w.status == 'rejected' else ''}</td><td>{e(w.direction)}</td><td>{w.span_days} j</td>"
                 f"<td>{_m(p.study_minus_control_db, 2)}</td><td>{status}</td><td>{ratio}{ic}</td><td>{'oui' if w.development_window else ''}</td></tr>")
    h.append("</table><p class='mut'>« Dév. » : fenêtre déjà examinée dans l'étude v2 (données de développement, pas un échantillon d'évaluation indépendant). "
             "Les intervalles sont conditionnels au protocole (blocs de 1 km) ; ils ne couvrent ni le choix du témoin, ni la géométrie, ni l'interprétation.</p>")
    if pilot:
        h.append(f"<h3>Fenêtre pilote {e(pilot.before_date)} → {e(pilot.after_date)}</h3>")
        for lid in [pilot.quality_layer_id] + [l for p in pilot.pols if p.pol == "HH" for l in p.layer_ids]:
            lay = next((x for x in s.layers if x.id == lid), None)
            if lay:
                h.append(f"<figure><img src='{e(lay.url)}' alt='{e(lay.id)}'><figcaption>{e(LAYER_FR.get(lay.title_key, lay.title_key))}</figcaption></figure>")
        if pilot.gunw_context:
            g = pilot.gunw_context
            h.append(f"<p class='mut'>Contexte (observable différent, cohérence GUNW v2) : rapport {_f(g.get('ratio'), 2)}, intervalle "
                     f"[{_f(g.get('ci_low'), 2)} ; {_f(g.get('ci_high'), 2)}].</p>")
    h += ["<h2>4. Comparaison indépendante</h2>"]
    for ev in s.evidence.optical:
        h.append(f"<p><b>Optique {e(MODE_FR[ev.mode])}</b> : {ev.n_radar_comparisons} comparaisons radar, <b>{ev.n_unique_optical_pairs} couple(s) Sentinel-2 distinct(s)</b>, "
                 f"{ev.n_groups_ci_above_1} dont l'intervalle du rapport dépasse 1. Les comparaisons qui partagent les deux mêmes scènes forment un seul appui temporel.</p>")
        if ev.groups:
            h.append("<table><tr><th>Groupe</th><th>Avant</th><th>Après</th><th>Fenêtres radar</th></tr>" + "".join(
                f"<tr><td>{e(g.group_id)}</td><td>{e(g.before_item)}</td><td>{e(g.after_item)}</td><td>{e(', '.join(g.pair_ids))}</td></tr>" for g in ev.groups) + "</table>")
    r = s.references
    h.append(f"<p><b>Références indépendantes :</b> état <b>{e(REF_FR[r.status])}</b>. Unités de 3 × 3 cellules d'analyse (60 m), tirées d'une graine enregistrée, "
             f"stratifiées selon le statut radar. Échantillon tiré : "
             f"{', '.join(f'{STRATA_FR[k]} = {v}' for k, v in r.n_units_sampled.items()) or 'aucun'}. Annotations comptées : {r.n_annotated}. "
             f"Manque : {e('; '.join(MISSING_FR.get(k, k) for k in r.missing)) or 'rien'}. Sans référence évaluée, aucune précision ni validation n'est annoncée.</p>")
    h += ["<h2>5. Conclusion par zone</h2><table><tr><th>Zone</th><th>Surface</th><th>Variation radar mesurée</th><th>Changement optique visible</th><th>Cause</th></tr>"]
    for c in s.conclusions:
        rp, op = c.radar_params, c.optical_params
        radar = LEVEL[c.radar_variation]
        if c.radar_variation == "measured":
            radar += f" : {rp['n_windows_elevated']}/{rp['n_windows_with_baseline']} fenêtres au-dessus du témoin (fraction médiane signalée {_f(rp['median_flagged_fraction'], 3)}) ; Δ médian vs témoin {_f(rp['median_study_minus_control_db'], 2)} dB"
        elif rp.get("median_study_minus_control_db") is not None:
            radar += f" ; Δ médian vs témoin {_f(rp['median_study_minus_control_db'], 2)} dB (descriptif)"
        h.append(f"<tr><td><b>{e(c.zone_id)}</b></td><td>{_f(c.area_km2, 3, ' km²')}</td><td>{radar}</td>"
                 f"<td>{OPT[c.optical_visible_change]} ({op['n_distinct_optical_pairs_elevated']}/{op['n_distinct_optical_pairs_assessed']} couples ; "
                 f"{op['n_elevated_pairs_with_a_window_outside_development']} soutenu(s) aussi hors fenêtres de développement)</td>"
                 f"<td>aucune cause documentée ; indéterminée</td></tr>")
    h.append("</table><p class='mut'>Z1 est une zone à vérifier, pas une excavation démontrée. Hypothèses alternatives : humidité, végétation ou culture, rugosité, opérations, "
             "calibration instrumentale. Ni minerai, teneur, volume, production, danger de digue, vitesse annuelle ou déplacement vertical ne sont déduits de ces résultats.</p>")
    h += ["<h2>6. Limites</h2><ul>"] + [f"<li>{e(LIMITS_FR.get(k, k))}</li>" for k in s.limits] + ["</ul>"]
    h += ["<h2>7. Sources et traçabilité</h2><ul>"] + [f"<li><a href='{e(x['url'])}'>{e(x['title'])}</a></li>" for x in s.external_sources] + ["</ul>",
          f"<p class='mut'>Contrat {e(s.schema_version)} ; protocole sha256 {e(s.protocol.sha256[:16])}… ; le manifeste (study.json → manifest) relie chaque sortie à ses entrées hachées.</p></body></html>"]
    (folder / "report").mkdir(parents=True, exist_ok=True)
    out = folder / "report" / "report.html"
    # relative image paths: the report sits one folder below the layers
    out.write_text("".join(h).replace("src='layers/", "src='../layers/"), encoding="utf-8", newline="\n")
    return "report/report.html"
