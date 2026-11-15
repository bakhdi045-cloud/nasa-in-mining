# Feuille de route décisionnelle — NASA in Mining

Version 2 — 15 novembre 2026 (v1 : plan initial ; v2 : états après exécution de D0–D6). Ce document est tenu à jour à chaque jalon. Les choix importants et leur
historique sont consignés dans [DECISIONS.md](DECISIONS.md).

Il ne s'agit pas d'un calendrier. Chaque ligne décrit une décision, les preuves qui la fondent, le critère qui
permet de la considérer comme acquise et ce que l'on fait si les observations la contredisent.

Légende des états : **ouvert** (preuves insuffisantes) · **retenu** (choix fait, critère non encore vérifié) ·
**franchi** (critère de passage vérifié) · **partiel** (critère satisfait en partie, manque explicite) ·
**bloqué** (dépend d'une information extérieure) · **réévalué** (choix modifié par les observations).

## Dépendances

```text
D0 question ──► D1 site/périmètre ──► D2 données ──► D3 méthode ──► D4 contrat ──► D5 interface ──► D6 présentation
                     │                    │              │
                     │                    └─► accès Earthdata (bloquant pour les résultats réels, pas pour le code)
                     └─► référence indépendante datée (Sentinel-2) ──► D3 comparaison indépendante
```

Ce qui avance indépendamment des données manquantes : contrat `MiningCase`, API, interface, tests sur données
synthétiques, états « indisponible ». Ce qui ne peut pas avancer sans elles : tout résultat présenté comme réel.

## Tableau des décisions

| ID | Décision | Options | Preuves nécessaires | Choix retenu et justification | Critère de passage | Solution de repli | État |
|---|---|---|---|---|---|---|---|
| D0 | Question minière mesurable | (a) changement du signal radar dans le périmètre ; (b) déplacement LOS des verses et fronts ; (c) détection de minerai, volume, production, rupture | Observable effectivement fourni par les produits ; possibilité de le mesurer dans un périmètre avec une référence | **(a)** : « Entre deux acquisitions NISAR successives de même géométrie, quelles zones du périmètre cartographié présentent une perte de cohérence L-bande anormale par rapport à l'anneau témoin, et ces zones sont-elles retrouvées par l'autre géométrie et par Sentinel-2 ? ». (b) en complément seulement si la cohérence le permet. (c) **exclu** : aucun produit ne l'observe | Question, utilisateur, observable, unités et limites écrits ; résultats chiffrables (km², fraction observable, récurrence, dates) | Si la cohérence est saturée ou inexploitable : se limiter à la couverture et à l'état « non mesurable » | **franchi** (voir § D0) |
| D1 | Site et périmètre | Benguerir (OSM `landuse=quarry`, parcelles OSM, point historique) ; sites alternatifs (Khouribga, Youssoufia) | Polygone sourcé, daté, sous licence réutilisable ; nature du polygone ; couverture radar ; référence indépendante datée | **Benguerir, polygone OSM way 638354631 v3 (2020-02-10), 39,5 km²**, nature « emprise cartographiée d'usage carrière », **pas une concession**. Les 853 parcelles OSM de 2020 (2,4 km² hors polygone) sont une zone annexe. Point/cercle historiques abandonnés | Périmètre documenté (source, date, méthode, précision, droits, limites) dans `docs/BOUNDARY.md` ; couverture GUNW confirmée par téléchargement réel | Si l'emprise 2020 manquait l'activité 2026 (changements concentrés à la frontière) : étendre avec les parcelles ou une emprise optique 2026 documentée, sans la présenter comme officielle | **franchi** pour la question (a) ; **réévalué** : activité observée dans les parcelles hors polygone → vérification « mettre à jour le périmètre » |
| D2 | Données et compatibilité | NISAR GUNW (provisoire P05023) ; NISAR GCOV ; NISAR GUNW validé (V1) ; Sentinel-1 (ESA) ; Sentinel-2 pour référence | Catalogue, accès, téléchargement réel, contenu des couches, géométrie, version, résolution, looks, corrections | **NISAR GUNW PROVISIONAL V1, CRID P05023**, 17 paires (044A/018 : 9 ; 023D/072 : 8), cohérence 20 m (30 looks) et 80 m (208 looks). Lecture à distance de la fenêtre (≈ 27 Mo/produit au lieu de 2,2 Go). **Sentinel-2 L2A** tuile 29SPR pour la référence optique. Aucun GUNW validé (V1) n'existe sur le site à cette date | Produits lus, empreintes SHA-256, grilles identiques par géométrie, métadonnées de version et corrections enregistrées dans `docs/DATA_SOURCES.md` | Si l'accès Earthdata échoue : état « indisponible » explicite, aucun résultat réel ; si GUNW inexploitable : GCOV (rétrodiffusion), à documenter comme autre observable | **franchi** (voir `docs/DATA_SOURCES.md`) ; produits **provisoires** |
| D3 | Méthode | Recette héritée `surface-change` (cercle 5 km, seuil 0,3) ; seuil fixe dans le polygone ; seuil relatif à un témoin par paire ; détection par anomalie temporelle par pixel | Hypothèses des recettes héritées ; distribution de cohérence dans le témoin ; stabilité des grilles ; comparaison indépendante | **Seuil relatif au témoin, par paire** : pixel signalé si sa cohérence est inférieure au quantile 1 % de l'anneau témoin pour la même paire. Sensibilité à 0,5 % et 5 %. Seuil hérité 0,3 non utilisé comme calibration. Contrôle qualité hérité (`quality.split`) réutilisé ; `roi.summarize_raster` réutilisé pour les statistiques dans le polygone | Exécution reproductible (manifeste, empreintes) ; critères de qualité documentés ; taux de signalement du témoin ≈ quantile choisi ; cohérence inter-géométries et avec Sentinel-2 mesurées et rapportées sans surinterprétation | Si le témoin est lui-même perturbé (pluie, labours) : rapporter la paire comme « non interprétable » ; si l'optique ne concorde pas : le dire et rétrograder le niveau de validation | **franchi**, comparaison indépendante **partielle** (10 paires sur 15) — `docs/SCIENTIFIC_VALIDATION.md` |
| D3b | Déplacement LOS en complément | Ne rien publier ; carte LOS par paire référencée au témoin ; série cumulée | Cohérence suffisante, composantes connexes, bruit du témoin, convention de signe | Carte LOS par paire référencée à la médiane du témoin, masquée (cohérence 80 m ≥ 0,3, même composante) ; bruit empirique = σ robuste du témoin. **Signe non vérifié localement**, niveau « calculé » | σ empirique < signal ; signe documenté ; aucune conversion en risque | Ne pas afficher de LOS si σ ≥ signal ou couverture insuffisante | **réévalué** : σ du témoin 0,36–6,8 cm, signal non distinguable → LOS affichée « au niveau du bruit », non interprétée |
| D4 | Contrat et architecture | JSON libre ; modèle Pydantic + schéma JSON ; base de données ; calcul à la demande | Besoin d'une provenance traçable, d'erreurs claires, d'un mode hors ligne | **Modèle `MiningCase` Pydantic v2**, schéma JSON exporté, **FastAPI** servant des résultats précalculés et des couches statiques ; pas de base de données ni de calcul à la demande (inutile pour un cas) | Le JSON produit par le pipeline valide le schéma ; l'API renvoie des erreurs structurées ; le frontend affiche exactement les valeurs du fichier | Si FastAPI n'est pas disponible : servir les fichiers statiques précalculés, le frontend ne dépend que du JSON | **franchi** (tests de contrat) |
| D5 | Interface | Tableau de bord générique ; parcours narratif question → preuves | Capacité à suivre une conclusion jusqu'aux données ; i18n, RTL, accessibilité | **React + TypeScript + Vite + MapLibre**, parcours en cinq étapes, FR/EN/AR (RTL), fond de carte Sentinel-2 local (hors ligne), légendes avec unités, vue imprimable, exports | Un utilisateur peut cliquer d'un chiffre vers la paire, les dates, la couche, la méthode et la source ; inspection des 3 langues et de 3 largeurs | Si MapLibre échoue (WebGL absent) : tableau et images statiques avec coordonnées | **franchi** (e2e bureau et mobile, 3 langues inspectées) ; audit outillé d'accessibilité manquant |
| D6 | Prêt à présenter ? | Présenter comme étude validée ; présenter comme étude de cas calculée avec limites ; ne pas présenter | Contrôles séparés : logiciel, reproductibilité, qualité des données, validation scientifique, lisibilité | Décision prise à la fin, critère par critère | Les valeurs affichées égalent les sorties ; provenance accessible ; limites visibles | Présenter seulement les critères satisfaits, avec la liste de ce qui manque | **décidé** : présentable comme étude de cas calculée et concordante, pas comme étude validée (§ D6) |

## D0 — Question minière (franchi)

- **Utilisateur visé** : analyste en suivi environnemental ou en contrôle des sites miniers (exploitant,
  administration, chercheur) qui doit choisir où et quand vérifier l'activité de surface d'une carrière.
- **Question** : entre deux acquisitions NISAR successives (12 jours, même orbite, même cadre, même CRID), quelles
  zones du périmètre cartographié présentent une perte de cohérence anormale par rapport à l'anneau témoin ?
  Se répètent-elles d'une paire à l'autre, sont-elles retrouvées par l'autre géométrie et par l'optique ?
- **Observable** : la cohérence interférométrique L-bande (sans unité, 0–1) des produits GUNW, à 20 m.
- **Résultats mesurables** : surface signalée (km²) et fraction de la surface observable ; fraction observable ;
  zones connexes ≥ 0,01 km² avec dates ; récurrence par pixel ; taux de signalement du témoin ; concordance
  ascendant/descendant ; concordance spatiale avec le changement Sentinel-2.
- **Décision éclairée** : prioriser des vérifications (examen d'images, visite, relevé topographique) et suivre où
  l'activité se produit d'une fenêtre à l'autre.
- **Limites explicites** : une perte de cohérence dit que la surface a changé, pas pourquoi (excavation, dépôt,
  circulation, humidité, végétation). Aucune détection de minerai, teneur, production, volume, ni prédiction de
  rupture. L'absence de signalement n'est ni « mine inactive » ni « site sûr ».

## Faits, hypothèses et inconnues (au 15 novembre 2026)

| Type | Énoncé |
|---|---|
| Fait vérifié | 17 GUNW provisoires (P05023) couvrent le polygone, du 17 juin au 15 octobre 2026 ; aucun GUNW validé (V1) ; 19 GCOV provisoires + 3 GCOV V1 (P05036). |
| Fait vérifié | Téléchargement réel par lectures partielles avec authentification Earthdata ; empreintes SHA-256 enregistrées. |
| Fait vérifié | Les grilles 20 m et 80 m des deux géométries sont alignées sur les mêmes bords de pixels (EPSG:32629). |
| Fait vérifié | Les indicateurs `geocoding/*CorrectionApplied` des produits valent `True` ; ils concernent le géocodage. La cohérence n'est pas affectée par ces corrections. |
| Hypothèse | La phase dépliée GUNW n'est pas corrigée de l'écran ionosphérique ni de la troposphère (couches fournies séparément) ; la référence locale au témoin retire seulement la composante de grande longueur d'onde. |
| Fait vérifié | Le polygone OSM date de 2020 ; il ne s'agit pas d'une limite légale. |
| Hypothèse | L'anneau témoin 1–4 km, bâti exclu, représente la variabilité de cohérence non minière de la même scène. |
| Hypothèse | Une perte de cohérence locale dans la carrière est dominée par des remaniements de surface. |
| Inconnue | Emprise réelle exploitée en 2026 ; calendrier d'exploitation ; pluies locales entre les dates. |
| Inconnue | Vérité terrain datée du changement ; aucune n'est disponible dans ce projet. |

## Jalons exécutés (résumé)

| Jalon | Décision prise | Preuves utilisées | Critère | Prochaine action |
|---|---|---|---|---|
| D0 | Perte de cohérence relative au témoin, LOS en complément | couches GUNW, nature de l'exploitation | satisfait | — |
| D1 | Benguerir, OSM way 638354631 v3 (2020) + parcelles hors périmètre | historique OSM, Sentinel-2 2026, taux par anneau | satisfait ; périmètre daté | obtenir un périmètre 2026 sourcé |
| D2 | GUNW provisoires P05023, lecture partielle ; Sentinel-2 L2A | CMR, 17 lectures réelles, empreintes, grilles alignées | satisfait ; produits provisoires | relancer avec GUNW validés |
| D3 | seuil quantile 1 % du témoin à 20 m, raccord `roi.summarize_raster` | 15 paires, deux orbites, 10 comparaisons optiques | satisfait ; comparaison partielle | vérité terrain, optique d'automne |
| D4 | `MiningCase` Pydantic + schéma, FastAPI statique | tests de contrat, erreurs JSON | satisfait | — |
| D5 | parcours en 5 étapes, traçabilité de chaque valeur, FR/EN/AR | Vitest, Playwright, captures | satisfait ; audit a11y outillé manquant | audit axe + lecteur d'écran |
| D6 | présenter comme étude de cas calculée | critères séparés ci-dessous | voir § D6 | — |

## D6 — Prêt à être présenté ?

| Critère | Verdict | Preuve |
|---|---|---|
| Fonctionnement logiciel | **oui** | 56 tests Python, 11 Vitest, 2 parcours Playwright, build |
| Reproductibilité | **oui** | deux exécutions, sorties identiques, manifeste avec commit et SHA-256 |
| Qualité des données | **oui, avec réserve** | produits provisoires ; 2 paires écartées et affichées comme non observées |
| Validation scientifique | **non** (concordance seulement) | Sentinel-2 et deux orbites concordent sur la localisation ; aucune vérité terrain, cause inconnue |
| Lisibilité et accessibilité | **oui, avec réserve** | trois langues, RTL, mobile, clavier ; pas d'audit outillé |

Décision : l'application peut être présentée comme **étude de cas calculée dont la localisation des changements
concorde avec une source indépendante**. Elle ne doit pas être présentée comme une étude validée, ni comme une mesure
d'excavation ou de production. Les valeurs affichées sont celles de `case.json`, leur provenance est accessible depuis
chaque valeur, et les limites sont visibles dans l'interface (étape 4).

## Réévaluations

| Décision | Observation | Changement |
|---|---|---|
| D1 | parcelles 2020 hors polygone signalées au-dessus du témoin dans 12 paires sur 15 | zone séparée + vérification « mettre à jour le périmètre » |
| D3 | zone récurrente principale à signature d'humidification | diagnostics optiques et lecture indicative ajoutés |
| D3 | seulement 6 paires comparables avec le filtre nuages de tuile à 10 % | validité mesurée dans la fenêtre, écart 8 jours : 10 paires |
| D3b | bruit LOS du même ordre que les valeurs du périmètre | LOS non interprétée |
| D2 | accès Earthdata absent localement | jeton d'équipe NASA_SAR utilisé sur arbitrage de l'utilisateur |
