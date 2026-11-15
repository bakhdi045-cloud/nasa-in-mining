# Périmètre étudié — Benguerir

Fichier : [`cases/benguerir/zones.geojson`](../cases/benguerir/zones.geojson), produit par
`python scripts/build_benguerir_zones.py` (option `--fetch` pour réinterroger Overpass).

## Périmètre principal (`study`)

| Élément | Valeur |
|---|---|
| Source | OpenStreetMap, way [638354631](https://www.openstreetmap.org/way/638354631), `landuse=quarry` |
| Date | version 3 du 2020-02-10 (v1 2018-10-26, Potlatch 2 ; v2 2020-02-07 « Mise à jour zone laverie OCP Ben Guerir » ; v3 « OCP mine ») |
| Méthode | digitalisation par contributeurs ; v2 et v3 déclarent l'imagerie Esri World Imagery (iD 2.17.1) |
| Extraction | Overpass API, base OSM du 2026-11-15T02:33Z ; historique par l'API OSM v0.6 |
| Surface | 39,548 km² (EPSG:32629) ; 209 nœuds ; emprise 32,2002–32,3119 N, 7,8711–7,7841 O |
| Précision | non publiée ; dépend de l'imagerie et du contributeur ; visuellement cohérente à quelques dizaines de mètres avec Sentinel-2 (20 m) du 2026-11-01 |
| Droits | ODbL 1.0, attribution « © OpenStreetMap contributors » ; le polygone dérivé reste sous ODbL |
| Nature | emprise cartographiée d'un usage du sol « carrière » ; **ni concession, ni limite légale, ni emprise exploitée 2026** |

## Zones complémentaires

- **Parcelles hors périmètre** (`panels_outside`) : union des 853 multipolygones OSM `landuse=industrial` nommés
  P1S, P2, P4, P5, P7 (2020, contributeur unique, changeset `source=knowledge`, « Mise à jour zone mine Ben Guerir »)
  moins le polygone principal : 2,388 km². Leur signification (panneaux, tranches) n'est pas confirmée.
- **Anneau témoin** (`control`) : 1 à 4 km du périmètre, moins les zones OSM résidentielles, industrielles,
  commerciales, en construction, militaires (base aérienne de Ben Guerir), universitaires (UM6P), eau et autres
  carrières, élargies de 100 m : 146,461 km². Sous-zones 1–2 km et 2–4 km calculées par le pipeline.
- **Exclusions** (`exclusions`) : union simplifiée des 893 objets exclus du témoin.

## Limites

1. Le polygone a six ans : l'emprise exploitée a pu évoluer. Les bandes visibles à l'est sur Sentinel-2 2026 sont
   en partie hors polygone (couvertes par les parcelles).
2. Le polygone inclut des zones non excavées (pistes, installations de traitement au nord-ouest, verses) : la
   « surface du périmètre » n'est pas la surface excavée.
3. Les sélections de pixels se font par centre de pixel (20 m) : effet de bord ≤ 10 m.
4. L'absence de signalement dans une partie du polygone ne dit rien de son statut d'exploitation.

## Critère de passage D1

Satisfait pour la question D0 : source, date, méthode, droits et limites documentés ; couverture radar confirmée par
téléchargement réel (17 paires, 100 % de la surface du périmètre observable sur chaque paire retenue). Non satisfait
pour un usage réglementaire : aucune limite officielle n'a été obtenue.

## Mise à jour v2 (15 novembre 2026)

**Versions de périmètre conservées** (`perimeter_versions` dans `case.json`) :

| Version | Usage | Surface (pixels 20 m) |
|---|---|---|
| OSM way 638354631 v3 (2020-02-10) | principale | voir `case.json` |
| moins un pixel de 20 m | sensibilité (placement de la limite) | idem |
| plus un pixel de 20 m | sensibilité | idem |
| plus parcelles OSM 2020 | sensibilité ; sémantique des parcelles non confirmée | idem |

Le périmètre n'est **pas agrandi** pour englober les zones signalées par le radar.

**Recherche d'une emprise récente indépendante** : l'élément OSM est toujours à la version 3 du 2020-02-10 (API OSM
interrogée le 2026-11-15). Aucune limite récente publiée et réutilisable n'a été trouvée. Pistes, à documenter avant
usage : cartographie optique datée de 2026 indépendante des signalements radar (photo-interprétation de Sentinel-2 ou
d'images très haute résolution, avec protocole et date), ou limite fournie par l'exploitant ou l'administration.
ESA WorldCover 2021 sert seulement à stratifier les témoins : il ne délimite pas la mine.
