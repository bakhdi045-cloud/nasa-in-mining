# Rapport comparatif v1 / v2

v1 : commit `1a15171` (exécution 20261115T034718Z). v2 : exécution 20261115T150945Z, code `ec59393`.
Tous les chiffres viennent des deux fichiers `case.json` enregistrés ; le tableau détaillé est produit par
`scripts/report_tables.py` dans [generated/v1_v2_comparison.md](generated/v1_v2_comparison.md), et les tableaux
complets v2 sont dans [generated/v2_tables.md](generated/v2_tables.md).

Objectif de la v2 : fiabilité, pas un résultat plus spectaculaire. Plusieurs conclusions v1 sont affaiblies ou retirées.

## Ce qui a changé dans la méthode et pourquoi les chiffres changent

| Changement | v1 | v2 | Effet sur les chiffres |
|---|---|---|---|
| Nom de l'observable | « perte de cohérence » | « faible cohérence relative au témoin » ; « baisse » réservé à une comparaison temporelle (non faite) | aucun ; interprétation corrigée |
| Taux du témoin | mesuré sur les pixels ayant servi au quantile (≈ 1 % par construction) | seuil calibré sur une moitié du témoin (damier de 1 km), taux mesuré sur l'autre moitié | taux évalués de 0,9 à 1,6 % ; rapport médian (12 j) **2,60 → 1,99** |
| Incertitude | aucune | bootstrap par blocs de 1 km (500 m et 2 km en sensibilité) | le rapport n'est entièrement au-dessus de 1 que dans **2 paires de 12 jours sur 13** |
| Seuil | 1 % seul (0,5 et 5 % en surface seulement) | 0,5 %, 1 %, 5 % systématiquement, quatre témoins | à **5 %, 0 paire sur 13** dépasse le témoin (rapport médian 0,84) : l'excès du périmètre est limité aux cohérences les plus basses |
| Témoins | anneau 1–4 km | anneau, anneau 2–4 km, anneau « sol nu », anneau « cultures » (WorldCover 2021) | même sens avec tous les témoins au quantile 1 % (11 à 13 paires sur 13) |
| Contrôle qualité | phase plate + cohérence médiane 80 m | contrôle de cohérence (masque produit, part valide, médiane 20 m) séparé du contrôle de phase (LOS) | mêmes 2 paires écartées, mais pour leur vraie raison : **le masque du produit déclare invalide l'acquisition du 2026-09-07** |
| Sentinel-2 : radiométrie | réflectance = DN × 10⁻⁴ − 0,1 | vérifié pixel à pixel : DN Earth Search = DN ESA − 1000, donc réflectance = DN × 10⁻⁴ | différences de réflectance inchangées ; **NDVI/MNDWI v1 biaisés** |
| Sentinel-2 : masque | SCL 2, 4, 5, 6, 7 valides | SCL 4, 5, 6 ; 7 douteux (sensibilité) ; 2 exclu | moins de pixels ; rapport avec SCL 7 publié à côté |
| Sentinel-2 : scènes | filtre nuages de tuile ≤ 60 %, écart ≤ 8 j | recherche complète paginée (41 scènes), couverture claire mesurée dans les zones ; stricte ≤ 3 j, exploratoire ≤ 8 j séparée | **3 comparaisons strictes** (au lieu de 10 à ≤ 8 j) |
| Association optique | rapport de concordance seul | table 2 × 2, proportions absolues, Jaccard, part des changements optiques couverte, IC | rapports 8 à 66, mais P(optique | radar) = **10 %** pour la paire 17–29 juin et 18 % seulement des changements optiques tombent dans les pixels radar signalés (médiane stricte) |
| Orbites | cartes de répétition sur 8 et 5 paires (supports différents) | fenêtres de 12 j appariées un à un (recouvrement ≥ 6 j) | 5 fenêtres appariées, Jaccard médian 0,35, IC du rapport > 1 pour les 5 |
| Répétition | toutes paires 12 j ; zones « répétées » par centroïdes à 0,003° | 12 j seulement, lacunes visibles, paires disjointes en sensibilité, appariement par recouvrement ≥ 50 % | Z1 sous le seuil dans 8/8 paires ascendantes et 5/5 descendantes |
| Niveau de preuve | promu si concordance optique médiane > 2 | critères fixés à l'avance : ≥ 3 fenêtres appariées et ≥ 3 comparaisons strictes avec IC > 1 | « associé à une observation indépendante », **atteint de justesse (3/3)** |
| Exécution | réécriture de `output/` | `runs/<id>/` puis publication après vérification ; empreintes recalculées à la lecture | 218 entrées et 102 sorties vérifiées |

## Conclusions v1 retirées ou corrigées

1. **« Le périmètre est signalé 1,2 à 3,2 fois plus que le témoin »** — corrigé : contre un taux évalué hors
   calibration, 1,2 à 2,6 fois (paires de 12 j), avec des intervalles qui incluent 1 dans 11 paires sur 13 ; et
   l'excès disparaît au quantile 5 %. Conclusion v2 : faible excès, concentré dans les cohérences les plus basses.
2. **« Sentinel-2 confirme la localisation (×8 à ×64, médiane ×31) »** — corrigé : en comparaison stricte, 3 paires
   seulement ; association nette (IC > 1) mais faible recouvrement absolu (Jaccard 0,09 à 0,17) ; la plupart des
   changements optiques du périmètre ne sont pas signalés par le radar. Le niveau « concordant avec une source
   indépendante » devient « associé à une observation indépendante », au seuil minimal des critères.
3. **« Les parcelles hors polygone sont actives »** — retiré : elles sont plus souvent sous le seuil que le témoin
   dans 10 paires sur 13 ; leur statut d'exploitation est inconnu.
4. **« La zone principale est répétée dans 16 paires »** (v1 docs ; 15 dans le fichier v1) — corrigé : le comptage v1
   additionnait des zones voisines par proximité de centroïdes et pouvait compter deux zones dans la même paire.
   v2 : recouvrement géométrique, Z1 sous le seuil dans les 13 paires de 12 jours.
5. **« Déplacement LOS au niveau du bruit »** — remplacé par un énoncé calculé : les centiles 5–95 du périmètre
   restent dans ±3σ du témoin pour les 15 paires ; aucune interprétation LOS n'est faite.
6. **« Matériau remanié » pour une variation de luminosité** — retiré : « variation de luminosité, sans cause attribuée ».
7. **« Cohérence 1 = surface identique, 0 = surface entièrement changée »** — corrigé dans les trois langues.
8. **Fenêtres de 24 jours** — v1 les mélangeait dans les synthèses ; v2 les résume à part (2 paires).

## Ce qui reste et ce qui manque

Ce qui résiste à tous les contrôles : une zone de 0,31 km² au sud du périmètre (Z1, 32,2156 N, 7,8072 O, sol nu) est
sous le seuil dans toutes les paires de 12 jours des deux orbites, et Sentinel-2 y montre un changement optique dans
les trois comparaisons strictes, avec une signature d'humidification ou d'assèchement (hypothèse). Ce qui manque pour
aller au-delà d'une association : une observation de terrain datée, des produits validés et un périmètre récent.
