# Méthode v2 — faible cohérence relative au témoin

Code : [`src/nasa_in_mining/mining/`](../src/nasa_in_mining/mining/) (`pipeline.py`, `stats.py`, `optical.py`,
`findings.py`, `coherence_change.py`, `contract.py`, `export.py`). Paramètres :
[`cases/benguerir/case_config.json`](../cases/benguerir/case_config.json). Version de méthode : 2.0.0.

## Observable

Pour une paire GUNW, un pixel du périmètre est retenu quand sa cohérence (couche 20 m, 6 × 5 visées) est
**plus faible que le quantile q de la cohérence d'un témoin de la même paire**. C'est une *faible cohérence relative
au témoin*. Ce n'est pas une baisse par rapport à un état antérieur du même pixel (aucune comparaison temporelle de ce
type n'est calculée), ni une proportion de surface changée.

La cohérence mesure la ressemblance des deux échos radar d'un pixel. Elle baisse quand la réponse de la surface varie
entre les deux dates (remaniement, humidité, végétation) ; elle dépend aussi du bruit (signal faible, nombre de visées :
le biais d'estimation vaut environ 0,16 pour une cohérence nulle à 30 visées), de la géométrie de visée (pentes, ombre,
repliement) et des propriétés propres de la surface.

## Chaîne

1. **Import et intégrité** — index par `catalog` (CRID P05023 seul) ; chaque fichier lu est haché à la lecture et
   comparé à l'empreinte déclarée par sa provenance (extracteur v2 : clé de cache emprise × couches × version) ;
   un écart arrête l'exécution. La description du masque contenue dans chaque produit est comparée à la disposition
   décodée (bits 0–7 : chiffres eau / sous-fauchée de référence / sous-fauchée secondaire ; bits 8–15 et 16–23 :
   anomalies RSLC).
2. **Contrôles distincts** — *cohérence* : part valide, chiffres de sous-fauchée du masque, cohérence médiane (≥ 0,15)
   dans le périmètre et le témoin ; *phase* (LOS seulement) : `quality.check` hérité (phase plate, cohérence 80 m).
   Les pixels portant un bit d'anomalie sont exclus (aucun n'a été rencontré dans les 17 produits).
3. **Grille** — grille 20 m du premier produit ; toute couche d'une autre grille donne `incompatible_grid`, sans
   rééchantillonnage.
4. **Témoins** — anneau 1–4 km (principal), anneau 2–4 km, anneau ∩ « sol nu / végétation clairsemée » et anneau ∩
   « cultures » (ESA WorldCover 2021). Chaque témoin est coupé en damier de blocs de 1 km : moitié de *calibration*
   (seuil) et moitié d'*évaluation* (taux). Le taux de calibration ≈ q par construction et n'est pas une validation.
5. **Profils** — 4 témoins × 3 quantiles (0,5 %, 1 %, 5 %). Profil principal : anneau, 1 % (profil historique de la v1).
   Le seuil n'est jamais choisi pour augmenter le nombre de signalements.
6. **Statistiques** — surfaces observée et sous le seuil, fractions, cohérence médiane, pour le périmètre, les
   parcelles hors périmètre, le témoin et les anneaux 1–2 / 2–4 km ; recoupement obligatoire avec
   `roi.summarize_raster`.
7. **Incertitude statistique** — bootstrap par blocs carrés (2000 rééchantillonnages, intervalle percentile 95 %) de la
   part du périmètre et du rapport au taux évalué (blocs du périmètre et du témoin rééchantillonnés indépendamment).
   Taille de bloc : 1 km, choisie sur l'autocorrélation mesurée de l'indicateur dans le témoin (0,37 à 20 m ; 0,12 à
   100 m ; 0,07 à 250 m ; 0,04 à 500 m ; 0,02 à 1 et 2 km). 500 m et 2 km sont publiés en sensibilité. Avec moins de
   5 blocs, l'intervalle n'est pas estimé et la raison est donnée.
8. **Sensibilités séparées** — seuil (quantiles), témoin (quatre témoins), périmètre (−1 pixel, +1 pixel, + parcelles
   OSM 2020), stabilité des zones (Jaccard entre quantiles, part des zones conservées à 0,5 %).
9. **Zones** — composantes 8-connexes ≥ 0,01 km². Deux zones de paires différentes sont « la même » seulement si elles
   partagent au moins la moitié des pixels de la plus petite.
10. **Répétition** — paires de 12 jours d'une même orbite seulement ; nombre d'observations par pixel publié ;
    lacunes listées ; seuil « au moins la moitié des paires » appliqué si ≥ 3 observations ; sensibilité sur paires
    sans acquisition commune ; Jaccard des paires voisines (acquisition partagée) comparé à celui des paires à deux
    pas, pour repérer l'effet d'une acquisition particulière.
11. **Orbites** — appariement un à un des paires de 12 jours par plus grand recouvrement de fenêtre (≥ 6 jours) ;
    table 2 × 2 sur les pixels du périmètre valides dans les deux, rapport avec IC, Jaccard.
12. **Sentinel-2** — scène utilisable si ≥ 90 % de pixels clairs (SCL 4, 5, 6) dans le périmètre et ≥ 80 % dans le
    témoin. Comparaison **stricte** : scènes à ≤ 3 jours de chaque date radar ; **exploratoire** : ≤ 8 jours, séparée.
    Changement optique = ‖Δρ‖₂ sur 6 bandes (réflectance = DN/10000), seuil = quantile 99 % de la moitié de
    calibration du témoin ; domaine commun = périmètre valide radar ∩ clair dans les deux scènes (≥ 80 % du
    périmètre). Publiés : table 2 × 2, P(optique | radar), P(optique | non radar), rapport avec IC par blocs, Jaccard,
    part des changements optiques couverte par le radar, rapport avec SCL 7 inclus. Hypothèses spectrales par pixel
    (règles simples non calibrées) : |ΔMNDWI| ≥ 0,2 et ≥ 2|ΔNDVI| → humidification/assèchement ; |ΔNDVI| ≥ 0,1 →
    végétation ; |Δluminosité| ≥ 0,03 → variation de luminosité ; sinon faible.
13. **Fiches de vérification** — pixels sous le seuil dans au moins la moitié des paires observées (≥ 3) des deux
    orbites, composantes ≥ 0,01 km² : observation, paires, comparaisons optiques strictes, hypothèses alternatives,
    informations à recueillir. Aucun score de danger.
14. **LOS** — calculée (convention documentée, signe non vérifié, sans correction atmosphérique), référencée au
    témoin ; publiée comme σ du témoin et centiles du périmètre ; **non interprétée**.
15. **Conclusions et niveaux** — `findings.py` : direction des énoncés calculée ; niveaux : *calculé* → *recoupé entre
    orbites* (≥ 3 fenêtres appariées dont l'IC du rapport dépasse 1) → *associé à une observation indépendante*
    (en plus, ≥ 3 comparaisons strictes dont l'IC dépasse 1) → *validé indépendamment* (impossible sans observation de
    terrain enregistrée, refusé par le contrat). Ces critères ont été fixés avant l'exécution sur les données réelles.
16. **Publication** — l'exécution écrit dans `cases/<cas>/runs/<id>/`, vérifie le contrat, la présence et l'empreinte
    de chaque fichier référencé, puis remplace `cases/<cas>/output/`. `processing.status` = *failed* si une étape requise
    échoue, *partial* si une étape facultative manque ou si une paire n'est pas analysée, *complete* sinon.

## Ce que la méthode ne fait pas

Elle ne mesure pas de baisse temporelle d'un même pixel, n'attribue pas de cause, ne mesure ni profondeur ni volume,
n'utilise pas Sentinel-2 comme vérité terrain, n'interprète pas la LOS et ne qualifie jamais un pixel non signalé de stable.
