# NASA in Mining

Observation de sites miniers avec les produits radar NISAR : une étude exploratoire réelle (mine de phosphate de
Benguerir, Maroc, juin–octobre 2026), un pipeline reproductible, une API légère et une interface web FR/EN/AR.

**Niveau de présentation : étude exploratoire calculée, avec associations entre observations et limites explicites.**
Aucune observation de terrain n'a été utilisée ; les produits NISAR sont provisoires.

## Question et observable

Pour chaque paire d'acquisitions NISAR, quelles parties du périmètre cartographié de la mine présentent une cohérence
plus faible que celle des terrains témoins de la même paire ? L'observable est une **faible cohérence relative au
témoin**. Ce n'est ni une baisse mesurée du même pixel dans le temps, ni une surface « changée ». La cohérence dépend
des remaniements, mais aussi de l'humidité, de la végétation, du bruit, de la géométrie de visée et de la surface.

L'application ne détecte ni minerai, ni teneur, ni production, ni volume ; elle n'attribue pas de cause, ne prédit pas
de rupture et ne qualifie jamais une zone de « stable », « inactive » ou « sûre ».

## Résultat en bref (exécution publiée)

- 15 paires analysées sur 17 ; 2 écartées parce que le masque du produit déclare invalide l'acquisition du 2026-09-07.
- Le périmètre dépasse le taux du témoin (évalué hors calibration) dans les 13 paires de 12 jours, d'un facteur
  1,2 à 2,6 ; l'intervalle par blocs n'exclut 1 que pour 2 paires, et l'excès disparaît au quantile 5 %.
- Les deux orbites désignent les mêmes secteurs (5 fenêtres appariées) ; Sentinel-2, en comparaison stricte (3 paires),
  montre une association nette mais un faible recouvrement absolu.
- Une zone de 0,31 km² (Z1) est sous le seuil dans toutes les paires de 12 jours des deux orbites, avec une signature
  optique d'humidification ou d'assèchement (hypothèse) : c'est la vérification proposée en priorité.

Détails : [docs/SCIENTIFIC_VALIDATION.md](docs/SCIENTIFIC_VALIDATION.md), comparaison avec la v1 :
[docs/COMPARISON_V1_V2.md](docs/COMPARISON_V1_V2.md), méthode : [docs/METHOD.md](docs/METHOD.md), feuille de route :
[ROADMAP_DECISIONS.md](ROADMAP_DECISIONS.md), décisions : [DECISIONS.md](DECISIONS.md).

## Lancer la démonstration (Windows / PowerShell)

Prérequis : Python ≥ 3.10, Node ≥ 22. Aucune donnée scientifique, aucun jeton et aucun accès Internet ne sont
nécessaires après l'installation : le cas publié (`cases/benguerir/output/`, environ 14 Mo) est versionné.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[api,test]"
cd web; npm ci; npm run build; cd ..
.\.venv\Scripts\python.exe -m nasa_in_mining serve
```

Ouvrir http://127.0.0.1:8000. **Mode hors ligne** : l'application et le serveur local fonctionnent sans Internet
(polices, worker MapLibre, fonds Sentinel-2 datés et couches servis localement) ; seul le fond OpenStreetMap, proposé
en option, demande un accès réseau. L'état affiché est partageable par l'URL : `?lang=fr&case=…&run=…&pair=…&layer=…`.

API : `/api/health`, `/api/cases` (exécution publiée et exécutions locales vérifiées), `/api/cases/{id}?run=…`,
`/api/cases/{id}/files/{chemin}?run=…`, documentation `/api/docs`. Développement de l'interface : service sur le port
8000 puis `cd web; npm run dev`.

## Lire les résultats

1. **Question** — l'observable et ses causes possibles.
2. **Site et données** — périmètre daté (OSM 2020, pas une concession), témoins, dates radar UTC, motifs de rejet,
   couverture optique mesurée.
3. **Observations** — chaque valeur est un bouton qui ouvre sa provenance (unité, intervalle, paire, granule, DOI,
   fichiers SHA-256). Comparer la part du périmètre au **taux du témoin évalué**, lire l'intervalle, puis la table de
   sensibilité (3 quantiles × 4 témoins), l'incertitude de périmètre et la stabilité des zones.
4. **Qualité et preuves** — niveaux de preuve et leurs critères ; fenêtres appariées entre orbites ; comparaisons
   Sentinel-2 avec effectifs absolus (un rapport élevé peut reposer sur peu de pixels) ; LOS rapportée, non interprétée.
5. **Vérifications suivantes** — fiches par zone : observation, paires, hypothèses alternatives, informations à recueillir.

La carte affiche toujours la date de son fond ; un avertissement apparaît si ce fond ne correspond pas à la paire.
La vue imprimable garde une carte statique, la légende, les dates, les sources et les limites.

## Recalculer l'étude depuis les données

```powershell
.\.venv\Scripts\python.exe scripts\build_benguerir_zones.py           # zones OSM (option --fetch)
$env:EARTHDATA_TOKEN = "<jeton>"    # ou fichier .earthdata_token à la racine (ignoré par Git)
.\.venv\Scripts\python.exe scripts\fetch_benguerir_nisar.py           # inventaire CMR paginé + recadrage GUNW
.\.venv\Scripts\python.exe scripts\fetch_benguerir_sentinel2.py       # Sentinel-2 (public) + WorldCover
.\.venv\Scripts\python.exe -m nasa_in_mining case-run --case cases\benguerir --data data
.\.venv\Scripts\python.exe scripts\report_tables.py                   # tableaux de la documentation
```

Chaque exécution s'écrit dans `cases/benguerir/runs/<id>/` (non versionné) et n'est publiée dans `output/` qu'après
vérification du contrat, des fichiers et des empreintes (`--no-publish` pour ne pas publier). Les données lues
(environ 700 Mo) restent dans `data/`, ignoré par Git.

## Vérifier

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests          # 71 tests
cd web; npm run typecheck; npm test; npm run build; npm run e2e       # 14 tests unitaires, 10 parcours navigateur (axe inclus)
```

Le parcours navigateur démarre le service sur le port 8799 et nécessite une fois
`npx playwright install chromium --only-shell`. Rapport : [docs/SOFTWARE_VALIDATION.md](docs/SOFTWARE_VALIDATION.md).

## Organisation

| Dossier | Contenu |
|---|---|
| `src/nasa_in_mining/` (modules hérités) | traitements extraits de NASA_SAR, inchangés (empreintes `UPSTREAM.json`) |
| `src/nasa_in_mining/access/` | CMR et STAC paginés, lecture partielle HDF5 NISAR, Sentinel-2, WorldCover |
| `src/nasa_in_mining/mining/` | statistiques, comparaison optique, conclusions, pipeline, contrat `MiningCase` 2.0, exports |
| `src/nasa_in_mining/api.py` | FastAPI en lecture seule |
| `contract/mining_case.schema.json` | schéma JSON du contrat (source des types TypeScript générés) |
| `cases/benguerir/` | configuration, zones, inventaires datés, exécution publiée |
| `web/` | interface React + TypeScript + Vite + MapLibre |
| `docs/` | périmètre, sources, méthode, validations, comparaison v1/v2, tableaux générés |

## Sources et licences

NISAR : NASA/JPL, ASF DAAC (DOI 10.5067/NIL2GUNW-P1). Sentinel-2 : « Contains modified Copernicus Sentinel data 2026 ».
ESA WorldCover 2021 : CC BY 4.0. Zones : © OpenStreetMap contributors, ODbL. Provenance du code extrait :
[PROVENANCE.md](PROVENANCE.md) ; la licence du code amont reste à clarifier avec ses auteurs.
