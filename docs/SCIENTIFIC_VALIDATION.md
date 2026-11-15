# Validation scientifique v2 — Benguerir, juin–octobre 2026

Niveau de présentation : **étude exploratoire calculée, avec associations entre observations et limites explicites.**
Source : `cases/benguerir/output/case.json` (exécution 20261115T150945Z, code `ec59393`). Tableaux complets produits par
script : [generated/v2_tables.md](generated/v2_tables.md). Comparaison avec la v1 : [COMPARISON_V1_V2.md](COMPARISON_V1_V2.md).

## Niveau par observable

| Observable | Niveau | Critères (fixés avant l'exécution) | Manque |
|---|---|---|---|
| Localisation des faibles cohérences | **associé à une observation indépendante** | fenêtres appariées entre orbites avec IC > 1 : 5 (requis 3) ; comparaisons optiques strictes avec IC > 1 : **3 (requis 3)** | terrain daté, produits validés, périmètre récent |
| Déplacement LOS | calculé | interprétation reportée | signe, GNSS/nivellement, corrections atmosphériques |
| Cause | non calculé | — | terrain, calendrier d'exploitation |

Le second critère est atteint au minimum : avec une seule comparaison stricte de moins, le niveau serait « recoupé
entre orbites ». Une association entre capteurs n'est pas une validation et ne donne pas de précision de détection.

## Résultats, avec leurs incertitudes

**Couverture.** 15 paires analysées sur 17. Les paires 26 août → 7 sept. et 7 → 19 sept. (descendantes) sont écartées :
le masque du produit déclare invalide l'acquisition du 2026-09-07 sur toute la zone. Ces fenêtres restent non observées.
Le périmètre est entièrement observable dans les 15 paires.

**Périmètre contre témoin (profil principal).** Dans les 13 paires de 12 jours, la part du périmètre sous le seuil
(1,2 à 3,1 %) dépasse le taux du témoin évalué hors calibration (0,9 à 1,6 %) : rapport de 1,18 à 2,63 (médiane
1,99). L'intervalle à 95 % par blocs n'est entièrement au-dessus de 1 que pour **2 paires sur 13**. Les 2 paires de
24 jours sont résumées à part (rapports 2,78 [1,25 ; 5,47] et 1,68 [0,58 ; 3,72]).

**Sensibilité au seuil.** Au quantile 0,5 %, 13 paires sur 13 dépassent le témoin (rapport médian 2,67) ; au quantile
5 %, **aucune** (0,84). L'excès du périmètre se limite donc aux cohérences les plus basses ; il ne caractérise pas
l'ensemble du périmètre. Recouvrement médian des zones : 0,74 avec 0,5 %, 0,54 avec 5 %.

**Sensibilité au témoin.** Au quantile 1 % : anneau 13/13 (médiane 1,99), anneau 2–4 km 13/13 (1,85), sol nu 13/13
(2,38), cultures 11/13 (1,81). Le périmètre est à 66 % « sol nu » (WorldCover 2021) contre 12 % pour l'anneau : le
témoin « sol nu » est le plus comparable en occupation du sol, et il donne un écart plus grand, pas plus petit.

**Anneaux et parcelles.** Le taux de l'anneau 1–2 km (médiane 0,62 %) est plus faible que celui de l'anneau 2–4 km
(1,27 %) dans 13 paires sur 13 ; les deux anneaux diffèrent en occupation du sol. Les parcelles OSM 2020 hors périmètre
sont plus souvent sous le seuil que le témoin dans 10 paires sur 13 ; leur statut est inconnu.

**Orbites.** 5 fenêtres de 12 jours appariées (10,6 jours de recouvrement chacune ; 3 paires ascendantes sans partenaire) :
rapports 36 à 49, intervalles tous au-dessus de 1, Jaccard 0,26 à 0,40 (médiane 0,35). Les deux orbites désignent
les mêmes secteurs, sans les recouvrir entièrement.

**Sentinel-2.** 41 scènes lues (recherche complète), 26 utilisables. Comparaison stricte possible pour 3 paires :

| Paire | Scènes | P(optique \| radar) | P(optique \| ailleurs) | Rapport [IC 95 %] | Jaccard |
|---|---|---|---|---|---|
| 17 → 29 juin (asc.) | 14 juin / 29 juin | 10,0 % | 0,15 % | 66 [38 ; 153] | 0,095 |
| 16 → 28 août (asc.) | 13 août / 28 août | 77,3 % | 9,7 % | 8,0 [6,0 ; 9,9] | 0,172 |
| 14 → 26 août (desc.) | 13 août / 28 août | 87,6 % | 10,6 % | 8,3 [6,8 ; 10,2] | 0,094 |

La part des changements optiques du périmètre qui tombe dans les pixels radar signalés est de 18 % (médiane) : le
radar signale une petite partie de ce que l'optique voit changer, et la plus grande partie de ce qu'il signale change
aussi optiquement en août, beaucoup moins en juin. Aucune comparaison stricte n'est possible après le 9 septembre :
scènes nuageuses aux dates radar (par exemple 2 et 7 sept., 27 sept., 2 et 4 oct., tous < 90 % clairs dans le
périmètre). La comparaison exploratoire (≤ 8 jours, 10 paires) est publiée à part et n'entre pas dans les critères.

**Répétition.** Ascendante : 8 paires de 12 jours, 2,84 km² sous le seuil au moins une fois, 1,09 km² dans au moins la
moitié des paires (0,93 km² sur paires sans acquisition commune). Descendante : 5 paires, 1,43 / 0,39 / 0,43 km².
Le recouvrement des paires voisines n'est pas nettement supérieur à celui des paires à deux pas (0,43 / 0,37 et
0,28 / 0,19) ; un effet d'acquisition partagée ne peut pas être exclu pour l'orbite descendante (rapport 1,49).

**Zone à vérifier.** Une seule zone remplit le critère : Z1, 0,306 km², 32,2156 N 7,8072 O, dans le périmètre,
« sol nu » ; sous le seuil dans 8 paires sur 8 (asc.) et 5 sur 5 (desc.) ; changement optique sur 94 % de la zone dans
les 3 comparaisons strictes, avec une signature dominante d'humidification ou d'assèchement (hypothèse spectrale,
réflectance corrigée). Hypothèses alternatives : remaniement de surface, humidité, bruit/géométrie, acquisition partagée.

**LOS.** σ du témoin de 0,36 à 6,84 cm ; centiles 5–95 du périmètre dans ±3σ pour les 15 paires. Non interprétée.

## Distinction des incertitudes

- *Statistique* : intervalles par blocs (1 km ; 500 m et 2 km en sensibilité), dans chaque valeur concernée.
- *Seuil* : trois quantiles. *Témoin* : quatre témoins. *Périmètre* : ±1 pixel et parcelles 2020.
- Non estimées : incertitude de la date d'un changement à l'intérieur d'une fenêtre ; erreurs de WorldCover 2021 ;
  précision géométrique du polygone OSM ; justesse des hypothèses spectrales.

## Critère de passage D3 (v2)

| Critère | État |
|---|---|
| Exécution reproductible | satisfait (deux exécutions : 102 sorties identiques) |
| Qualité documentée | satisfait (masque produit, contrôle de cohérence séparé du contrôle de phase, intégrité des fichiers) |
| Comparaison indépendante | partielle : 3 comparaisons strictes, aucune après le 9 septembre |
| Conclusions proportionnées | satisfait : excès faible et limité aux plus basses cohérences ; association, pas validation |
