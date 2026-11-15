# Journal des décisions

Chaque entrée indique la décision, les preuves, les options écartées et ce qui la ferait réviser. Les décisions
réversibles ont été prises sans arbitrage ; celles qui en ont demandé un sont signalées. Voir la feuille de route
[ROADMAP_DECISIONS.md](ROADMAP_DECISIONS.md) pour l'état des critères de passage.

## DEC-01 — Question : perte de cohérence relative au témoin (D0)

- **Choix** : mesurer où et quand la cohérence L-bande d'une paire GUNW tombe, dans le périmètre, sous le niveau
  bas de l'anneau témoin de la même paire. Le déplacement LOS est un complément, pas le cœur de l'étude.
- **Preuves** : les GUNW fournissent la cohérence à 20 m (30 visées) et 80 m (208 visées) ; une exploitation à ciel
  ouvert remanie sa surface en continu, ce qui décorrèle le signal entre deux passages de 12 jours.
- **Écarté** : minerai, teneur, production, volume (aucun observable) ; prédiction de rupture (GOFF absent et
  non pertinent sans modèle géotechnique) ; « mine active / inactive » (une absence de signalement ne le prouve pas).
- **Réviser si** : la cohérence de fond était trop basse pour qu'un remaniement soit distinguable (non observé :
  médiane du témoin 0,67–0,78 sur les paires retenues).

## DEC-02 — Site Benguerir, périmètre OSM way 638354631 (D1)

- **Choix** : polygone `landuse=quarry` d'OpenStreetMap, version 3 du 10 février 2020, 39,55 km² (calcul en
  EPSG:32629). Nature déclarée : emprise cartographiée d'usage « carrière », pas une concession.
- **Preuves** : historique OSM (création 2018, mises à jour 2020 sur imagerie Esri World Imagery, commentaires
  « Mise à jour zone laverie OCP Ben Guerir », « OCP mine ») ; superposition visuelle sur Sentinel-2 du
  1ᵉʳ novembre 2026 : les panneaux d'exploitation visibles sont dans le polygone, sauf des bandes à l'est.
- **Écarté** : le point historique (32.25825, -7.82355) et le cercle de 5 km de la recette héritée ; une limite
  de concession (aucune source publique réutilisable trouvée).
- **Complément** : 853 parcelles OSM `landuse=industrial` nommées P1S/P2/P4/P5/P7… (2020, `source=knowledge`) dont
  2,39 km² sont hors du polygone : analysées séparément (zone « parcelles hors périmètre »).
- **Réviser si** : les signalements se concentraient au contact du polygone. Observé : le taux de l'anneau
  1–2 km (médiane 0,58 %) est inférieur à celui de l'anneau 2–4 km (1,17 %), mais les parcelles hors périmètre
  sont signalées au-dessus du témoin dans 12 paires sur 15 → la vérification « mettre à jour le périmètre » est
  proposée. Voir [docs/BOUNDARY.md](docs/BOUNDARY.md).

## DEC-03 — Produits NISAR GUNW provisoires, lecture partielle (D2)

- **Choix** : collection `NISAR_L2_GUNW_PROVISIONAL_V1`, CRID P05023, version produit 1.0.11, 17 paires
  (044A/F018 : 9 ; 023D/F072 : 8). Lecture HTTP par plages de la seule fenêtre d'étude (17,2 × 21,2 km),
  25–31 Mo par produit au lieu de 1,9–2,4 Go ; aucun rééchantillonnage.
- **Preuves** : recherche CMR du 15 novembre 2026 ; aucun granule `NISAR_L2_GUNW_V1` (validé) sur le site ;
  lecture réelle réussie des 17 produits avec empreintes SHA-256 ; grilles 20 m et 80 m alignées sur les mêmes
  bords de pixels pour les deux géométries.
- **Accès** : Earthdata requis (vérifié : HTTP 401 sans identifiant). **Arbitrage utilisateur** : utiliser le jeton
  d'équipe présent dans NASA_SAR ; il a été copié, sans être affiché, dans `.earthdata_token` (ignoré par Git),
  et NASA_SAR n'a pas été modifié.
- **Écarté pour cette version** : GCOV (rétrodiffusion, 19 provisoires + 3 V1) — observable différent, non
  nécessaire pour la question ; Sentinel-1 — NISAR couvre le site et la question.
- **Réviser si** : des GUNW validés (CRID P05036 ou suivant) couvrent le site → relancer (vérification N_validated).

## DEC-04 — Cohérence 20 m comme grille d'analyse (D3)

- **Choix** : couche `wrappedInterferogram/HH/coherenceMagnitude` (20 m, 6 × 5 visées) et son masque.
- **Pourquoi** : les fronts et bandes d'exploitation mesurent de quelques dizaines à quelques centaines de mètres ;
  à 80 m une zone de 0,01 km² ne fait que 1,6 pixel. Le biais d'estimation à 30 visées (≈ 0,16 pour une cohérence
  nulle) est accepté car le seuil est relatif au témoin de la même grille.
- **Conservé à 80 m** : contrôle qualité hérité (`quality.split`) et LOS (phase dépliée, 208 visées).

## DEC-05 — Seuil relatif au témoin (quantile 1 %) plutôt que seuil hérité (D3)

- **Choix** : pour chaque paire, seuil = quantile 1 % de la cohérence valide de l'anneau témoin. Sensibilité
  rapportée pour 0,5 % et 5 %.
- **Pourquoi** : le seuil hérité 0,3 (perte de cohérence de `damage.py`) a été calibré sur 044/17 pour des
  événements, sur des cercles aléatoires, pas pour une carrière ; un seuil relatif s'adapte à la décorrélation de
  scène (humidité, saison) et donne un taux de fausse alerte explicite dans le témoin. Les seuils observés vont de
  0,197 à 0,343 : un seuil fixe aurait signalé des fractions très différentes selon la géométrie.
- **Limite** : ce n'est pas une probabilité ; le témoin contient des cultures et pistes.

## DEC-06 — Anneau témoin 1–4 km, bâti exclu (D3)

- **Choix** : anneau entre 1 et 4 km du polygone, moins les zones OSM résidentielles, industrielles (dont les
  parcelles minières), militaires (base aérienne), universitaires, eau, autres carrières, avec une marge de 100 m :
  146,5 km².
- **Pourquoi** : même scène, même géométrie, même date ; 1 km d'écart pour limiter la contamination par l'exploitation
  et le flou des fenêtres de cohérence ; 4 km pour rester sur le même plateau. Découpage 1–2 km / 2–4 km pour tester
  un débordement de l'activité.

## DEC-07 — Raccordement polygone ↔ traitements hérités (D3)

- `roi.summarize_raster` est réutilisé sur le GeoTIFF des pixels signalés de chaque paire : surface observée et
  surface signalée doivent égaler le calcul interne (sinon l'exécution échoue). Les deux ont été égaux pour les 15 paires.
- `damage.analyze` (cercle de 5 km) n'est pas utilisé : il répond à une autre question (événement ponctuel).
- `catalog`, `quality`, `wavelength`, `displacement.los_cm_full`, `uncertainty.robust_sigma`, `raster._colormap`
  sont réutilisés sans modification (empreintes `UPSTREAM.json` inchangées).

## DEC-08 — Référence indépendante : Sentinel-2 L2A (D3)

- **Choix** : scènes de la tuile 29SPR (Earth Search, AWS Open Data), encadrant chaque fenêtre radar à 8 jours au plus,
  ≥ 90 % de pixels valides (SCL) dans la fenêtre. Changement optique = norme L2 sur 6 bandes ; seuil = quantile 99 %
  du témoin ; concordance = P(changement optique | signalé radar) / P(changement optique | non signalé).
- **Ce que cela valide** : la localisation des changements de surface. **Ne valide pas** : la valeur de cohérence,
  la LOS, la cause.
- **Ajout après observation** : la plus grande zone signalée (≈ 0,25–0,46 km² près de 32,215 N, 7,807 O) présente
  une forte variation de MNDWI (humidification/assèchement) : des diagnostics optiques (ΔNDVI, ΔMNDWI, Δluminosité)
  et une lecture indicative ont été ajoutés pour examiner les explications alternatives.

## DEC-09 — LOS : calculée, non interprétée (D3b)

- **Choix** : LOS par paire (convention documentée, signe non vérifié localement), référencée à la médiane du témoin
  dans la même composante connexe ; σ empirique = σ robuste du témoin. Pas de correction ionosphérique/troposphérique.
- **Observé** : σ de 0,36 à 6,8 cm selon la paire ; les 5ᵉ–95ᵉ centiles du périmètre restent dans ±5,7 cm. Le signal
  n'est pas distinguable du bruit à l'échelle d'une paire → présenté comme « au niveau du bruit », aucune conclusion.

## DEC-10 — Contrat `MiningCase` et architecture (D4)

- Pydantic v2 + schéma JSON versionné (`contract/mining_case.schema.json`), FastAPI en lecture seule sur résultats
  précalculés, React/TypeScript/Vite, MapLibre 6 avec fond Sentinel-2 local (hors ligne), i18n maison FR/EN/AR.
- Pas de base de données ni de calcul à la demande : un cas, des fichiers, une reproduction par `case-run`.
- Les phrases de résultats sont composées par l'interface à partir de champs structurés : un chiffre affiché est le
  chiffre du fichier.
- Couches : PNG reprojetés en EPSG:3857 (plus proche voisin) pour un placement exact par MapLibre ; les aperçus de
  cohérence (≈ 12 Mo) sont régénérés localement et non versionnés.

## DEC-11 — Interface : parcours en cinq étapes et traçabilité (D5)

- Question → site et données → observations → qualité et preuves → vérifications suivantes. Chaque valeur mesurée
  est un bouton qui ouvre sa chaîne de provenance (valeur, unité, incertitude, paire, granule, DOI, fichiers SHA-256,
  couche cartographique).
- Fond OSM en option seulement (en ligne) ; le mode par défaut ne fait aucune requête externe (vérifié en e2e).

## Historique

| Date | Décision | Changement |
|---|---|---|
| 2026-11-15 | DEC-03 | Accès Earthdata : jeton d'équipe NASA_SAR utilisé sur instruction de l'utilisateur. |
| 2026-11-15 | DEC-08 | Filtre nuages de tuile relevé de 10 % à 60 % (validité mesurée dans la fenêtre) et écart maximal 6 → 8 jours : 10 paires comparables au lieu de 6. |
| 2026-11-15 | DEC-08 | Ajout des diagnostics optiques après observation d'une zone d'humidification récurrente. |
| 2026-11-15 | DEC-02 | Parcelles hors périmètre analysées séparément ; vérification « mettre à jour le périmètre » ajoutée. |
