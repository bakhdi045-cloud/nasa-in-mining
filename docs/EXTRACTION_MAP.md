# Carte d’extraction

Les 16 fichiers sources et leurs adaptations exactes sont recensés dans `UPSTREAM.json`.

| Source NASA_SAR | Destination `src/nasa_in_mining/` | Rôle |
|---|---|---|
| `backend/catalog.py` | `catalog.py` | Produits locaux, géométrie, dates, CRID, sélection temporelle |
| `backend/raster.py` | `raster.py` | Lecture, fenêtres, profils, reprojection et export PNG |
| `backend/quality.py` | `quality.py` | Rejet de phase plate et cohérence insuffisante |
| `backend/uncertainty.py` | `uncertainty.py` | Bruit robuste et règles de confiance héritées |
| `backend/palettes.json` | `palettes.json` | Palettes originales des cartes |
| `backend/recipes/__init__.py` | `recipes/__init__.py` | Organisation des recettes |
| `backend/recipes/wavelength.py` | `recipes/wavelength.py` | Longueur d’onde propre au produit, avec fallback expliqué |
| `backend/recipes/corrections.py` | `recipes/corrections.py` | Ionosphère, troposphère, marée et sources des corrections |
| `backend/recipes/displacement.py` | `recipes/displacement.py` | Déplacement LOS et référence |
| `backend/recipes/timeseries.py` | `recipes/timeseries.py` | Séries cumulées et cartes de vitesse sous conditions |
| `backend/recipes/decompose.py` | `recipes/decompose.py` | Décomposition verticale / est-ouest, encore sans σ propagé |
| `backend/recipes/damage.py` | `recipes/damage.py` | Changement de surface, malgré le nom historique du module |
| `backend/recipes/backscatter.py` | `recipes/backscatter.py` | Heuristiques GCOV eau / végétation |
| `backend/recipes/offsets.py` | `recipes/offsets.py` | Grands déplacements GOFF |
| `backend/recipes/soil_moisture.py` | `recipes/soil_moisture.py` | Lecture et séries SME2 |
| `backend/science/exposure.py` | `exposure.py` | Surfaces, population, bâtiments et variantes de masque |

## Dépendances préservées

```text
catalog ────────────── configuration locale
raster ─────────────── cache local + palettes
quality ────────────── uncertainty
displacement ───────── raster + wavelength + corrections
timeseries ─────────── catalog + quality + displacement
surface change ─────── catalog + quality + raster
backscatter / offsets  catalog + raster
soil moisture ──────── catalog + raster + HDF5
exposure ───────────── rasters + géodésie + sources auxiliaires optionnelles
```

Les dépendances Python déclarées sont NumPy, SciPy, Rasterio, PyProj, h5py, Matplotlib, Pillow et Requests.
FastAPI, Anthropic, XGBoost, scikit-learn, Node et React ne sont pas nécessaires pour ce socle extrait.

## Nouveaux points d’entrée

- CLI : `nasa-mining` ou `python -m nasa_in_mining`.
- Analyse ponctuelle : `nasa_in_mining.analysis.analyze_point`.
- Statistiques par polygone : `nasa_in_mining.roi.summarize_raster`.
- Les fonctions d’origine restent importables depuis les modules du nouveau paquet.

L’analyse ponctuelle et les statistiques par polygone sont deux opérations distinctes. La présence d’un
polygone dans le nouveau projet ne remplace pas les cercles et références spatiales internes des recettes
héritées. Une future analyse minière devra expliciter ce raccordement.
