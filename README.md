# NASA in Mining

Socle Python autonome pour observer les changements et déformations de sites miniers avec des produits NISAR.
Les traitements proviennent de **NISAR Pulse / NASA_SAR**, avec leur provenance et leurs limites conservées.
Ce dépôt est indépendant du dépôt source : il ne l’importe pas et n’a pas besoin de son interface ou de son API.

Cette première livraison est une **bibliothèque de traitements et une CLI**, pas encore une application web ni
une étude de Benguerir validée. Aucun résultat minier réel n’est fourni. Les tests utilisent des données
synthétiques explicitement créées pour vérifier les calculs.

## Traitements disponibles

| Traitement | Données | Utilité possible pour le projet minier |
|---|---|---|
| `surface-change` | GUNW : paires comparables de cohérence et phase | Repérer un changement du signal de surface, avec baseline et fond de scène |
| `displacement` | GUNW : phase, cohérence, composantes connexes | Mesurer un déplacement LOS autour d’un point avec référence et bruit |
| `timeseries` | Pile GUNW de même géométrie et CRID | Suivre le déplacement cumulé, conserver les ruptures de chaîne et rejets |
| `offsets` | GOFF | Examiner de grands déplacements, avec les limites du suivi de pixels |
| `flood` / `vegetation-loss` | GCOV HH/HV avant/après | Explorer des changements de rétrodiffusion ; classifications heuristiques |
| `soil-moisture` | SME2 | Contexte régional de l’humidité, sans assimilation à une mesure géotechnique |
| Corrections, longueur d’onde, qualité et bruit | Couches et métadonnées des produits | Prétraiter les signaux, documenter les corrections et rejets |
| Exposition : surface, population, bâtiments | Masque et sources auxiliaires | Calculer des indicateurs dans une zone définie, sans conclure à des dommages |
| `summarize` — **nouvel adaptateur** | GeoTIFF + polygone GeoJSON | Calculer couverture, statistiques et surface sélectionnée dans une emprise explicite |

Le détail de ce qui a été repris est dans [docs/EXTRACTION_MAP.md](docs/EXTRACTION_MAP.md).

## Installer — Windows / PowerShell

Python **3.10 ou plus récent** est nécessaire. Depuis ce nouveau dépôt :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m nasa_in_mining doctor
.\.venv\Scripts\python.exe -m nasa_in_mining capabilities
```

L’activation de `.venv` est facultative lorsque son exécutable est appelé explicitement. Sous Linux/macOS,
utiliser `.venv/bin/python`. L’installation ajoute aussi la commande `nasa-mining` dans l’environnement.

## Utiliser les produits déjà préparés

Le catalogue lit le format d’extraction de NISAR Pulse :

```text
data/
  GUNW/<nom complet du produit>/_DONE
                                *unwrappedPhase.tif
                                *coherenceMagnitude.tif
                                *connectedComponents.tif
                                radar_geometry.npz        (si disponible)
  GCOV/<produit>/_DONE, *HHHH.tif, *HVHV.tif
  GOFF/<produit>/_DONE, *alongTrackOffset.tif, ...
  SME2/<produit>/_DONE, <produit>.h5
```

Les fichiers réels ne sont pas embarqués. Aucun téléchargement de produits n’est automatique. On peut
utiliser un dossier de données existant **sans le copier dans ce dépôt** :

```powershell
.\.venv\Scripts\python.exe -m nasa_in_mining catalog --data "D:\nisar_data" --level GUNW
```

Une analyse ponctuelle, avec le point indicatif de Benguerir déjà utilisé en amont :

```powershell
.\.venv\Scripts\python.exe -m nasa_in_mining analyze --data "D:\nisar_data" --recipe surface-change --lat 32.25825 --lon -7.82355 --output outputs\surface-change.json
```

**Ce point n’est pas une limite de carrière vérifiée.** La recette héritée `surface-change` mesure un cercle
de 5 km, explicitement identifié dans la réponse. Son résultat ne doit pas être présenté comme la surface
de toute la mine. Les PNG produits se trouvent dans `.cache/nasa-in-mining/layers/` ; les champs `/layers/...`
sont des descripteurs pour une future API, aucun serveur HTTP n’est inclus.

Les autres recettes se choisissent avec `--recipe displacement`, `timeseries`, `offsets`, `flood`,
`vegetation-loss` ou `soil-moisture`. `--event 2026-01-20` signifie une journée entière ; un instant exact
doit porter une heure et son fuseau, par exemple `2026-01-20T12:00:00Z`.

Sans données, le catalogue retourne `[]` et l’analyse retourne `status: no_coverage`, avec le code de sortie 2.
Elle ne fabrique pas une mesure nulle. Les échecs de qualité ou d’historique retournent `insufficient_data`.

## Statistiques à l’intérieur d’un polygone minier

Fournir un **vrai polygone vérifié**, au format GeoJSON WGS84, et un raster de signal existant :

```powershell
.\.venv\Scripts\python.exe -m nasa_in_mining summarize --raster "D:\results\coherence-loss.tif" --roi "D:\boundaries\mine.geojson" --unit coherence --threshold 0.3 --output outputs\roi-statistics.json
```

Le seuil de cette commande est un exemple explicite de sélection, pas une calibration minière. La réponse
contient les pixels observables, leur fraction, les statistiques du signal et la surface sélectionnée.
Les surfaces projetées tiennent compte des unités du CRS ; les grilles géographiques nord-en-haut utilisent
une surface géodésique par ligne. Un CRS projeté approprié limite la distorsion des surfaces.

Les pixels sont sélectionnés par leur centre. Une petite emprise sous-pixel peut donc n’avoir aucun échantillon.
L’état `no_data` ne signifie pas « terrain stable ». `uncertainty: null` indique qu’aucune incertitude de
classification n’a été estimée, et ne doit pas être remplacé par un faux σ ou un label « exact ».

La CLI analyse le raster fourni ; elle ne transforme pas automatiquement les résultats circulaires hérités en
une classification minière sur polygone. Cette intégration sera l’étape suivante.

## Configuration

Les variables doivent être définies **avant** d’importer les modules ou de lancer la CLI.

| Variable | Valeur par défaut / rôle |
|---|---|
| `MINING_DATA` | `./data`, ou `--data` sur la commande |
| `MINING_CACHE` | `./.cache/nasa-in-mining`, ou `--cache` |
| `MINING_AUX` | `<data>/auxiliary`, compatible Windows |
| `MINING_OFFLINE` | `1` : helpers externes hors ligne par défaut ; `--online` autorise leurs accès optionnels |
| `MINING_LOS_SIGN` | `1`, convention documentée ; `-1` uniquement si justifié |
| `MINING_LOS_SIGN_VERIFIED` | `0`, sans prétendre qu’un contrôle local a été effectué |
| `MINING_DATA_GAPS` | `[]`, aucune lacune marocaine imposée à un nouveau site |
| `NISAR_CORRECTIONS` | `iono` hérité ; `iono,tropo,tide` ou `none` selon validation scientifique |
| `NISAR_DEM` | Chemin local, `none` ou `glo30` ; le défaut hors ligne utilise une hauteur constante documentée |

Les alias `NISAR_DATA`, `NISAR_CACHE`, `NISAR_AUX`, `NISAR_OFFLINE` et de signe restent acceptés,
avec priorité aux `MINING_*`. Les paramètres scientifiques avancés des recettes gardent leur nom `NISAR_*`.
Le fichier `.env.example` sert de documentation ; il n’est pas chargé automatiquement.

## Vérifier

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Les tests couvrent notamment le calcul de déplacement avec fréquence du produit, la détection de changement,
les séries courtes, la qualité, l’absence de couverture, les polygones, les surfaces géographiques et le mode
hors ligne. Ils ne prouvent pas la validité des résultats sur une mine réelle.
Le compte rendu de cette extraction est dans [docs/VALIDATION.md](docs/VALIDATION.md).

## Limites conservées

- Changement radar ne signifie pas automatiquement excavation, dommage ou production.
- Les seuils de cohérence hérités ont un domaine de calibration particulier, décrit dans `recipes/damage.py`.
- La direction LOS reste non vérifiée tant qu’un contrôle indépendant n’a pas été fait.
- Les recettes ponctuelles héritées supposent des grilles métriques carrées ; la façade les refuse sinon.
- Une vitesse annuelle n’est rapportée qu’à partir de 365 jours d’historique ; une chaîne coupée n’est pas comblée.
- La décomposition ascendante/descendante est extraite, mais ne fournit pas encore de σ propagé.
- Les variations de seuil/contour de l’exposition sont des sensibilités ; la forme historique `sigma: 1` de
  `to_case_exposure` ne constitue pas une calibration statistique. Ne pas l’utiliser comme preuve de précision.
- SME2 ne mesure ni la pression interstitielle d’une digue ni sa chimie ; GOFF ne prédit pas une rupture.
- Aucun traitement extrait ne localise directement un gisement, une teneur ou un volume extrait.

## Origine et suite

[PROVENANCE.md](PROVENANCE.md) décrit l’origine, les adaptations et le statut de licence observé.
[UPSTREAM.json](UPSTREAM.json) donne le commit source et les empreintes SHA-256 des 16 fichiers.
[docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) propose la suite pour une étude de Benguerir vérifiable.
