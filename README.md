# NASA in Mining

Observation de sites miniers avec les produits radar NISAR : une étude de cas réelle (mine de phosphate de
Benguerir, Maroc, juin–octobre 2026), un pipeline reproductible, une API légère et une interface web FR/EN/AR.

**Question étudiée** : entre deux passages NISAR successifs, quelles zones du périmètre cartographié de la mine
montrent une perte de cohérence radar plus forte que les terrains témoins alentour ? Se répètent-elles, et sont-elles
retrouvées par l'autre orbite et par Sentinel-2 ?

**Ce que l'application ne fait pas** : détecter un minerai, une teneur, une production ou un volume extrait, attribuer
une cause à un changement, prédire une rupture, ou déclarer une zone « stable », « inactive » ou « sûre ».

## État de l'étude

| Aspect | État |
|---|---|
| Données | 17 paires NISAR GUNW **provisoires** (CRID P05023) réellement lues ; 15 analysées, 2 écartées par le contrôle qualité |
| Périmètre | polygone OpenStreetMap 2020 (39,5 km²), usage « carrière », **pas une concession** |
| Localisation des changements | concordante avec Sentinel-2 et entre les deux orbites ; **non validée sur le terrain** |
| Déplacement LOS | calculé, au niveau du bruit, signe non vérifié : non interprété |
| Cause des changements | non déterminée (une zone récurrente principale a une signature d'humidification) |

Détails : [docs/SCIENTIFIC_VALIDATION.md](docs/SCIENTIFIC_VALIDATION.md) et
[docs/SOFTWARE_VALIDATION.md](docs/SOFTWARE_VALIDATION.md). Feuille de route : [ROADMAP_DECISIONS.md](ROADMAP_DECISIONS.md) ;
décisions : [DECISIONS.md](DECISIONS.md).

## Lancer l'application (Windows / PowerShell)

Prérequis : Python ≥ 3.10, Node ≥ 22 (pour construire l'interface).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[api,test]"
cd web; npm ci; npm run build; cd ..
.\.venv\Scripts\python.exe -m nasa_in_mining serve
```

Ouvrir http://127.0.0.1:8000. Le service lit les résultats enregistrés dans `cases/*/output/` et sert l'interface
construite ; il fonctionne **hors ligne** (fond Sentinel-2, polices et couches locaux). Le fond OpenStreetMap n'est
chargé que si on le choisit dans la carte. API : `/api/health`, `/api/cases`, `/api/cases/{id}`,
`/api/cases/{id}/files/{chemin}` ; documentation interactive `/api/docs`.

Développement de l'interface : lancer le service (port 8000) puis `cd web; npm run dev` (Vite relaie `/api`).

## Reproduire l'étude depuis les données

```powershell
# 1. Zones (OpenStreetMap, déjà versionnées ; --fetch pour les réinterroger)
.\.venv\Scripts\python.exe scripts\build_benguerir_zones.py
# 2. NISAR : inventaire CMR et lecture partielle des GUNW (compte Earthdata requis)
$env:EARTHDATA_TOKEN = "<jeton>"    # ou un fichier .earthdata_token à la racine (ignoré par Git)
.\.venv\Scripts\python.exe scripts\fetch_benguerir_nisar.py
# 3. Sentinel-2 (public)
.\.venv\Scripts\python.exe scripts\fetch_benguerir_sentinel2.py
# 4. Calcul, contrôles, comparaison, exports, manifeste
.\.venv\Scripts\python.exe -m nasa_in_mining case-run --case cases\benguerir --data data
```

Les données lues (≈ 540 Mo) vont dans `data/`, ignoré par Git. Sans produit, `case-run` écrit un cas
`unavailable` explicite, jamais un résultat « sans changement ». Les aperçus de cohérence (`coh_*.png`) sont
régénérés par l'étape 4 et ne sont pas versionnés.

## Vérifier

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests     # 56 tests (données synthétiques)
cd web; npm run typecheck; npm test; npm run build; npm run e2e  # 11 tests unitaires, parcours navigateur
```

Le parcours navigateur (Playwright) démarre le service sur le port 8799 ; il nécessite
`npx playwright install chromium --only-shell` une fois.

## Organisation

| Dossier | Contenu |
|---|---|
| `src/nasa_in_mining/` (modules hérités) | traitements extraits de NASA_SAR, inchangés (empreintes `UPSTREAM.json`) |
| `src/nasa_in_mining/access/` | recherche CMR, lecture partielle HTTP des HDF5 NISAR, fenêtres Sentinel-2 |
| `src/nasa_in_mining/mining/` | zones, perte de cohérence relative au témoin, pipeline, contrat `MiningCase`, exports |
| `src/nasa_in_mining/api.py` | FastAPI en lecture seule |
| `contract/mining_case.schema.json` | schéma JSON du contrat |
| `cases/benguerir/` | configuration, zones, inventaires, résultats enregistrés |
| `web/` | interface React + TypeScript + Vite + MapLibre |
| `docs/` | périmètre, sources, méthode, validations |

## CLI

`nasa-mining` (ou `python -m nasa_in_mining`) : `doctor`, `capabilities`, `catalog`, `analyze` (recettes ponctuelles
héritées), `summarize` (raster dans un polygone), `case-run`, `contract-schema`, `serve`. Les commandes héritées et
leurs limites sont décrites dans [docs/EXTRACTION_MAP.md](docs/EXTRACTION_MAP.md) ; la recette `surface-change`
mesure toujours un cercle de 5 km et n'est pas utilisée par l'étude de cas.

## Sources et licences

NISAR : NASA/JPL, ASF DAAC (DOI 10.5067/NIL2GUNW-P1). Sentinel-2 : « Contains modified Copernicus Sentinel data 2026 ».
Zones : © OpenStreetMap contributors, ODbL. Provenance du code extrait : [PROVENANCE.md](PROVENANCE.md) ; la licence du
code amont reste à clarifier avec ses auteurs.
