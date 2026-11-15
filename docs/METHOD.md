# Méthode — perte de cohérence relative au témoin

Implémentation : [`src/nasa_in_mining/mining/`](../src/nasa_in_mining/mining/) (`pipeline.py`, `coherence_change.py`,
`export.py`, `contract.py`). Paramètres : [`cases/benguerir/case_config.json`](../cases/benguerir/case_config.json).

## Chaîne

1. **Import** — index des produits par le module extrait `catalog` (CRID P05023 seulement : jamais de mélange de
   versions) ; provenance (`provenance.json`, SHA-256) de chaque couche.
2. **Contrôles** — `quality.split` hérité (phase plate σ < 0,001 rad, cohérence médiane < 0,15) sur les couches 80 m ;
   chaque couche 20 m doit avoir exactement la grille d'analyse (forme, CRS, transformée), sinon statut
   `incompatible_grid` (aucun rééchantillonnage implicite).
3. **Grille** — cohérence 20 m (EPSG:32629). Les zones sont rasterisées par centre de pixel.
4. **Masque de qualité** — pixel valide si cohérence finie et masque produit valide : chiffre des sous-fauchées de
   référence et secondaire non nuls, chiffre « eau » nul. Les bits d'anomalie (8–23) sont décodés mais ne masquent pas.
5. **Calcul** — pour chaque paire : seuil τ = quantile 1 % de la cohérence valide de l'anneau témoin (≥ 2 000 pixels,
   sinon `insufficient_control`) ; pixel signalé si γ < τ. Sensibilité : quantiles 0,5 % et 5 %.
6. **Statistiques par zone** — périmètre, parcelles hors périmètre, témoin, témoin 1–2 km, témoin 2–4 km : surface
   de la zone, surface observée, fraction observée, surface signalée, fraction signalée de la surface observée,
   cohérence médiane. Une zone non observée donne `null` avec une raison, jamais 0.
   **Recoupement** : le GeoTIFF des pixels signalés est relu par `roi.summarize_raster` (module existant) ; les
   surfaces observée et signalée doivent être identiques, sinon l'exécution échoue.
7. **Zones de changement** — composantes 8-connexes de pixels signalés dans le périmètre, ≥ 0,01 km² (25 pixels) ;
   les 12 plus grandes sont décrites (surface, centroïde, cohérence médiane) et vectorisées.
8. **Répétition** — par géométrie, fraction des paires de 12 jours observées où chaque pixel est signalé (les paires de
   24 jours sont affichées mais exclues). Accord inter-géométries : corrélation de Spearman des cartes dans le
   périmètre ; concordance (lift) et Jaccard des pixels signalés dans ≥ 50 % des paires.
9. **Comparaison indépendante** — Sentinel-2 avant (≤ 8 j avant la 1ʳᵉ date) et après (≤ 8 j après la 2ᵉ),
   ≥ 90 % de pixels valides ; changement optique = ‖Δρ‖₂ sur 6 bandes, seuil = quantile 99 % du témoin ;
   concordance = P(optique | radar) / P(optique | non radar) dans le périmètre. Diagnostics par zone : ΔNDVI, ΔMNDWI
   (vert/SWIR1), Δluminosité moyenne, et lecture indicative (règles : |ΔMNDWI| ≥ 0,2 et ≥ 2|ΔNDVI| → humidification
   ou assèchement ; |ΔNDVI| ≥ 0,1 → végétation ; |Δluminosité| ≥ 0,03 → matériau remanié ; sinon faible). Ces règles
   sont descriptives, non calibrées.
10. **LOS (complément)** — `displacement.los_cm_full` hérité (masque cohérence 80 m < 0,3 et composante 0), sans
    correction atmosphérique ; référence = médiane du témoin dans la composante connexe majoritaire du témoin ;
    σ = σ robuste du témoin ; surface au-delà de 3σ. Signe conforme à la convention documentée, non vérifié.
11. **Export** — GeoTIFF des signalements (0/1/255) et de la répétition, GeoJSON des zones, CSV par paire, PNG
    EPSG:3857 pour la carte, `case.json` validé par le contrat `MiningCase`.
12. **Manifeste** — commit Git, état des sources, versions des bibliothèques, SHA-256 de la configuration, des
    entrées et des sorties, durée.

## Pourquoi pas les seuils hérités

| Hérité | Domaine d'origine | Utilisation ici |
|---|---|---|
| perte de cohérence > 0,3 (`damage.CHANGE_THRESHOLD`) | événements, cercles de 5 km, cadre 044/17 juin–sept. 2026 | non utilisé |
| marges d'excès 0,11 / 0,15 | distribution nulle de cercles aléatoires | non utilisé |
| cohérence < 0,3 (`config.COHERENCE_MIN`) | masque de phase | utilisé pour la LOS uniquement (vérifié par le code) |
| `quality.split` | rejet grossier d'une paire | utilisé tel quel |

## Explications alternatives examinées

| Explication | Test dans la chaîne | Résultat (Benguerir) |
|---|---|---|
| Décorrélation de scène (pluie, rosée, saison) | seuil relatif au témoin ; médiane du témoin par paire ; ΔMNDWI médian du témoin | médiane du témoin 0,67–0,78 ; ΔMNDWI du témoin −0,035 à +0,021 : pas d'événement de scène |
| Végétation | ΔNDVI par zone | lecture « végétation » absente des zones décrites (saison sèche) |
| Eau / humidification | masque eau du produit ; ΔMNDWI | la zone la plus récurrente (≈ 0,25–0,46 km², 32,215 N 7,807 O) a une signature d'humidification/assèchement dans 5 des 10 paires comparées |
| Défaut de produit | `quality.split`, cohérence médiane | 2 paires descendantes (26 août → 19 sept.) écartées : cohérence ≈ 0,01 sur tout le cadre |
| Limite de périmètre | taux 1–2 km vs 2–4 km ; parcelles hors périmètre | pas de débordement au contact du polygone ; activité dans les parcelles de 2020 hors polygone |
| Géométrie de visée (ombre, repliement) | accord ascendant/descendant | Spearman 0,61 ; les zones fréquentes sont communes aux deux orbites |

## Ce que la méthode ne fait pas

Elle n'attribue pas de cause, ne mesure ni profondeur ni volume, et ne qualifie pas un pixel non signalé de stable.
