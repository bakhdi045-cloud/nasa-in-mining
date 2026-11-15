# Validation scientifique — cas Benguerir, juin–octobre 2026

Rapport distinct de la validation logicielle. Source des chiffres : `cases/benguerir/output/case.json`
(exécution 20261115T034718Z, commit 9c265f7) et `exports/pairs.csv`.

## Niveau atteint par observable

| Observable | Niveau | Ce qui le soutient | Ce qui manque |
|---|---|---|---|
| Localisation des pertes de cohérence | **concordant avec une source indépendante** | exécution reproductible ; contrôle qualité ; accord ascendant/descendant (Spearman 0,61) ; concordance Sentinel-2 (×7,7 à ×64) | vérité terrain datée ; produits NISAR validés |
| Déplacement LOS | **calculé** | bruit estimé dans le témoin | signe vérifié localement ; GNSS/nivellement ; corrections ionosphère/troposphère |
| Cause des changements | **non calculé** | — | terrain, calendrier d'exploitation |

Aucune grandeur n'est « validée indépendamment ». La concordance optique soutient **où** la surface a changé ; elle
ne valide ni la valeur de cohérence, ni le seuil, ni une quelconque LOS.

## Résultats calculés

15 paires analysées sur 17 (deux paires descendantes, 26 août → 19 septembre, écartées : cohérence médiane ≈ 0,01
et phase plate sur tout le cadre ; ces dates restent **non observées**). Le périmètre est entièrement observable
(fraction 1,0) sur toutes les paires retenues.

| Paire | Orbite | Jours | Seuil τ | Signalé périmètre | Part | Témoin 1–2 km | Témoin 2–4 km | Parcelles hors périmètre | Concordance S2 |
|---|---|---|---|---|---|---|---|---|---|
| 17 juin → 29 juin | 044A | 12 | 0,317 | 1,040 km² | 2,63 % | 0,77 % | 1,09 % | 2,01 % | ×64,1 |
| 29 juin → 11 juil. | 044A | 12 | 0,311 | 1,028 km² | 2,60 % | 0,64 % | 1,14 % | 2,29 % | ×48,7 |
| 11 juil. → 23 juil. | 044A | 12 | 0,331 | 1,143 km² | 2,89 % | 0,68 % | 1,12 % | 1,88 % | ×58,2 |
| 23 juil. → 16 août | 044A | 24 | 0,292 | 1,262 km² | 3,19 % | 0,81 % | 1,07 % | 2,53 % | ×15,1 |
| 16 août → 28 août | 044A | 12 | 0,343 | 1,032 km² | 2,61 % | 0,64 % | 1,14 % | 2,21 % | ×8,0 |
| 28 août → 9 sept. | 044A | 12 | 0,323 | 1,101 km² | 2,78 % | 0,63 % | 1,15 % | 2,81 % | ×7,7 |
| 9 sept. → 21 sept. | 044A | 12 | 0,314 | 1,040 km² | 2,63 % | 0,46 % | 1,21 % | 4,24 % | pas de scène |
| 21 sept. → 3 oct. | 044A | 12 | 0,326 | 1,174 km² | 2,97 % | 0,58 % | 1,17 % | 3,62 % | pas de scène |
| 3 oct. → 15 oct. | 044A | 12 | 0,277 | 0,964 km² | 2,44 % | 0,80 % | 1,08 % | 1,72 % | pas de scène |
| 27 juin → 9 juil. | 023D | 12 | 0,236 | 0,474 km² | 1,20 % | 0,34 % | 1,26 % | 1,22 % | ×50,9 |
| 9 juil. → 21 juil. | 023D | 12 | 0,243 | 0,592 km² | 1,50 % | 0,25 % | 1,30 % | 1,02 % | ×46,8 |
| 21 juil. → 14 août | 023D | 24 | 0,223 | 0,644 km² | 1,63 % | 0,36 % | 1,25 % | 0,95 % | ×13,6 |
| 14 août → 26 août | 023D | 12 | 0,241 | 0,490 km² | 1,24 % | 0,29 % | 1,28 % | 0,87 % | ×8,3 |
| 26 août → 7 sept. | 023D | 12 | — | écartée | — | — | — | — | — |
| 7 sept. → 19 sept. | 023D | 12 | — | écartée | — | — | — | — | — |
| 19 sept. → 1ᵉʳ oct. | 023D | 12 | 0,254 | 0,702 km² | 1,78 % | 0,35 % | 1,26 % | 2,24 % | pas de scène |
| 1ᵉʳ oct. → 13 oct. | 023D | 12 | 0,197 | 0,476 km² | 1,20 % | 0,56 % | 1,17 % | 0,85 % | pas de scène |

Taux du témoin : 1,0 % par construction. Sensibilité (quantiles 0,5 % et 5 %) dans `case.json`.

Répétition (paires de 12 jours) : orbite ascendante, 2,73 km² du périmètre signalés au moins une fois et 1,04 km²
dans au moins la moitié des 8 paires ; orbite descendante, 1,43 km² et 0,39 km² sur 5 paires.

## Lecture proportionnée

1. **Le périmètre change plus que son environnement** dans les 15 paires (1,2 à 3,2 fois le taux du témoin). La part
   signalée est faible (1,2–3,2 % de 39,5 km², soit 0,47–1,26 km² par fenêtre) : l'activité de surface détectable
   est localisée, ce qui est attendu pour une exploitation par bandes.
2. **Les deux orbites désignent les mêmes secteurs** (Spearman 0,61 ; concordance ×51 pour les pixels fréquemment
   signalés ; Jaccard 0,32). Elles diffèrent en niveau : l'orbite descendante (soir) a des seuils plus bas
   (0,20–0,25 contre 0,28–0,34) et signale moitié moins de surface ; l'heure et la géométrie de visée suffisent à
   expliquer cet écart, qui n'est pas interprété comme un changement d'activité.
3. **Sentinel-2 confirme la localisation** : un pixel signalé est 7,7 à 64 fois plus souvent un pixel de changement
   optique (médiane ×31) ; la concordance est plus faible en août (×7,7–8,3), sans explication établie.
4. **Une part importante du signal n'est pas de l'excavation** : la zone la plus récurrente (0,25–0,46 km² près de
   32,215 N, 7,807 O), signalée dans 16 paires sur les deux orbites, a une signature optique d'humidification ou
   d'assèchement dans 5 des 10 paires comparées (ΔMNDWI de ±0,3 à ±0,5), compatible avec un bassin ou une aire
   d'épandage humide. Une perte de cohérence n'y signifie pas un front de taille.
5. **Pas de débordement au contact du polygone** (taux 1–2 km inférieur au taux 2–4 km, qui comprend des cultures),
   **mais** les parcelles minières cartographiées en 2020 hors polygone sont signalées au-dessus du témoin dans
   12 paires sur 15 (jusqu'à 4,2 %) : le polygone de 2020 sous-estime l'emprise active.
6. **LOS** : bruit du témoin de 0,36 à 6,8 cm selon la paire ; percentiles 5–95 du périmètre dans ±5,7 cm. Aucun
   mouvement n'est distingué du bruit à l'échelle d'une paire.

## Explications alternatives

Examinées dans [METHOD.md](METHOD.md) : décorrélation de scène (non : médiane du témoin 0,67–0,78, ΔMNDWI du témoin
−0,035 à +0,021), végétation (non relevée), humidité (oui pour la zone principale), défaut de produit (deux paires
écartées), limite de périmètre (activité hors polygone), géométrie de visée (accord des deux orbites).

## Critère de passage D3

| Critère | État |
|---|---|
| Exécution reproductible | **satisfait** (deux exécutions identiques, manifeste, empreintes) |
| Critères de qualité documentés | **satisfait** (masque produit, contrôle hérité, témoin minimal, grilles identiques) |
| Comparaison indépendante | **partiel** : 10 paires sur 15 ; aucune après le 9 septembre faute de scènes claires |
| Conclusions proportionnées | **satisfait** : localisation concordante ; cause, volume et LOS non conclus |

## Ce qui permettrait d'aller plus loin

Observation de terrain ou calendrier d'exploitation datés ; images très haute résolution aux points proposés ;
GUNW validés (CRID définitif) ; correction ionosphérique (couche fournie) et troposphérique pour la LOS ; point de
contrôle GNSS pour le signe ; périmètre 2026 documenté.
