# Étude de changements de surface — mine OCP Benguerir

**Niveau de présentation : étude exploratoire calculée, avec associations entre observations et limites explicites.**
Aucune référence indépendante n'a été évaluée, le périmètre n'a pas reçu de revue humaine et les produits NISAR sont
provisoires : l'étude **n'est pas validée**. Site unique : OCP Benguerir (Guemassa est exclu).
Chiffres : [tables générées](generated/surface_tables.md) à partir de `study.json`. Rapport imprimable :
`cases/benguerir-surface-study/output/report/report.html`. Audit de départ : [docs/audit/2026-11-16](audit/2026-11-16/AUDIT.md).

## Ce qui est mesuré

| Notion | Définition (figée dans [protocol.json](../cases/benguerir-surface-study/protocol.json) avant les résultats) |
|---|---|
| Observable principal | Δγ⁰ (HH) = 10·log₁₀(γ⁰ après / γ⁰ avant), NISAR L2 GCOV, fréquence A, puissance linéaire |
| Grille | échantillons natifs de 10 m moyennés **en puissance linéaire** sur la grille de 20 m (celle des GUNW) ; agrégats de zone aussi en linéaire avant conversion en dB |
| Résolution effective | la grille n'est pas la résolution : nombre de vues médian ≈ 5 ; l'étalement empirique du témoin sert de précision de travail |
| Variation d'un couple | descriptive : un couple ne dit pas ce qui est habituel |
| Signalement | écart du couple à la **médiane de couples homogènes de même durée sans acquisition commune** (≥ 3, sinon `insufficient_baseline`) supérieur à 3 σ robustes de la moitié « calibration » du témoin ; taux mesuré sur la moitié « évaluation » |
| Intervalle | bootstrap par blocs de 1 km (500 m et 2 km en sensibilité), **conditionnel au protocole** |
| HV | secondaire ; les cellules à moins de 2 × le plancher de bruit (NEBS) sont exclues et comptées |
| Cohérence GUNW | contexte seulement (v2) ; jamais rebaptisée « changement de surface » |

Le masque d'exception du produit P05036 contient des bits de validité par polarisation (256 = HH, 512 = HV) : ils ne sont pas des anomalies (découvert en lisant les premières acquisitions, test `test_validity_bits_of_the_p05036_exception_mask_are_not_anomalies`).

Une grandeur absente est une raison, jamais un zéro ni « stable ». Les raisons par pixel (bits) : hors acquisition,
non focalisé, anomalie instrumentale, valeur invalide, proche du plancher de bruit, sous-pixels insuffisants,
date indisponible. Aucun masque d'ombre ou de repli n'est inventé : le produit ne le fournit pas.

## Résultats de l'exécution publiée (20261116T131850Z)

Calculés par `study-run` sur 21 acquisitions GCOV réelles ; détails dans [generated/surface_tables.md](generated/surface_tables.md).

- **Fenêtres** : 18 (9 ascendantes, 8 descendantes P05023, 1 pilote P05036) ; 16 calculées ; 2 rejetées parce que
  l'acquisition descendante du 7 septembre est entièrement « non focalisée » (le masque du produit, comme dans la v2). Les
  fenêtres de 24 jours qui traversent la lacune instrument (27 juillet–10 août) sont gardées à part : sans référence de
  même durée, `insufficient_baseline`. Pilote P05036 (25 oct.–6 nov.) : une seule fenêtre, décrite sans signalement.
- **Variation d'ensemble** : Δγ⁰ HH périmètre − témoin entre −0,21 et +0,24 dB sur les fenêtres de 12 jours : pas de
  changement de rétrodiffusion d'ensemble du périmètre. Un décalage commun d'environ +0,3 dB (24 jours, des deux orbites)
  et de +0,5 à +0,7 dB (25 oct.–6 nov.) apparaît **dans toutes les zones, témoin compris** : c'est un décalage de fenêtre
  (lacune, calibration, état de surface régional), qu'une comparaison au témoin retire ; il illustre l'effet possible de
  la calibration d'avant le 12 novembre (non vérifiable ici).
- **Signalement** (13 fenêtres de 12 jours avec référence de 3 à 6 couples) : fraction signalée 1,2–3,9 % dans le périmètre
  contre 0,8–1,3 % dans le témoin d'évaluation ; rapport 1,10–3,31, intervalle par blocs entièrement au-dessus de 1 pour
  **6/13** fenêtres (2 ascendantes, 4 descendantes). La référence des fenêtres descendantes repose sur 3–4 couples : le
  rapport plus élevé de cette orbite peut refléter une référence plus bruitée. Un rapport supérieur à 1 n'établit pas un
  changement de surface.
- **Où se concentre l'excès** : Z1 (0,306 km²) et quatre petites zones candidates (0,014–0,061 km²) sont signalées dans
  12–13 des 13 fenêtres (fraction médiane signalée de 24 à 63 % de leurs cellules). Pour Z1, Δγ⁰ HH vaut de −3,4 à +1,4 dB sur les fenêtres de 12 jours
  (jusqu'à +3,9 dB sur celles de 24 jours) alors que le périmètre reste à ±0,3 dB ; le signe est le même sur 4 des 5
  fenêtres qui se recouvrent entre les deux orbites. Les zones `N*` sont choisies **par** la récurrence des signalements :
  leur décompte est circulaire. Z1 provient de la v2 : sa lecture n'est pas indépendante.
- **Optique** : 3 comparaisons strictes mais **2 couples Sentinel-2 distincts** (14–29 juin ; 13–28 août), tous deux avec un
  intervalle > 1 ; 8 comparaisons exploratoires, 5 couples. Z1 est élevée sur les 2 couples stricts, mais ces couples
  viennent de fenêtres de développement ; le couple du 13–28 août soutient aussi une fenêtre descendante hors développement.
- **Références indépendantes** : aucune annotation ; échantillon tiré (40/40/33/40/35 unités par strate) en attente.
- **Périmètre** : carte historique, revue humaine en attente.

**Lecture proportionnée** : le radar GCOV montre, dans de petites zones dont Z1, des variations répétées de plusieurs dB
entre acquisitions, associées dans l'optique à un changement visible sur deux couples ; l'ensemble du périmètre ne varie
pas de façon mesurable par rapport au témoin. Aucun résultat ne dit si ces variations sont des travaux, de l'humidité,
de la végétation, de la rugosité ou de la calibration : cause indéterminée, validation en attente.

## Données et provenance

- **GCOV** (extraction par lecture partielle HTTP, `scripts/fetch_benguerir_gcov.py`, 21 crops d'environ 100 Mo transférés chacun sur 6 Go) : lot P05023 trace 44 ascendante
  cadre 18 (10 acquisitions) et trace 23 descendante cadre 72 (9) ; pilote séparé P05036 trace 23 descendante
  (25 octobre, 6 novembre). Le 27 octobre ascendant est isolé et n'est pas comparé. Catalogue CMR interrogé à
  l'exécution (19 GCOV provisoires, 3 GCOV validés ; mêmes comptes que l'audit). DOI, concept ID, granule, URL, CRID,
  versions, SHA-256 de chaque crop sont dans `data/GCOV/*/provenance.json` et le manifeste.
- **Sentinel-2 L2A** (ESA/Copernicus) : scènes déjà lues pour la v2 (tuile 29SPR).
- **OPERA RTC-S1** (produit NASA/JPL dérivé de Sentinel-1 ESA/Copernicus, bande C) : inventaire dédoublonné
  `inventory/OPERA_L2_RTC-S1_V1_dedup.json` (148 granules, 88 couples rafale-date, 44 dates), **aucun fichier téléchargé,
  aucun calcul** ; bande C et bande L ne se soustraient jamais.
- Page Resources du défi : récupération tentée deux fois, erreur de certificat TLS ; son contenu n'est pas connu.

### Précautions de calibration (ASF, 12 novembre 2026)

Environ 30 % des données de certains modes radar acquises avant le 12 novembre 2026 ont des résidus radiométriques
d'environ 1 dB (RCID 156, 217, 236, 238… : modes DH 40M05N). Les produits utilisés se nomment « 4005 / DHDH », ce qui est
cohérent avec cette famille, mais **le RCID n'est pas dans les métadonnées du produit** : l'applicabilité n'est pas
vérifiable. Conséquences : valeurs absolues possiblement décalées (la soustraction du témoin en annule une partie) ;
P05023 et P05036, et les deux orbites, ne sont jamais mêlés. Le produit indique `noiseCorrectionApplied = False`.
La lacune instrument du 27 juillet au 10 août 2026 est visible et n'est jamais interpolée.

## Périmètre

`boundary/boundary.geojson` + `boundary_review.json` : état **carte historique** (OSM 2020, 39,5 km²), revue humaine
**en attente**, incertitude de position non estimée, classes « installations, excavations, verses, bassins » non
identifiées, aucune revendication légale. Contrôles automatiques descriptifs (occupation du sol, contraste optique de
part et d'autre du bord). Pour passer à `remote_sensing_reviewed` ou `operator_confirmed`, renseigner
`cases/benguerir-surface-study/boundary/boundary_review_input.json` avec relecteur, dates, imagerie et preuves : le code
refuse tout état revu sans ces champs. Rien n'a été envoyé à OCP ou à l'UM6P.

## Comparaison indépendante

1. **Recoupement Sentinel-2** : comparé par fenêtre, **compté par couple optique distinct** (`evidence.optical`) ; les
   comparaisons qui partagent les deux mêmes scènes forment un seul appui temporel. L'étude v2 est relue de la même
   façon (3 comparaisons strictes = **2 couples optiques**).
2. **Références indépendantes** (`annotation/`) : plan d'échantillonnage tiré **une fois** depuis une graine enregistrée,
   unités de 60 m, strates signalées/non signalées/non observables dans le périmètre et le témoin, probabilités
   d'inclusion, paquet d'annotation **en aveugle** (sans résultat radar). Les annotations `agent` ou `automated` sont
   comptées mais n'étayent jamais une validation. L'évaluation exige ≥ 30 unités déterminées par classe, ≥ 3 groupes
   indépendants, un relecteur indépendant et aveugle ; sinon `insufficient_reference`. État actuel : **en attente
   d'annotations**.

## Conclusion par zone

Pour chaque zone : variation radar mesurée, changement optique visible (par couple distinct), cause documentée (aucune),
cause indéterminée. Z1 reste une zone à vérifier. Les zones candidates `N*` sont retenues **parce que** leurs cellules
sont signalées de façon récurrente : leur décompte de fenêtres est circulaire, indiqué comme tel.
Ne sont pas déduits : minerai, teneur, volume, production, danger de digue, vitesse annuelle, déplacement vertical.

## Commandes exactes

```powershell
# environnement : .venv du dépôt ; jeton Earthdata lu localement (EARTHDATA_TOKEN ou .earthdata_token), jamais affiché
.\.venv\Scripts\python.exe scripts\fetch_benguerir_gcov.py --inventory-only
.\.venv\Scripts\python.exe scripts\fetch_benguerir_gcov.py --batch pilot_0816_0828       # test du lot homogène d'intégration
.\.venv\Scripts\python.exe scripts\fetch_benguerir_gcov.py --batch p05023_T044_A_F018
.\.venv\Scripts\python.exe scripts\fetch_benguerir_gcov.py --batch p05023_T023_D_F072
.\.venv\Scripts\python.exe scripts\fetch_benguerir_gcov.py --batch p05036_T023_D_F072    # pilote séparé
.\.venv\Scripts\python.exe scripts\inventory_opera.py                                    # OPERA : inventaire seul
.\.venv\Scripts\python.exe scripts\build_boundary_dossier.py
.\.venv\Scripts\python.exe -m nasa_in_mining study-run --case cases\benguerir-surface-study --no-publish   # exécution isolée
.\.venv\Scripts\python.exe -m nasa_in_mining study-run --case cases\benguerir-surface-study                # publication après vérification
.\.venv\Scripts\python.exe scripts\report_surface_tables.py
.\.venv\Scripts\python.exe -m nasa_in_mining serve --port 8010   # puis http://127.0.0.1:8010 (le port 8000 peut être pris)
```

Le cas v2 (`cases/benguerir/output`) n'est jamais modifié ; la nouvelle étude écrit dans
`cases/benguerir-surface-study/runs/<id>/` puis `output/` après vérification (contrat, fichiers, empreintes).

## Ce qui reste hors de portée de ce travail

Revue humaine ou confirmation de l'opérateur du périmètre ; annotations indépendantes en aveugle ; observations de
terrain, calendrier d'opérations, pluie/arrosage ; RCID des acquisitions ; données GCOV validées sur la période
principale ; OPERA (inventaire seul) ; test avec lecteur d'écran. La demande de ces éléments est préparée dans
[docs/NEXT_STEPS.md](NEXT_STEPS.md) et n'a pas été envoyée.
