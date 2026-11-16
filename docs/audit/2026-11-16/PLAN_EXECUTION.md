# Décisions et plan de réalisation — Benguerir OCP

Point de départ : [audit du 16 novembre 2026](AUDIT.md), branche `feature/benguerir-robustness-v2`, commit `22c6ed9`.
Ce document définit la cible ; les fonctionnalités décrites ci-dessous ne sont pas encore implémentées.

## Décisions prises

1. **Un seul site : la mine de phosphate OCP Benguerir.** Conserver l'historique v2 et créer un nouveau cas/méthode
   pour les nouveaux résultats. La configuration actuelle a son empreinte dans le manifeste : ne pas la modifier
   silencieusement puis prétendre reproduire le même cas.
2. **Produit : étude de changement de surface, vérifiable par zone et par période.** Le résultat attendu est une
   carte de variation radar interprétée à l'aide de références indépendantes. L'activité minière ne sera attribuée
   que lorsque la référence permet cette attribution.
3. **Conserver React/TypeScript, FastAPI, les contrats, le socle raster et les manifestes.** Recomposer les parcours
   autour des cinq livrables de l'utilisateur. Aucune migration de framework n'apporte ici de validation scientifique.
4. **Ajouter d'abord GCOV NISAR.** Utiliser le lot P05023 pour les fenêtres historiques avec optique ; traiter
   P05036 séparément. OPERA/Sentinel-1 reste un complément si GCOV échoue aux contrôles ou pour recouper un résultat.
5. **Garder la faible cohérence comme indice auxiliaire.** Une faible cohérence persistante ne doit pas être vendue
   comme une succession d'excavations. Le nom et la formule de chaque observable doivent être visibles.
6. **Séparer maturité des données, intégrité logicielle et validation de l'étude.** Aucun test vert, DOI ou mot
   `VALIDATED` dans un catalogue n'élève à lui seul le niveau scientifique du cas.

## Ordre d'exécution et critères de passage

### P0 — Geler la référence et corriger la lecture des preuves

Créer une branche de travail, par exemple `feature/benguerir-surface-study`, depuis la v2. Conserver le dossier
d'audit et les fichiers déjà modifiés par l'utilisateur ; ne pas utiliser de reset destructif ni écraser d'autres travaux.

- Garder `cases/benguerir/output/` comme référence historique. Utiliser un nouveau cas tel que
  `cases/benguerir-surface-study/` et des répertoires d'exécution distincts. Éviter la copie des données sources volumineuses.
- Compter séparément `n_radar_comparisons`, `n_unique_optical_pairs` et les groupes qui partagent une acquisition.
  Définir les critères sur ces groupes ; ne pas moyenner deux observations utilisant les mêmes images comme
  deux confirmations indépendantes. Conserver les 3 comparaisons existantes, mais afficher **2 couples optiques**.
- Remplacer une validation fondée seulement sur `evidence.field_truth` par des références structurées avec
  géométrie, dates, source, auteur de la revue, méthode, droits, observable appuyé et limites.
- Étendre le contrat avec des champs facultatifs et versionnés, ou un schéma de nouvelle méthode clairement séparé.
  Les anciens cas doivent rester lisibles. Régénérer les types TypeScript depuis le schéma.

**Passage :** la v2 se charge encore, les deux couples optiques sont comptés correctement, et un simple marqueur
de texte ne peut pas produire une affirmation de validation. Aucun nouveau chiffre de changement n'est encore publié.

### P1 — Périmètre daté et protocole figé

Chercher un contour publiquement documenté OCP/UM6P ; à défaut, préparer une délimitation sur des images contemporaines,
avec journal de digitalisation. La revue humaine ou opérateur reste enregistrée comme attente tant qu'elle n'a pas eu lieu.
Ne pas qualifier une géométrie de « vérifiée » uniquement parce qu'elle est topologiquement valide.

Produire `boundary.geojson` et `boundary_review.json` avec :

- site, opérateur et source documentaire ; date de l'imagerie et date de la revue ; CRS et licence ;
- distinction emprise étudiée, installations, excavations visibles, verses et bassins quand ces classes sont identifiables ;
- état `historical_map`, `draft_interpretation`, `remote_sensing_reviewed` ou `operator_confirmed`, avec preuves ;
- incertitude de position et comparaison d'aire/recouvrement avec OSM 2020 ; absence de revendication de limite légale ;
- zones témoins définies avant examen des résultats, exclusions et contrôle de comparabilité des sols/pentes/usages.

Conserver une zone de contexte et les anneaux existants comme comparateurs. Le recul 1–4 km est une convention
d'analyse, pas une frontière d'influence minière. Les témoins ne sont pas réputés stables sans vérification.

Écrire avant calcul un protocole versionné : périodes, unités, résolution, minimum de couverture par zone,
référence de comparaison, règle de signalement, incertitudes et références réservées à l'évaluation.
La période principale reste juin–octobre 2026 ; une extension octobre–novembre est une analyse distincte.

**Passage :** contour et statut honnêtes, sources lisibles et protocole figé. Si une revue indépendante manque,
continuer le développement et les calculs exploratoires, en gardant la validation du périmètre en attente.

### P2 — Données SAR, changement temporel et qualité

**Accès.** Ajouter un extracteur GCOV distinct, utilisant les outils de lecture partielle existants lorsque compatibles.
Lire gamma-0 HH et HV si présentes, masques, fréquences, résolution, grille, incidence, métadonnées de traitement et
indicateurs de bruit disponibles. Conserver DOI, concept ID CMR, granule ID, URL, dates UTC, CRID, mode et SHA-256.
Une propriété de qualité absente reste `unknown` ; ne pas inventer un masque d'ombre ou de bruit.

Commencer par les deux produits du **16 et 28 août 2026, trace 44 ascendante, cadre 18, P05023**, listés dans
`data_plan.json`. Ils correspondent à une fenêtre déjà confrontée à l'optique. Ce choix sert à intégrer le pipeline,
pas à créer un échantillon de validation indépendant : ces dates ont déjà été examinées dans la v2.
Étendre ensuite au lot homogène pour vérifier la variation habituelle et les périodes réservées à l'évaluation.

Pilote complémentaire P05036 : **25 octobre–6 novembre, trace 23 descendante, cadre 72**. Le 27 octobre ascendant
est isolé dans l'inventaire : ne pas le comparer au descendant comme si la géométrie était la même.
Examiner les modes concernés par les anomalies de calibration avant le 12 novembre et publier les limites applicables.

**Observable.** Pour chaque canal comparable, publier au minimum
`delta_db = 10 * log10(gamma0_after / gamma0_before)`, uniquement pour des valeurs positives et valides aux deux dates.
L'agrégation spatiale s'effectue sur la puissance linéaire avant conversion en dB. Ne pas confondre pas de grille et
résolution effective. Ne pas utiliser les heuristiques de crue/végétation des anciennes recettes comme classificateur minier.

Un seul couple permet une carte descriptive de variation, pas une estimation robuste de l'état habituel. Pour un
signalement par rapport à une référence temporelle, fixer un minimum de dates homogènes et indépendantes dans le
protocole ; sans ce minimum, retourner `insufficient_baseline`. Les intervalles de 12 et 24 jours restent séparés.
Les valeurs C-band OPERA et L-band NISAR ne sont jamais soustraites directement.

**Qualité.** Produire une couche par date et une couche commune par comparaison. Distinguer au moins : observé,
absent, anomalie instrumentale, géométrie non exploitable lorsque documentée, et couverture insuffisante.
Traiter l'eau comme une catégorie/contextualisation motivée selon l'observable, pas comme une preuve automatique
de mauvaise acquisition. La faible cohérence est un signal à étudier : ne pas la supprimer par un seuil LOS.

Exporter les motifs en GeoTIFF, la fraction utile par zone et le masque final exact des statistiques. La carte doit
montrer les zones non observées, y compris pour une paire rejetée. Masquer l'aperçu scientifique de cohérence par
`valid` ; réserver la version brute à une vue technique explicite si elle est conservée.

**Passage :** même paire, même grille, mêmes pixels valides dans calcul, API, carte et exports ; les tests refusent
un mélange CRID/orbite/polarisation incompatible. Une donnée candidate est distinguée d'une donnée téléchargée,
extraite et finalement utilisable. Aucun achat, aucun calcul distant payant n'est nécessaire au périmètre prévu.

### P3 — Évaluation indépendante à la bonne échelle

La comparaison actuelle entre seuil radar et seuil optique est un recoupement entre capteurs. Pour évaluer la
détection de changements visibles, constituer un jeu de référence **avant** de regarder les nouveaux signalements :

1. Définir des unités spatiales à la résolution effective, et des fenêtres compatibles. Séparer zones de calibration,
   de réglage et d'évaluation ; grouper les unités qui partagent images, acquisitions ou événement.
2. Prélever des zones signalées, non signalées et non observables, à l'intérieur et autour de la mine ; ne pas
   évaluer seulement Z1 ou les zones les plus spectaculaires. Enregistrer les probabilités d'échantillonnage.
3. Annoter sur optique datée ou observations de site : changement visible, absence de changement visible, indéterminé,
   en conservant la preuve et le niveau de résolution. L'absence de preuve optique ne devient pas une absence de changement.
4. Faire réviser les annotations sans montrer le résultat radar à l'annotateur. Les références automatisées et
   celles proposées par un agent restent identifiées comme telles, sans simuler une revue humaine indépendante.
5. Rapporter effectifs, couverture, précision/rappel ou métriques par zone quand appropriés, intervalles spatiaux,
   taux d'indétermination et pondération du plan d'échantillonnage. Aucun objectif de précision n'est choisi après
   consultation des résultats ; pas de « 95 % exact » déduit du niveau d'un intervalle de confiance.

Sentinel-2 L2A est conservé avec les masques et conventions de réflectance documentés. Des scènes Landsat/USGS-NASA
peuvent compléter une période après vérification du catalogue, de la résolution et des dates ; leur disponibilité
locale n'a pas été auditée ici. Une image non datée ou un fond web non licencié n'est pas une référence d'évaluation.

Les observations du site demandées, si disponibles, sont limitées et concrètes : contour autorisé, images datées,
calendrier d'opérations sur les zones retenues et informations pluie/arrosage pour expliquer les alternatives.
Préparer cette demande ; ne pas contacter OCP ou d'autres personnes sans instruction d'envoi.

**Passage :** le rapport précise le domaine évalué et les inconnues. L'optique peut étayer un changement de surface
observable à sa résolution ; une attribution opérationnelle précise demande une preuve adaptée. L'absence de terrain
n'empêche pas une étude utile, mais interdit de prétendre avoir validé sur le terrain.

### P4 — Recomposer l'interface et livrer l'étude

Parcours cible : **Site → Changements → Qualité et dates → Comparaison → Conclusion**.
Réutiliser `MapView`, la provenance, le contrat et la gestion FR/EN/AR.

- Site : contour, date et statut de revue, tampon et témoins.
- Changements : images radar avant/après, variation en dB, géométrie et fenêtre ; faible cohérence en complément.
- Qualité : motifs, pixels observables, dates manquantes, granularité de la mesure.
- Comparaison : optique avant/après, références indépendantes et effectifs ; mêmes étendues et dates explicites.
- Conclusion : par zone, ce qui est mesuré, corroboré, attribuable ou indéterminé, puis limites de généralisation.

Livrer un rapport HTML imprimable, les couches GeoTIFF/GeoJSON, les tables, les sources et le manifeste permettant
de remonter de chaque chiffre au produit. Un PDF peut être produit ensuite, avec contrôle du rendu.

**Passage :** données réelles dans l'API et le navigateur, cas historique toujours lisible, FR/EN/AR sur bureau et
390 px, carte et sources à l'impression, états vides explicites, aucun nombre fabriqué pour compléter une section.
Documenter séparément tests logiciels, reproductibilité et résultats de l'évaluation indépendante.

## Simplification du projet

| Conserver au centre | Sortir du parcours principal / différer | Suppression de code éventuelle |
|---|---|---|
| Périmètres, catalogue, accès, masques, raster, ROI, statistiques, provenance, API, carte et exports | LOS non interprétée, vitesse annuelle, décomposition verticale/est-ouest, GOFF, SME2, exposition population/bâtiments, détection de crue/forêt | Seulement après inventaire des imports et maintien des dépendances réellement utilisées |
| Cohérence historique comme élément de contexte | Promesses de danger, production, minerai, volumes, classification minière automatique | Ne pas ajouter ces promesses ; aucune donnée de validation ne les soutient |
| Documentation courante et cas v2 comme référence | Récits v1 devenus obsolètes | Les déplacer vers une archive clairement datée ; conserver provenance et historique Git |

Les recettes génériques peuvent rester dans une surface CLI avancée ou être archivées. Les effacer avant d'avoir
isolé `catalog`, `raster`, `quality` et leurs dépendances n'améliore pas l'étude.

## Conditions honnêtes de livraison

L'agent doit terminer tout le développement réalisable avec les données accessibles. Si le contour récent ou les
références indépendantes n'ont pas été obtenus, il livre la version exploratoire complète et un état de validation
partiel, avec les seules preuves manquantes. Il ne déclare pas l'objectif scientifique « validé » pour fermer la tâche.
Les étapes P0–P4 peuvent progresser sur leurs parties indépendantes ; les conditions de validation restent obligatoires.
