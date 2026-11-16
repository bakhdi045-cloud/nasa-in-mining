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

## Itération 2 (robustesse)

### DEC-12 — Observable : faible cohérence relative au témoin
Le détecteur compare chaque pixel au témoin de la même paire ; il ne mesure pas de baisse du même pixel. « Baisse » et
« perte supplémentaire » sont réservées à une comparaison temporelle explicitement calculée (non faite).

### DEC-13 — Calibration et évaluation séparées, intervalles par blocs
Damier de blocs de 1 km dans chaque témoin : quantile sur une moitié, taux sur l'autre. Bootstrap par blocs de 1 km
(500 m et 2 km en sensibilité) d'après l'autocorrélation mesurée (0,02 à 1 km). Le profil 1 % est conservé comme
profil historique ; 0,5 % et 5 % sont toujours publiés. Constat : à 5 %, le périmètre ne dépasse plus le témoin.

### DEC-14 — Témoins multiples documentés
Anneau 1–4 km (principal), anneau 2–4 km, anneau « sol nu » et anneau « cultures » (WorldCover 2021). Le périmètre est
à 66 % « sol nu » contre 12 % dans l'anneau : le témoin « sol nu » est le plus comparable ; il donne un écart plus fort.

### DEC-15 — Radiométrie Sentinel-2 et masque
Réflectance = DN/10000 (vérifié contre Planetary Computer : écart de 1000 DN). SCL 2 exclu, SCL 7 douteux (en
sensibilité). Couverture claire mesurée dans les zones, sans filtre de nuages de tuile.

### DEC-16 — Comparaisons optiques stricte et exploratoire séparées
Stricte ≤ 3 jours (test conservateur, pas une garantie de simultanéité), seule utilisée par les critères ;
exploratoire ≤ 8 jours, affichée à part. Toujours avec table 2 × 2, proportions absolues, Jaccard et IC.

### DEC-17 — Critères de niveau de preuve fixés avant l'exécution réelle
« Recoupé entre orbites » : ≥ 3 fenêtres appariées avec IC du rapport > 1 ; « associé à une observation
indépendante » : en plus ≥ 3 comparaisons strictes avec IC > 1 ; « validé » : impossible sans terrain (refusé par le
contrat). Résultat : 5/3 et 3/3, atteint au minimum.

### DEC-18 — Contrôles qualité séparés et masque produit
Le contrôle de cohérence lit le masque NISAR (chiffres de sous-fauchée) : l'acquisition du 2026-09-07 est déclarée
invalide par le produit, ce qui écarte deux paires. Le contrôle de phase hérité ne sert qu'à la LOS.

### DEC-19 — Exécutions isolées et publication vérifiée
Chaque exécution écrit dans `runs/<id>/`, vérifie contrat, fichiers et empreintes, puis remplace `output/`. Les caches
NISAR et Sentinel-2 ne sont réutilisés qu'avec les mêmes paramètres et des empreintes intactes.

### DEC-20 — Démonstration versionnée
Les aperçus de cohérence (64 niveaux, environ 0,6 Mo chacun) sont versionnés : le cas publié (environ 14 Mo)
fonctionne après clonage, sans `data/` ni jeton.

### DEC-21 — Étude de surface sur GCOV, nouveau contrat séparé (16 novembre 2026)
Observable principal : Δγ⁰ HH en dB sur la puissance linéaire à 20 m, protocole figé avant les résultats
(`cases/benguerir-surface-study/protocol.json`). Nouveau contrat 3.0 et nouveau cas ; la v2 (contrat 2.x) reste lisible et
inchangée. La faible cohérence GUNW devient un contexte, jamais renommée « changement de surface ».

### DEC-22 — Pas de signalement sans référence temporelle
Un couple seul est descriptif. Le signalement exige ≥ 3 couples homogènes de même durée sans acquisition commune ;
sinon `insufficient_baseline`. Les durées de 12 et 24 jours, les CRID, les traces et les orbites ne sont jamais mêlés.

### DEC-23 — Appui optique compté par couple Sentinel-2 distinct
Les 3 comparaisons strictes de la v2 reposent sur 2 couples optiques : le critère « associé à une observation
indépendante » compte désormais les couples distincts (≥ 3). Les cas 2.0 sont relus avec ce décompte calculé à la lecture.

### DEC-24 — Une étiquette ne vaut pas une validation
`independently_validated` exige des références structurées effectives (relecteur indépendant, aveugle au radar, méthode,
droits, dates, unités géolocalisées, effectifs, probabilités d'échantillonnage, métriques). Les annotations d'un agent ou
d'un algorithme sont comptées à part et n'étayent rien. Un état de périmètre « revu » exige relecteur, dates et preuves.

### DEC-25 — HV secondaire, HH principal
En HV la puissance médiane est à environ 3 dB du plancher de bruit et le produit n'applique pas la correction du bruit :
les cellules à moins de 2 × le plancher sont exclues et comptées, pas interprétées.

### DEC-26 — Qualité par pixel avec raisons
Bits : hors acquisition, non focalisé, anomalie instrumentale, valeur invalide, plancher de bruit, sous-pixels
insuffisants, date indisponible. Aucun masque d'ombre ou de repli inventé. Les fenêtres rejetées gardent leur couche.

### DEC-27 — Précautions de calibration avant le 12 novembre 2026
Le RCID n'est pas dans les métadonnées GCOV : l'applicabilité du résidu d'environ 1 dB (modes DH 40M05N) ne peut pas être
vérifiée ; elle est affichée comme limite. Le pilote P05036 est analysé à part.

### DEC-28 — OPERA en inventaire seulement
148 granules (88 couples rafale-date, 44 dates) dédoublonnés ; ni téléchargement ni calcul ; bande C jamais soustraite de la
bande L.

| Date | Décisions | Changement |
|---|---|---|
| 2026-11-15 | DEC-12 à DEC-20 | itération de robustesse ; conclusions v1 corrigées (voir docs/COMPARISON_V1_V2.md) |
| 2026-11-16 | DEC-21 à DEC-28 | étude de surface GCOV, contrat 3.0, références indépendantes (protocole), périmètre en attente de revue |
