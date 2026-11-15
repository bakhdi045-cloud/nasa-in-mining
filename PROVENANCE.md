# Provenance des traitements

Les traitements extraits sont issus du projet collectif **NISAR Pulse / NASA_SAR**, équipe The SAR :

- Dépôt : https://github.com/AYmANTwill/NASA_SAR
- Révision inspectée : `9fbac7311da026149243ff3fb5a25adc7188dbab`.
- Emplacement amont : `backend/`, particulièrement `recipes/` et `science/exposure.py`.
- La paternité du code existant reste celle des contributeurs du dépôt amont ; cette extraction ne présente
  pas ces algorithmes comme de nouvelles créations d’Adam.

Le manifeste [UPSTREAM.json](UPSTREAM.json) conserve, pour chaque fichier, son chemin source, son SHA-256 avant
extraction, son chemin de destination et son SHA-256 adapté. Le commit identifie le contexte amont ; les
empreintes décrivent exactement les octets lus dans la copie de travail au moment de l’extraction.

## Adaptations explicites

1. Les imports de `config`, `catalog`, `raster`, `quality`, `uncertainty` et `recipes` sont qualifiés par le
   paquet `nasa_in_mining`. Les fins de ligne des fichiers Python et JSON extraits sont normalisées en LF,
   avec une règle Git pour conserver les mêmes empreintes sous Windows et Linux.
2. La configuration est nouvelle et autonome. Elle ne contient aucun identifiant Earthdata ou clé LLM.
3. Les dossiers de données/cache sont locaux au projet exécuté ou configurés explicitement ; aucun chemin
   d’exécution vers le checkout NASA_SAR n’est nécessaire.
4. Le cache auxiliaire s’appelle `auxiliary`, plutôt que `aux` (nom réservé sous Windows).
5. Les accès auxiliaires externes sont hors ligne par défaut, avec activation explicite possible.
6. La lacune d’acquisition marocaine de juillet 2026 n’est pas appliquée automatiquement à d’autres sites.
7. Le User-Agent HTTP du module d’exposition identifie ce nouveau projet.

Les formules et critères numériques des modules extraits sont conservés. Les limitations connues ne sont
pas supprimées parce que le contexte devient minier. Le contrôle de grille dans `analysis.py` évite d’appeler
les fenêtres métriques héritées sur des pixels en degrés ou des grilles incompatibles.

Les modules `config.py`, `analysis.py`, `roi.py`, `cli.py`, les tests et cette documentation sont les ajouts
d’adaptation de ce dépôt. `roi.py` fournit de nouvelles statistiques spatiales génériques, sans classifier
la cause d’un changement et sans produire d’incertitude statistique supposée.

## Ce qui n’a pas été transféré

- Les interfaces `frontend/` et `frontend-v2/`, leurs composants et plugins.
- Les serveurs FastAPI, l’agent conversationnel, les clés et la configuration de fournisseurs LLM.
- Le téléchargeur `download_all.py` et ses identifiants intégrés signalés dans le projet amont.
- Les modèles de faille, inversions de magnitude et scénarios séisme/flood particuliers.
- Les données brutes, produits traités, caches de réponses, `.env`, environnements Python et historique Git amont.
- Une prétendue limite validée de la mine de Benguerir ou des résultats miniers « réels » issus de fixtures.

## Licence observée

Aucun fichier de licence du projet/backend n’a été trouvé dans la révision amont inspectée. Le fichier de
licence présent dans un skill de frontend tiers n’est pas une licence du backend. Aucune licence MIT, Apache,
ni qualification « domaine public NASA » n’est attribuée aux traitements extraits. Le champ de licence du
nouveau paquet est donc laissé non renseigné ; les conditions de réutilisation restent à clarifier avec les
auteurs du code amont. Ce document consigne la provenance et n’accorde pas une licence.

## Refaire ou contrôler l’extraction

```powershell
python scripts/extract_upstream.py --source "..\NASA_SAR" --dry-run
python scripts/extract_upstream.py --source "..\NASA_SAR"
```

Le script ne fait qu’ouvrir les fichiers source en lecture. Il écrit uniquement les destinations énumérées
dans ce dépôt et son manifeste. Il refuse une source imbriquée dans la destination, protège les modifications
locales des fichiers déjà extraits et vérifie que les octets source n’ont pas changé pendant son exécution.
La lecture de Git utilise une exception `safe.directory` limitée à la commande, sans configuration globale.
