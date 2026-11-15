# Sources de données

Inventaires complets (date de recherche, emprise, granules) : [`cases/benguerir/inventory/`](../cases/benguerir/inventory/).
On distingue trois états : **présent au catalogue** (CMR), **téléchargé** (octets lus, empreintes SHA-256) et
**exploitable** (contrôle qualité et grilles compatibles).

## Mise à jour v2 (15 novembre 2026)

- **Recherches complètes** : CMR paginé (`CMR-Search-After`, contrôle `CMR-Hits`) et STAC paginé (liens `next`,
  contrôle `numberMatched`), avec déduplication ; l'enregistrement de complétude est dans chaque inventaire.
  Nouvelle interrogation datée du 2026-11-15 : toujours **aucun GUNW validé (`NISAR_L2_GUNW_V1`) ni BETA** sur le
  site ; 3 GCOV validés (P05036, 25 oct.–6 nov.) existent mais concernent un autre observable (étape conditionnelle).
- **NISAR** : les 17 GUNW provisoires ont été recadrés de nouveau avec l'extracteur v2 (clé de cache : emprise,
  couches, version d'extracteur ; empreintes de tous les fichiers y compris `radar_geometry.npz` ; description du
  masque conservée ; publication atomique après vérification). Aucun bit d'anomalie RSLC n'est présent dans la fenêtre.
  Le masque des paires du 26 août → 7 sept. et du 7 → 19 sept. déclare invalide l'acquisition du 2026-09-07 (chiffre
  de sous-fauchée 0) : elles sont écartées pour cette raison.
- **Sentinel-2 — radiométrie vérifiée** : sur la scène S2B du 2026-08-28 (fenêtre de 200 × 200 pixels, bande B02),
  DN Earth Search = DN Planetary Computer − 1000 exactement ; Planetary Computer conservant le DN ESA, le décalage BOA
  est déjà appliqué dans les COG Earth Search. **Réflectance = DN / 10000** ; l'`offset` −0,1 des métadonnées
  `raster:bands` n'est pas appliqué. La v1 l'appliquait (biais de −0,1).
- **Sentinel-2 — masque** : SCL stocké à part (`scl.tif`) ; clairs 4, 5, 6 ; 7 douteux (sensibilité) ; 0, 1, 2, 3,
  8, 9, 10, 11 exclus. 10 m moyennés 2 × 2 en excluant les cellules touchant une absence de données.
- **Sentinel-2 — scènes** : aucun filtre de nuages de tuile ; 83 items trouvés sur l'emprise (41 sur la tuile 29SPR,
  les autres sur 29SNR, mêmes prises de vue) ; 41 lues ; 26 utilisables selon la couverture claire mesurée dans le
  périmètre (≥ 90 %) et le témoin (≥ 80 %). Liste complète : [generated/v2_tables.md](generated/v2_tables.md).
- **ESA WorldCover 2021 v200** (tuile N30W009, CC BY 4.0) lu sur la grille 20 m (classe majoritaire) pour les témoins
  d'occupation du sol comparable.

## Comparaison des données candidates (D2)

| Données | Couverture du site (2026-06 → 11) | Niveau / couches | Géométrie, résolution | Version | Volume, accès | Décision |
|---|---|---|---|---|---|---|
| NISAR L2 GUNW provisoire (`NISAR_L2_GUNW_PROVISIONAL_V1`, DOI 10.5067/NIL2GUNW-P1) | 17 paires, 17 juin → 15 oct. | phase dépliée, cohérence 80 m et 20 m, composantes, masques, écran ionosphérique | 2 géométries (044A/F018, 023D/F072), EPSG:32629, grilles alignées | CRID P05023, produit 1.0.11, provisoire | 1,9–2,4 Go/produit ; Earthdata ; lecture partielle 23–31 Mo | **retenu** |
| NISAR L2 GUNW validé (`NISAR_L2_GUNW_V1`) | aucun granule | — | — | — | — | indisponible ; à surveiller |
| NISAR L2 GCOV (provisoire et V1) | 19 + 3 (P05036, 25 oct.–6 nov.) | rétrodiffusion HH/HV 20 m | mêmes géométries | P05023 / P05036 | 5–6 Go/produit | non retenu : autre observable |
| NISAR L3 SME2 provisoire | 19 | humidité du sol régionale | grille grossière | P05023 | ~100 Mo | non retenu : échelle régionale |
| NISAR GOFF | aucun granule | — | — | — | — | indisponible |
| Sentinel-2 L2A (Copernicus, Earth Search) | 41 scènes tuile 29SPR (v2, sans filtre de tuile ; 26 utilisables) | réflectance de surface 10/20 m, SCL | UTM 29N, grille 20 m alignée sur NISAR | baselines 05.12 puis 05.13 (à partir du 22 sept.) | COG publics, sans identifiant | **référence indépendante** |

## Produits NISAR retenus

Collection `NISAR_L2_GUNW_PROVISIONAL_V1` (concept C2854335566-ASF), ASF DAAC. URL de données :
`https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GUNW_PROVISIONAL_V1/<granule>/<granule>.h5`.
Conditions : compte NASA Earthdata (politique de données ouvertes NASA). Logiciel de traitement ISCE3 0.25.16 ;
DEM Copernicus 30 m (version NISAR 1.2) ; déroulement SNAPHU ; filtrage RFI appliqué.

| Granule | Concept CMR | Acquisitions (UTC) | Durée | Traité le | Taille | Lu | État |
|---|---|---|---|---|---|---|---|
| `NISAR_L2_PR_GUNW_023_044_A_018_024_4000_SH_20260617T054643_20260617T054718_20260629T054642_20260629T054717_P05023_N_F_J_001` | G4257127975-ASF | 2026-06-17T05:46Z → 2026-06-29T05:46Z | 12 j | 2026-08-12 | 2242 Mo | 27.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_024_044_A_018_025_4000_SH_20260629T054642_20260629T054717_20260711T054642_20260711T054717_P05023_N_F_J_001` | G4253192335-ASF | 2026-06-29T05:46Z → 2026-07-11T05:46Z | 12 j | 2026-08-12 | 2226 Mo | 27.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_025_044_A_018_026_4000_SH_20260711T054642_20260711T054717_20260723T054641_20260723T054716_P05023_N_F_J_001` | G4266230268-ASF | 2026-07-11T05:46Z → 2026-07-23T05:46Z | 12 j | 2026-08-13 | 2230 Mo | 27.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_026_044_A_018_028_4000_SH_20260723T054641_20260723T054716_20260816T054640_20260816T054715_P05023_N_F_J_001` | G4284722050-ASF | 2026-07-23T05:46Z → 2026-08-16T05:46Z | 24 j | 2026-08-21 | 2250 Mo | 28.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_028_044_A_018_029_4000_SH_20260816T054640_20260816T054715_20260828T054640_20260828T054714_P05023_N_F_J_001` | G4292552159-ASF | 2026-08-16T05:46Z → 2026-08-28T05:46Z | 12 j | 2026-08-30 | 2193 Mo | 26.2 Mo | retenue |
| `NISAR_L2_PR_GUNW_029_044_A_018_030_4000_SH_20260828T054640_20260828T054714_20260909T054640_20260909T054714_P05023_N_F_J_001` | G4306727299-ASF | 2026-08-28T05:46Z → 2026-09-09T05:46Z | 12 j | 2026-09-11 | 2190 Mo | 25.2 Mo | retenue |
| `NISAR_L2_PR_GUNW_030_044_A_018_031_4000_SH_20260909T054640_20260909T054714_20260921T054640_20260921T054714_P05023_N_F_J_001` | G4320613791-ASF | 2026-09-09T05:46Z → 2026-09-21T05:46Z | 12 j | 2026-09-23 | 2181 Mo | 28.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_031_044_A_018_032_4000_SH_20260921T054640_20260921T054714_20261003T054640_20261003T054714_P05023_N_F_J_001` | G4341196287-ASF | 2026-09-21T05:46Z → 2026-10-03T05:46Z | 12 j | 2026-10-05 | 2193 Mo | 26.2 Mo | retenue |
| `NISAR_L2_PR_GUNW_032_044_A_018_033_4000_SH_20261003T054640_20261003T054714_20261015T054640_20261015T054714_P05023_N_F_J_001` | G4372434189-ASF | 2026-10-03T05:46Z → 2026-10-15T05:46Z | 12 j | 2026-10-17 | 2202 Mo | 26.2 Mo | retenue |
| `NISAR_L2_PR_GUNW_024_023_D_072_025_4000_SH_20260627T192000_20260627T192035_20260709T192000_20260709T192034_P05023_N_F_J_001` | G4247824160-ASF | 2026-06-27T19:20Z → 2026-07-09T19:20Z | 12 j | 2026-08-13 | 2218 Mo | 29.4 Mo | retenue |
| `NISAR_L2_PR_GUNW_025_023_D_072_026_4000_SH_20260709T192000_20260709T192034_20260721T191959_20260721T192034_P05023_N_F_J_001` | G4261782154-ASF | 2026-07-09T19:20Z → 2026-07-21T19:19Z | 12 j | 2026-08-14 | 2210 Mo | 28.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_026_023_D_072_028_4000_SH_20260721T191959_20260721T192034_20260814T191958_20260814T192032_P05023_F_F_J_001` | G4287425496-ASF | 2026-07-21T19:19Z → 2026-08-14T19:19Z | 24 j | 2026-08-25 | 2218 Mo | 28.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_028_023_D_072_029_4000_SH_20260814T191958_20260814T192032_20260826T191958_20260826T192032_P05023_N_F_J_001` | G4298695748-ASF | 2026-08-14T19:19Z → 2026-08-26T19:19Z | 12 j | 2026-09-04 | 2202 Mo | 27.3 Mo | retenue |
| `NISAR_L2_PR_GUNW_029_023_D_072_030_4000_SH_20260826T191958_20260826T192032_20260907T191957_20260907T192032_P05023_N_F_J_001` | G4303686421-ASF | 2026-08-26T19:19Z → 2026-09-07T19:19Z | 12 j | 2026-09-09 | 1920 Mo | 26.2 Mo | écartée (cohérence médiane 0.01, phase plate) |
| `NISAR_L2_PR_GUNW_030_023_D_072_031_4000_SH_20260907T191957_20260907T192032_20260919T191957_20260919T192032_P05023_F_F_J_001` | G4318944588-ASF | 2026-09-07T19:19Z → 2026-09-19T19:19Z | 12 j | 2026-09-21 | 1964 Mo | 23.1 Mo | écartée (cohérence médiane 0.01, phase plate) |
| `NISAR_L2_PR_GUNW_031_023_D_072_032_4000_SH_20260919T191957_20260919T192032_20261001T191958_20261001T192032_P05023_N_F_J_001` | G4337797723-ASF | 2026-09-19T19:19Z → 2026-10-01T19:19Z | 12 j | 2026-10-03 | 2214 Mo | 31.5 Mo | retenue |
| `NISAR_L2_PR_GUNW_032_023_D_072_033_4000_SH_20261001T191958_20261001T192032_20261013T191958_20261013T192032_P05023_N_F_J_001` | G4368502571-ASF | 2026-10-01T19:19Z → 2026-10-13T19:19Z | 12 j | 2026-10-15 | 2210 Mo | 28.3 Mo | retenue |

Couches lues (`provenance.json` de chaque produit, empreintes dans `case.json` → `acquisitions[].layers`) :

| Couche HDF5 (`science/LSAR/GUNW/grids/frequencyA/…`) | Grille | Unité | Usage |
|---|---|---|---|
| `wrappedInterferogram/HH/coherenceMagnitude` | 20 m, 6 × 5 visées | sans unité (0–1) | observable principal |
| `wrappedInterferogram/mask` | 20 m | codage décimal sous-fauchée / eau, bits d'anomalie | validité |
| `unwrappedInterferogram/HH/coherenceMagnitude` | 80 m, 16 × 13 visées | sans unité | contrôle qualité, masque LOS |
| `unwrappedInterferogram/HH/unwrappedPhase` | 80 m | radians | LOS (complément) |
| `unwrappedInterferogram/HH/connectedComponents` | 80 m | étiquette | référence LOS |
| `unwrappedInterferogram/mask` | 80 m | idem | conservé |
| `centerFrequency` | — | Hz (1 239 MHz) | longueur d'onde |

Fenêtre lue : EPSG:32629, x 601 840–619 040 m, y 3 558 800–3 580 000 m (bords alignés sur les grilles 20 et 80 m).
Pas de rééchantillonnage. Les métadonnées `geocoding/*CorrectionApplied = True` concernent le géocodage ; la phase
dépliée est utilisée sans soustraction ionosphérique/troposphérique (limite de la LOS).

## Référence indépendante : Sentinel-2 L2A

- Catalogue STAC : `https://earth-search.aws.element84.com/v1`, collection `sentinel-2-l2a`, tuile MGRS 29SPR.
- v1 : réflectance = DN × 0,0001 − 0,1 et SCL 2, 4, 5, 6, 7 valides — **corrigé en v2** (voir ci-dessus).
- Bandes B02, B03, B04, B08 (10 m moyennés 2 × 2) et B11, B12 (20 m), sur la grille 20 m de NISAR.
- Scènes utilisées pour la comparaison : S2C 2026-06-14, S2A 06-26, S2B 06-29, S2C 07-04, S2C 07-14, S2A 07-16,
  S2B 07-29, S2C 08-13, S2B 08-18, S2A 08-25, S2B 08-28, S2C 09-12 (baseline 05.12). Fonds de carte : S2C 2026-06-04
  et S2C 2026-11-01.
- Licence : données Copernicus Sentinel libres, mention « Contains modified Copernicus Sentinel data 2026 ».
- Aucune scène claire n'encadre les fenêtres radar après le 9 septembre (scènes nuageuses ou espacées) : les 5 paires
  concernées restent sans comparaison optique, état affiché `no_scene_pair`.

## Périmètre

OpenStreetMap (ODbL) : voir [BOUNDARY.md](BOUNDARY.md).

## Reproduire

```powershell
.\.venv\Scripts\python.exe scripts\build_benguerir_zones.py           # zones (option --fetch)
.\.venv\Scripts\python.exe scripts\fetch_benguerir_nisar.py           # inventaire CMR + recadrage GUNW (Earthdata)
.\.venv\Scripts\python.exe scripts\fetch_benguerir_sentinel2.py       # fenêtres Sentinel-2 (public)
.\.venv\Scripts\python.exe -m nasa_in_mining case-run --case cases\benguerir --data data
```

Les données lues (≈ 700 Mo en v2, dont 53 Mo NISAR) restent dans `data/`, ignoré par Git. Le jeton Earthdata se place dans la variable
`EARTHDATA_TOKEN` ou le fichier `.earthdata_token` (ignoré par Git) ; il n'est jamais écrit dans les journaux ni
dans les sorties.
