# Itération v2 — point d'arrêt (15 novembre 2026)

Branche `feature/benguerir-robustness-v2`, créée depuis `1a15171` (référence v1). Travail **en cours** : le code
v2 n'est pas encore exécuté de bout en bout, les tests et l'interface n'ont pas encore été adaptés au contrat 2.0.
Les résultats publiés dans `cases/benguerir/output/` sont toujours ceux de la v1.

## Fait

- **Radiométrie Sentinel-2 corrigée (constat important)** : comparaison pixel à pixel avec Planetary Computer
  (même scène S2B du 2026-08-28, 200 × 200 pixels) : DN Earth Search = DN ESA − 1000 exactement. Le décalage BOA
  est donc déjà appliqué ; réflectance = DN / 10000. La v1 soustrayait 0,1 une seconde fois : les écarts de
  réflectance (changement optique) n'étaient pas affectés, mais NDVI, MNDWI et les lectures spectrales de la v1
  étaient biaisés. Les métadonnées `raster:bands` (offset −0,1) ne s'appliquent pas à ces pixels.
- `access/sentinel2.py` : SCL stocké à part (`scl.tif`) ; classe 2 exclue, classe 7 douteuse ; pagination STAC
  avec déduplication et contrôle de complétude ; cache par paramètres et empreintes ; écriture atomique.
- `access/cmr.py` : pagination `CMR-Search-After`, contrôle `CMR-Hits`.
- `access/nisar_subset.py` : extracteur v2 (clé de cache, empreintes de tous les fichiers, description du masque
  conservée, vérification avant publication atomique).
- `access/worldcover.py` : ESA WorldCover 2021 sur la grille d'analyse, pour des témoins comparables par occupation du sol.
- Scripts de collecte mis à jour ; inventaire CMR re-daté : toujours **aucun GUNW validé ni BETA** sur le site.
- `mining/stats.py` : séparation calibration/évaluation du témoin (damier 1 km), bootstrap par blocs,
  autocorrélation, tables 2 × 2, appariement de zones par recouvrement, recouvrement de fenêtres.
- `mining/contract.py` : contrat 2.0 (valeurs finies, fractions dans [0, 1], incertitudes typées, états compatibles,
  références résolues, manifeste vérifiant les empreintes déclarées).
- `mining/optical.py` : comparaisons stricte (≤ 3 j) et exploratoire (≤ 8 j), couverture claire mesurée dans les
  zones, motif explicite d'absence, table de croisement, rapport avec intervalle, hypothèses spectrales.
- `mining/findings.py` : conclusions orientées par les données, niveaux de preuve à critères explicites (plus de
  promotion sur `median_lift > 2`), LOS rapportée sans interprétation, fiches de vérification par zone.
- `mining/pipeline.py` : réécriture v2 (QC cohérence séparé du QC phase, 4 témoins × 3 quantiles, sensibilité au
  périmètre, récurrence 12 j avec lacunes et paires disjointes, appariement interorbites par fenêtres, exécution dans
  `runs/<id>/` puis publication après vérification). **Importable, jamais exécuté.**

## Données locales (non versionnées)

Collectes interrompues à la demande : 13/17 GUNW recadrés en v2, 16/41 scènes Sentinel-2, WorldCover lu. Relancer
les deux scripts suffit : les éléments vérifiés sont réutilisés, les dossiers `.partial` sont refaits.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\fetch_benguerir_nisar.py
.\.venv\Scripts\python.exe -X utf8 scripts\fetch_benguerir_sentinel2.py
```

## Reste à faire (ordre prévu)

1. Ajouter à `cases/benguerir/case_config.json` les paramètres v2 (`quantiles`, `main_quantile`, `calibration_block_m`,
   `block_m`, `block_sizes_m`, `min_median_coherence`, `min_valid_fraction`, `min_observed_pairs`, `zone_overlap_min`,
   `min_overlap_days`, `coherence_preview_levels`, `max_dossiers`, `block_justification` ; optique : `strict_gap_days`,
   `exploratory_gap_days`, `min_clear_study`, `min_clear_control`, `min_joint_fraction`) et la référence WorldCover.
2. Terminer les collectes, exécuter `case-run`, corriger les erreurs, justifier la taille de bloc par l'autocorrélation.
3. Mettre à jour la CLI (`case-run` sans `--out`), l'API (exécutions multiples, `run` dans l'URL), les tests Python
   (cas inversés et contradictoires, cache corrompu, publication refusée), le schéma JSON.
4. Interface : types générés depuis le schéma + validation ajv, URL partageable, dates radar/optiques, sensibilités,
   proportions absolues, fiches par zone, focus piégé et retour au déclencheur, `inert`, erreurs carte visibles,
   carte statique à l'impression, audit axe dans les trois langues.
5. Versionner les aperçus nécessaires ; test de démarrage depuis un clone propre sans données ni jeton.
6. Docs : ROADMAP (v3), DECISIONS, METHOD, validations, rapport comparatif v1/v2 produit depuis les résultats.
