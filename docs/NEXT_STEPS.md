# Suite (mise à jour du 16 novembre 2026)

État : l'étude de surface (contrat 3.0) est calculée sur les données accessibles ; la **validation** reste en attente de
preuves externes qu'aucun calcul ne remplace. Ordre :

1. **Annotations indépendantes en aveugle.** Le paquet est prêt : `cases/benguerir-surface-study/output/annotation/`
   (unités de 60 m, images avant/après Sentinel-2 sans résultat radar, modèle CSV). Une personne indépendante remplit
   `annotation_template.csv` (étiquettes `change_visible`, `no_change_visible`, `indeterminate`, `source = human`,
   `blind_to_radar = true`), ajoute `annotation_meta.json` (relecteur, méthode, droits, dates), place les deux fichiers
   dans `cases/benguerir-surface-study/annotations/`, puis relance `study-run`. Seuils : ≥ 30 unités déterminées par
   classe, ≥ 3 groupes indépendants. Sans cela l'état reste `awaiting_annotations`.
2. **Périmètre récent.** Remplir `cases/benguerir-surface-study/boundary/boundary_review_input.json` (relecteur,
   date de revue, date et source de l'imagerie, preuves) pour passer à `remote_sensing_reviewed`, ou la confirmation
   écrite d'un contact OCP/UM6P pour `operator_confirmed`. Le code refuse ces états sans ces champs.
3. **Demande d'observations au site (préparée, non envoyée).** Contour autorisé ; images datées ; calendrier des
   opérations sur Z1 et les zones retenues ; pluie et arrosage aux dates radar (17 juin → 15 octobre 2026). Ne contacter
   OCP ou l'UM6P qu'avec l'accord de la personne qui porte le projet.
4. **RCID des acquisitions.** Le RCID n'est pas dans les métadonnées GCOV : demander à l'ASF / au support NISAR si les
   acquisitions « 4005 / DHDH » de la trace 44 ascendante et 23 descendante font partie des modes dégradés avant le
   12 novembre 2026 (≈ 1 dB). Retraiter avec les produits revalidés (campagne annoncée pour début 2027).
5. **Produits validés sur la période principale** : réinterroger `NISAR_L2_GCOV_V1` et `NISAR_L2_GUNW_V1` ; GCOV validé
   existe seulement à partir du 25 octobre (P05036), à garder dans une analyse séparée.
6. **Optique d'automne** : peu de couples stricts après septembre (nuages aux dates radar) ; ajouter Landsat 8/9 ou
   d'autres images datées après vérification du catalogue, de la résolution et des dates.
7. **OPERA RTC-S1 (bande C)** : inventaire fait (`inventory/OPERA_L2_RTC-S1_V1_dedup.json`) ; télécharger et comparer
   seulement après les points 1–2, bande C contre bande C, jamais soustraite d'une valeur NISAR en bande L.
8. **Accessibilité** : test avec lecteur d'écran (NVDA, VoiceOver) en arabe et en français (non fait).

À ne pas faire avant une référence indépendante : interprétation de la LOS, classificateur minier, quantités
(minerai, teneur, volume, production), danger de digue, vitesse annuelle, déplacement vertical.
