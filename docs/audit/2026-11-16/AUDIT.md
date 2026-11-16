# Audit de nasa-in-mining — étude OCP Benguerir

Date : 16 novembre 2026. Site confirmé par l'utilisateur : **Benguerir OCP uniquement**.
Guemassa est exclu de cette étude. État audité : `22c6ed951463bdb965a7557d57c19f88ec90c545`.

**Décision : conserver la branche v2 et construire une étude de changement de surface autour de ses acquis.**
Le dépôt constitue une étude exploratoire reproductible sur des données réelles, pas encore une étude de changements
miniers validée. Une réécriture complète ferait perdre une chaîne qui fonctionne. Les travaux prioritaires sont
scientifiques et géographiques avant d'être graphiques.

Documents associés : [plan d'exécution](PLAN_EXECUTION.md), [prompt pour l'agent](PROMPT_AGENT.md),
[preuves locales](local_evidence.json), [catalogue NASA interrogé](catalogue_live.json),
[recalcul comparé](reproducibility.json), [contrôles exécutés](checks.json), [sélection de données](data_plan.json).

## 1. Branches : toute l'histoire disponible est intégrée dans la v2

Lecture de `git branch -avv`, de l'historique, des arbres et des différences, puis vérification directe par
`git ls-remote --heads origin`. Le dépôt est distinct de `NASA_SAR` ; ce dernier n'a pas été modifié.

| Branche | Commit | Disponibilité vérifiée | Apport | Décision |
|---|---|---|---|---|
| `main` | `6a36907` | locale et GitHub | Socle Python, CLI, catalogue, recettes SAR héritées, statistiques sur polygone ; pas de cas réel ni d'interface à ce commit | Conserver comme origine ; ne pas repartir de cette version |
| `feature/benguerir-mining-case` | `1a15171` | locale seulement ; absente des branches actuellement publiées | +7 commits : cas Benguerir, accès aux données, cohérence par polygone, API, interface FR/EN/AR, première étude réelle | Référence historique ; résultats et méthode dépassés par v2 |
| `feature/benguerir-robustness-v2` | `22c6ed9` | locale, branche active et GitHub | +8 commits après v1 : statistiques spatiales, optique corrigée, qualité produit, manifestes, publication vérifiée et interface renforcée | Base retenue pour la suite |

Ces branches sont successives : `main → mining-case → robustness-v2`. Il n'y a pas de travail divergent à fusionner
entre ces trois pointes. GitHub annonce deux branches, dont les SHA correspondent aux références locales.
Cet inventaire porte sur les références locales et celles d'`origin`, pas sur d'éventuels forks ou branches supprimées.

Le commit courant contient 214 fichiers suivis, dont 38 sous `src/`, 27 sous `web/` et 116 sous `cases/`.
Les 16 fichiers hérités déclarés dans `UPSTREAM.json` ont toujours leurs empreintes attendues.

## 2. Couverture du projet

| Ensemble examiné | État et intérêt pour Benguerir |
|---|---|
| `catalog`, `raster`, `quality`, `roi`, `uncertainty`, `config` | Socle à conserver : inventaire local, géoréférencement, qualité, surfaces et configuration indépendante |
| `recipes/`, `analysis.py`, CLI historique | Capacités ponctuelles héritées : LOS, séries, eau, végétation, humidité, offsets. Leur présence ne signifie pas qu'elles sont validées sur la mine |
| `access/`, scripts d'acquisition | Recherche CMR/STAC paginée, recadrage réel, provenance et caches contrôlés. L'extracteur minier actuel télécharge GUNW ; il ne fournit pas encore la chaîne GCOV envisagée |
| `mining/` | Chaîne effective du cas : masques, témoins, seuils, bootstrap spatial, optique, récurrence, conclusions, contrat et exports |
| `api.py`, `contract/` | API locale de lecture des résultats, contrat strict et distinction valeur absente / zéro mesuré / incertitude inconnue |
| `web/` | Carte, dates, provenance, comparaison, limites, FR/EN/AR, mobile et impression ; interface à réorganiser plutôt qu'à remplacer |
| `cases/benguerir/` | Inventaires, périmètre OSM, configuration et résultats versionnés ; données sources recadrées dans `data/`, non versionnées |
| `tests/`, `web/e2e/`, documentation | Bon socle de régression ; tests logiciels et validation scientifique restent deux preuves différentes |

La revue a porté sur les entrées, contrats, traitements actifs, statistiques, accès aux données, exports et parcours.
Elle ne constitue ni une expertise géotechnique, ni une certification de chaque recette héritée.

## 3. État des cinq livrables demandés

| Livrable | Ce qui existe réellement | Ce qui manque pour la cible |
|---|---|---|
| Périmètre vérifié de la mine | Polygone OSM valide géométriquement, 39,548 km², source et date documentées ; témoins 1–4 km et parcelles complémentaires | Révision sur imagerie datée de l'étude, traçabilité de la revue et, si disponible, contour OCP/UM6P. OSM 2020 n'est pas une limite d'exploitation actuelle ni une concession |
| Carte des changements à l'intérieur et autour | Cohérence 20 m, pixels sous un seuil relatif au témoin, récurrence, exports GeoTIFF et GeoJSON ; cartes couvrant aussi les alentours | Mesure temporelle explicite du même observable, masque commun avant/après, cartes intérieures/extérieures et distinction changement / faible cohérence persistante |
| Dates et masque qualité | Dates UTC, orbite/trace/cadre, CRID, masques produit appliqués, deux paires rejetées ; GeoTIFF de signalement avec 255 = non observé | Couche qualité dédiée et export des motifs par pixel, visible aussi sur les fenêtres rejetées ; cohérence affichée masquée ou clairement identifiée comme brute |
| Comparaison indépendante | Sentinel-2 réel, 41 scènes lues, 26 utilisables ; 3 comparaisons strictes, 5 appariements entre orbites | Les 3 comparaisons strictes réutilisent seulement 2 couples optiques. Pas de référence annotée indépendante ni d'observation terrain datée ; couverture optique stricte très incomplète |
| Conclusion sur changements et inconnues | Conclusions calculées et prudentes ; hypothèses alternatives et fiche Z1 ; absence de terrain indiquée | Conclusion par zone, observable et période, fondée sur un changement mesuré et une référence évaluée ; cause minière réservée aux zones où elle est étayée |

**Aucun pourcentage global d'avancement n'est attribué** : le logiciel est fonctionnel, mais les lacunes de validation
ne se compensent pas par le nombre de fonctionnalités terminées.

## 4. Vérifications réalisées pendant cet audit

| Vérification | Observation du 16 novembre |
|---|---|
| Python | 71 tests réussis, 22,973 s ; avertissements de dépréciation |
| Interface | 14 tests Vitest réussis ; TypeScript et construction Vite réussis |
| API + navigateur | 10 parcours Playwright réussis contre le vrai serveur local et le cas enregistré : FR/EN/AR, bureau et 390 px, axe, fichiers et impression |
| Fin des parcours | Les 10 scénarios étaient terminés, mais le processus restait en arrêt du serveur ; arrêt manuel du serveur créé par ce test, puis sortie 0 et `10 passed`. À fiabiliser sous Windows |
| Contrat et fichiers | Contrat valide, aucune référence de sortie manquante ; 218/218 entrées et 102/102 sorties conformes à leurs SHA-256 |
| Géométries | Les quatre géométries du fichier de zones sont valides ; surface recalculée du périmètre : 39,5476395 km² |
| Recalcul scientifique | `case-run --no-publish`, exécution `20261116T105616Z`, 46 s : 102/102 sorties identiques ; contenu scientifique identique hors identifiant d'exécution et manifeste |
| Protection de la référence | Exécution publiée `20261115T150945Z` inchangée ; aucun nouveau produit scientifique publié |

Le recalcul utilise les recadrages réels déjà locaux. Il ne répète pas le téléchargement de chaque HDF5 et ne
constitue pas un nouveau test depuis un clone sans données. Les tests synthétiques restent explicitement des tests.
Les empreintes vérifient l'intégrité locale ; elles ne prouvent ni l'exhaustivité de toutes les données possibles,
ni la justesse physique d'une conclusion. Le catalogue public confirme les identifiants NISAR utilisés.

## 5. Résultat scientifique actuellement défendable

L'étude traite **15 paires sur 17**, entre le 17 juin et le 15 octobre 2026 : 13 intervalles de 12 jours et
2 de 24 jours. Deux fenêtres descendantes impliquant le 7 septembre sont exclues par le masque produit.

Pour les 13 fenêtres de 12 jours, au quantile principal 1 %, le rapport entre fraction sous le seuil dans la mine
et fraction sous le seuil dans le témoin d'évaluation varie de **1,18 à 2,63**, médiane **1,99**.
L'intervalle par blocs est entièrement supérieur à 1 pour **2/13 paires** seulement.
Au quantile 5 %, **0/13** rapports dépassent 1, médiane **0,84**. Il existe donc un excès dans la queue des très faibles
cohérences ; la conclusion n'est pas une généralisation à toute la surface de la mine.

Les trois comparaisons strictes concernent les couples Sentinel-2 **14–29 juin** et **13–28 août**.
Le second couple est utilisé pour une paire radar ascendante et une descendante. Leurs Jaccard sont respectivement
environ **0,095, 0,172 et 0,094**. Un rapport d'association élevé ne signifie pas une forte exactitude de classification.
La concordance entre orbites est utile, mais observe aussi les mêmes propriétés persistantes du terrain.

La fiche **Z1**, environ **0,306 km²**, centrée à **32,21559 N, 7,80722 O**, justifie une revue prioritaire.
Elle ne démontre pas une excavation : son interprétation spectrale évoque une variation d'humidité, qui reste une
hypothèse. Aucun volume extrait, déplacement vertical, dommage ou production OCP n'est démontré.

## 6. Points prioritaires relevés dans le code

1. **L'observable principal ne mesure pas encore le changement temporel demandé.**
   `mining/stats.py:threshold_split` compare chaque paire à un témoin spatial ; `pipeline.py` ne soustrait pas un état
   antérieur du même pixel. Le README le décrit honnêtement. Il faut ajouter un observable temporel et conserver
   la faible cohérence comme couche complémentaire, sans renommer les anciens résultats en « surface changée ».
2. **L'indépendance temporelle de l'optique doit être explicitée.**
   `findings.py:100,165` compte les comparaisons, pas les couples optiques distincts. Le seuil interne 3/3 est atteint
   avec deux références temporelles. Ce n'est pas une disparition de l'association observée ; c'est une limite de
   réplication à corriger avant de renforcer le niveau de preuve.
3. **La qualité n'est pas encore une couche autonome de motifs.**
   `pipeline.py:424` regroupe les causes dans le NoData 255 ; `pipeline.py:485` transmet la cohérence brute au PNG,
   sans appliquer `valid`. Les statistiques sont masquées, mais l'image de cohérence ne partage pas cette garantie.
   Le menu `MapView.tsx` ne propose pas de couche qualité dédiée. Ajouter les motifs et maintenir leur cohérence
   dans la carte, les statistiques et les exports.
4. **Une étiquette ne suffit pas pour enregistrer une validation indépendante.**
   `contract.py:412` exige le texte `evidence.field_truth` pour autoriser `independently_validated`, sans objet de
   référence daté, géolocalisé et évalué associé. Le pipeline actuel n'attribue pas abusivement ce niveau ; la future
   évolution doit exiger les preuves structurées, pas seulement le marqueur.
5. **La sélection des produits reste spécifique au prototype.**
   `pipeline.py:193` est limité à GUNW et au CRID de configuration ; `fetch_benguerir_nisar.py` n'extrait que les
   GUNW provisoires. GCOV doit avoir son propre accès et ses tests de compatibilité. Changer un nom de collection
   dans la configuration ne suffit pas.
6. **Les intervalles statistiques sont conditionnels aux choix du protocole.**
   `bootstrap_ratio` rééchantillonne les blocs d'indicateurs déjà seuillés, sans recalibrer le quantile à chaque tirage.
   Ce bootstrap ne couvre donc pas toutes les incertitudes de calibration, géométrie, choix de témoin et interprétation.
   Les sensibilités existantes doivent être conservées et leur domaine expliqué.

Les corrections v2 sur le taux réellement mesuré du témoin, la séparation calibration/évaluation, SCL 2,
la pagination, les scènes absentes, les intervalles de 24 jours et les manifestes optiques sont présentes.
Il ne faut pas relancer l'agent sur les défauts historiques comme s'ils étaient encore tous ouverts.

## 7. Données publiques vérifiées et décision d'utilisation

Requête NASA CMR du **16 novembre 2026, 10:55 UTC**, sur l'emprise actuelle mine + témoins,
du **1er juin au 16 novembre 2026**. Les comptes sont ceux de cette requête, pas une promesse de couverture globale.

| Collection | Entrées CMR | Décision |
|---|---:|---|
| `NISAR_L2_GUNW_PROVISIONAL_V1` | 17 | Conserver le lot existant comme référence exploratoire reproductible |
| `NISAR_L2_GUNW_V1` | 0 | Ne pas promettre un remplacement validé disponible sur cette zone et cette période |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | 19 | Priorité pour ajouter la variation de rétrodiffusion aux fenêtres déjà comparables à Sentinel-2, après contrôle de qualité |
| `NISAR_L2_GCOV_V1` | 3 | Pilote séparé P05036 : desc. 25 octobre / 6 novembre ; asc. 27 octobre isolée |
| `OPERA_L2_RTC-S1_V1` | 148 | Complément C-band possible ; dédoublonner versions et bursts avant de compter les acquisitions, puis vérifier la couverture utile |

Les empreintes géographiques CMR des 22 GCOV couvrent le polygone OSM d'étude. Cela ne garantit ni validité des pixels,
ni couverture utile du témoin, ni téléchargement réussi. Aucun GCOV/OPERA n'a été téléchargé ou analysé par cet audit.
Les candidats et identifiants exacts sont dans [data_plan.json](data_plan.json).

GCOV fournit une rétrodiffusion calibrée avec correction radiométrique du terrain ; la grandeur à comparer est la
puissance gamma-0 du même canal et d'une géométrie compatible. [Guide GCOV ASF](https://nisar-docs.asf.alaska.edu/gcov/).
OPERA est un produit NASA/JPL dérivé du radar **Sentinel-1 ESA/Copernicus**, pas un instrument NASA.
[Guide OPERA ASF](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/).

Les collections NISAR « VALIDATED » décrivent la maturité du produit, pas la validation de cette étude minière.
ASF signale des différences entre CRID et des problèmes de calibration pour certains modes avant le 12 novembre.
Les candidats P05036 ci-dessus précèdent cette date : vérifier le mode et les anomalies applicables, ne pas mélanger
automatiquement P05023/P05036, ni des acquisitions de part et d'autre d'une évolution de calibration.
[Notes officielles P05036](https://hyp3-docs.asf.alaska.edu/nisar-docs/release-notes/).

La lacune instrumentale fin juillet–début août est documentée par ASF ; elle ne doit pas devenir une interpolation
présentée comme une observation. [Anomalies connues](https://hyp3-docs.asf.alaska.edu/nisar-docs/nisar-known-issues/).

OCP confirme que Benguerir appartient au site de Gantour et accueille un Living Lab avec l'UM6P. Cela appuie le choix
du site et d'un interlocuteur de validation, sans fournir son périmètre détaillé.
[Source OCP](https://www.ocpgroup.ma/fr/nos-activites/operations-industrielles).

La [page Resources fournie](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/?tab=resources)
n'a pas pu être récupérée : erreurs du navigateur de recherche puis de certificat TLS par deux clients locaux.
La liste exacte de cet onglet n'est donc **pas certifiée par cet audit**. Les sources NASA/ASF ci-dessus ont été
consultées directement. Vérifier l'onglet avant une soumission au défi ; ne pas inventer son contenu.

## 8. Ce qui a été exécuté, ce qui reste à l'autre agent

Exécuté : audit des branches, lecture du projet, recherche des sources primaires, contrôle CMR réel, tests,
vérification des empreintes, recalcul scientifique sans publication, décisions, sélection de produits et dossier de reprise.
Le script [audit_study_readiness.py](../../../scripts/audit_study_readiness.py) rend les preuves locales et CMR reproductibles.

À exécuter : nouvelle version ciblée du produit, contour révisé, extraction GCOV, mesure temporelle, couche qualité,
jeu de références indépendant, évaluation et rapport final. Ces travaux sont détaillés dans le plan et le prompt.
Aucun module de production n'a été supprimé ou réécrit dans cet audit ; la référence scientifique v2 reste disponible.
