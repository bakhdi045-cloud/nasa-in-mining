# Simplification du projet après contrôle des dépendances (16 novembre 2026)

Principe : sortir du **parcours principal** ce qui ne sert pas l'étude de changements de surface de Benguerir, sans
casser ce qui est importé, testé ou nécessaire à la reproduction du cas v2. Rien n'a été supprimé : les sources et
l'historique Git restent entiers ; un élément n'est archivé que si plus rien ne l'importe.

| Élément | Qui l'utilise (vérifié par `grep` des imports et des tests) | Décision |
|---|---|---|
| LOS non interprétée (`recipes/displacement.py`, couches `los_*`, `LosPair`) | `mining/pipeline.py` (cas v2), `analysis.py`, tests | **Hors du parcours principal** : absente de l'interface d'étude (3.0) ; conservée dans le cas v2 historique, où elle est « calculée, non interprétée » |
| Recettes génériques ponctuelles (`recipes/backscatter`, `damage`, `offsets`, `soil_moisture`, `timeseries`, `wavelength`, `decompose`, `corrections`) | `analysis.py` (commande `analyze`), `tests/test_processing.py` | **Conservées en CLI avancée** ; ne servent ni de classificateur minier ni de contrôle qualité de l'étude. Heuristiques crue/végétation non utilisées |
| `exposure.py` (population / bâtiments) | `cli.py`, `tests/test_processing.py` | Conservé, hors parcours ; aucune promesse d'exposition |
| GOFF, SME2, vitesse annuelle, décomposition verticale / est-ouest | inventaires CMR seulement | Non traités ; différés |
| `catalog`, `raster`, `quality`, `roi`, `uncertainty`, `config` | cœur du dépôt, pipeline v2, tests | **Au centre** |
| Pipeline v2 (`mining/`), cas `cases/benguerir/` | référence scientifique publiée, API, interface en mode « cas historique » | Conservé tel quel (seules corrections : comptage optique par couple distinct, aperçu de cohérence masqué par `valid`) |
| `docs/COMPARISON_V1_V2.md`, `docs/generated/v1_v2_comparison.md` | `scripts/report_tables.py`, README, DECISIONS | Conservés : trace des corrections v1→v2, générée depuis les fichiers enregistrés |

Éléments d'interface : le parcours **Site → Changements → Qualité et dates → Comparaison → Conclusion** remplace
l'ancien parcours « Question → Site → Observations → Qualité → Suite » pour l'étude de surface ; l'ancien parcours reste
accessible (« Cas historique v2 ») pour relire la v2.
