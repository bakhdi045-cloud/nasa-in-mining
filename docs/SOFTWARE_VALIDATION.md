# Validation logicielle v2 — 15 novembre 2026

Rapport distinct de la validation scientifique ([SCIENTIFIC_VALIDATION.md](SCIENTIFIC_VALIDATION.md)).
Environnement : Windows 10, Python 3.12.10 (`.venv` du dépôt), Node 24.11.1, Chromium Playwright. NASA_SAR n'est
ni importé ni modifié ; les 16 fichiers extraits gardent les empreintes de `UPSTREAM.json`.

## Résultats

| Contrôle | Commande | Résultat |
|---|---|---|
| Tests Python | `.\.venv\Scripts\python.exe -B -m unittest discover -s tests` | voir tableau final ci-dessous |
| Tableaux de documentation à jour | `python scripts/report_tables.py --check` | inclus dans les tests Python |
| Types TypeScript ↔ schéma | `npm run contract` + test Vitest | identiques |
| Tests unitaires interface | `npm test` (Vitest) | 14 réussis |
| Typage, construction | `npm run typecheck`, `npm run build` | aucune erreur |
| Parcours navigateur | `npm run e2e` (Playwright, bureau 1440 × 900 et mobile 390 × 844) | 10 réussis |
| Accessibilité | axe dans le parcours, FR/EN/AR, deux largeurs | aucune violation sérieuse ou critique |
| Reproductibilité | deux exécutions réelles (20261115T145514Z et 20261115T150945Z) | 102 fichiers de sortie identiques ; contenu du cas identique hors manifeste |
| Intégrité | empreintes recalculées à la lecture (218 entrées) et vérifiées avant publication (102 sorties) | conformes |
| Démarrage depuis une copie propre | voir § ci-dessous | voir § ci-dessous |

## Défauts corrigés et tests associés

| Défaut v1 | Test v2 |
|---|---|
| Taux du témoin mesuré sur ses propres pixels de calibration | `test_calibration_and_evaluation_are_disjoint` |
| Pixels traités comme indépendants | `test_block_bootstrap_needs_enough_blocks` |
| Zones « identiques » par proximité de centroïdes | `test_neighbouring_zone_is_not_the_same_zone` |
| Rapport infini ou absent présenté comme nombre | `test_contingency_keeps_absolute_counts`, `test_every_quantile_and_profile_is_reported` |
| Niveau de preuve promu sur un rapport médian | `test_large_optical_ratio_without_interval_support_does_not_raise_the_level` |
| Direction « anneau intérieur plus faible » écrite d'avance | `test_ring_direction_follows_the_data` (+ test Vitest des gabarits) |
| Fenêtres de 24 jours mélangées | `test_24_day_pairs_are_summarised_separately` |
| LOS déclarée « au niveau du bruit » sans calcul | `test_los_statement_follows_the_values` |
| Motif de rejet imprécis | `test_coherence_qc_reports_its_real_reason`, `test_flat_phase_alone_does_not_reject_coherence` |
| Fichier corrompu ou modifié non détecté | `test_corrupt_input_stops_the_run`, `test_modified_crop_is_detected` |
| Cache réutilisé avec d'autres paramètres | `test_sentinel2_cache_requires_same_parameters` |
| Anciens fichiers mélangés à une nouvelle exécution | `test_new_run_never_reuses_old_files` |
| Publication malgré un fichier manquant | `test_missing_referenced_file_blocks_publication`, `test_recorded_case_and_every_referenced_file` (aperçus de cohérence inclus) |
| `processing.status` dépendant de la seule présence de scènes | `test_status_reflects_missing_optional_steps` |
| Contrat permissif (NaN, fraction > 1, IC inversé) | `ContractRules` (Python) et validation ajv + règles sémantiques (Vitest) |
| Validation sans terrain | `test_never_validated_without_field_truth` |
| Focus perdu, page active derrière le panneau | test Vitest focus/inert et parcours clavier Playwright (3 langues) |
| Erreurs de carte silencieuses | annonce `role="alert"` (inspection) |
| Carte absente de l'impression | test Playwright « print view keeps a static map » |

## Mode hors ligne (définition)

L'application et le serveur local (`python -m nasa_in_mining serve`) fonctionnent sans accès Internet : l'API lit les
résultats publiés dans `cases/*/output/` ; polices, worker MapLibre, fonds Sentinel-2 datés et couches sont servis
localement. Le fond OpenStreetMap n'est chargé que sur choix explicite. Les parcours Playwright bloquent toute requête
hors du service local et vérifient qu'aucune n'est émise. Recalculer l'étude, en revanche, demande les données
(`data/`) et, pour NISAR, un jeton Earthdata.

## Limites connues

- Audit axe automatisé seulement ; pas de test avec lecteur d'écran.
- Le rendu PDF d'impression n'est pas comparé à une référence ; le test vérifie la présence de la carte statique,
  de la légende, des sources et des limites.
- Les exécutions locales (`runs/`) ne sont pas versionnées ; seule l'exécution publiée l'est.
