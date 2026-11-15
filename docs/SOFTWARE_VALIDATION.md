# Validation logicielle — 15 novembre 2026

Ce rapport porte sur le fonctionnement du logiciel. Il ne dit rien de la justesse scientifique des résultats :
voir [SCIENTIFIC_VALIDATION.md](SCIENTIFIC_VALIDATION.md).

Environnement : Windows 10, Python 3.12.10 (`.venv` propre au dépôt), Node 24.11.1. NASA_SAR n'a été ni importé
ni modifié ; ses 16 fichiers extraits gardent les empreintes de `UPSTREAM.json` (vérifié).

## Résultats

| Contrôle | Commande | Résultat |
|---|---|---|
| Tests Python (extraction + cas minier) | `.\.venv\Scripts\python.exe -B -m unittest discover -s tests` | **56 réussis** (34 initiaux + 22 nouveaux) |
| Typage frontend | `npm run typecheck` (dans `web/`) | aucune erreur |
| Tests frontend (Vitest, jsdom) | `npm test` | **11 réussis** |
| Construction | `npm run build` | réussie (MapLibre 1,1 Mo, application 0,32 Mo, worker local) |
| Parcours navigateur (Playwright, Chromium) | `npm run e2e` | **2 réussis** : bureau 1440 × 900 et mobile 390 × 844 |
| Reproductibilité | deux exécutions de `case-run` (commits 4b97b04 puis 9c265f7) | rasters, PNG, GeoJSON, CSV et toutes les valeurs de `case.json` identiques ; seuls l'identifiant d'exécution, le commit, la durée et les empreintes des fichiers texte (fin de ligne CRLF → LF) diffèrent |
| Empreintes des sorties | relecture de `manifest.outputs` | 93/93 conformes |

## Ce que couvrent les tests

**Polygone et surfaces** — surface signalée exacte (0,25 km² = 625 pixels de 20 m) sur données synthétiques ;
recoupement automatique avec `roi.summarize_raster` à chaque paire réelle (l'exécution échoue en cas d'écart) ;
tests hérités de surfaces projetées et géodésiques.

**Nodata et zéro** — pixels non observés exclus et comptés à part (fraction observée 0,99 attendue et obtenue) ;
paire sans changement → surface signalée **mesurée égale à 0** ; cohérence mesurée 0,0 → signalée, pas « manquante » ;
zone entièrement non observée → `null` avec raison ; mesure `null` déclarée « mesurée » refusée par le contrat.

**Grilles incompatibles** — une couche de forme différente donne `incompatible_grid`, sans rééchantillonnage.

**Données insuffisantes** — témoin < 2 000 pixels → `insufficient_control` ; paire à phase plate → `rejected_quality` ;
aucun produit → cas `unavailable` valide, avec la limite « l'absence de données n'est pas une absence de changement ».

**Contrat API/frontend** — schéma JSON versionné identique au modèle ; le cas réel enregistré satisfait le contrat ;
`GET /api/cases/{id}` renvoie exactement le fichier ; erreurs JSON explicites (`case_not_found`, `file_not_found`,
`contract_violation`), traversée de chemin refusée ; côté interface, contrôle `schema_version`, parité des clés
FR/EN/AR et présence d'une traduction pour chaque clé du cas réel.

**Interface** — la surface signalée affichée égale la valeur de `case.json` (unitaire et navigateur) ; la chaîne de
provenance s'ouvre et se ferme au clavier (Échap) ; un point du graphique se sélectionne au clavier ; mesures absentes
affichées « non mesuré » avec raison ; état « aucune observation » ; erreur d'API expliquée ; repli sans WebGL.

**Hors ligne** — le parcours e2e bloque toute requête qui ne vise pas le service local : aucune n'a été émise
(polices, worker MapLibre, fond Sentinel-2 et couches sont servis localement). Le fond OpenStreetMap n'est chargé
que si l'utilisateur le choisit.

## Inspection visuelle

Captures examinées (dossier local `.playwright-mcp/`, non versionné) : anglais 1440 px, français 1280 et 820 px,
arabe 390 px (RTL : titre, navigation, carte, légendes). Pas de défilement horizontal de page à 390 px (mesuré).
Corrections faites après inspection : carte trop petite sur mobile, attribution qui masquait la carte, contraste
des signalements (cyan sur fond Sentinel-2 désaturé), ajustement de la carte à la fenêtre d'étude.

## Limites connues

- Les aperçus de cohérence (`coh_*.png`, 12 Mo) ne sont pas versionnés : sur une copie sans données, l'interface
  signale « image de couche absente » pour cette seule couche.
- Accessibilité vérifiée par structure (rôles, libellés, focus visible, clavier) et inspection, pas par un audit
  outillé (axe) ni par un lecteur d'écran.
- Les PDF imprimés ne sont pas testés automatiquement ; la feuille de style d'impression masque la carte (les
  couches restent téléchargeables) et développe les tableaux.
- Le build MapLibre dépasse 1 Mo ; pas de découpage supplémentaire.
