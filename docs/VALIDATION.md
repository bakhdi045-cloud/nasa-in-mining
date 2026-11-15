# Validation de l'extraction — 15 novembre 2026

- **34 tests réussis** avec `python -B -m unittest discover -s tests -v`.
- Paquet `nasa_in_mining-0.1.0-py3-none-any.whl` construit avec setuptools et installé dans un dossier de contrôle indépendant du code `src/`.
- Imports scientifiques, ressource `palettes.json`, commande `doctor` et catalogue vide vérifiés depuis le paquet installé.
- Les 16 empreintes source correspondent toujours à `UPSTREAM.json`. Le dépôt NASA_SAR a conservé son commit et son état Git observés avant l'extraction.

Les tests utilisent des GeoTIFF et HDF5 synthétiques : déplacement connu de 2 cm, perte de cohérence, changement de rétrodiffusion, offsets de 3 m, humidité et incertitude connues, séries temporelles, masques de qualité et statistiques sur polygones. L'absence de données est distinguée d'une mesure nulle. Les helpers externes sont contrôlés en mode hors ligne.

Le Python de l'environnement existant a servi d'interpréteur de vérification, sans installation dans cet environnement et sans écriture de bytecode. Les modules de traitement chargés proviennent du nouveau paquet. L'installation complète de toutes les dépendances dans un environnement vierge n'a pas été répétée.

| Dépendance vérifiée | Version |
|---|---|
| NumPy | 2.5.4 |
| SciPy | 1.18.1 |
| rasterio | 1.5.2 |
| pyproj | 3.8.0 |
| h5py | 3.16.0 |
| matplotlib | 3.11.2 |
| Pillow | 13.0.0 |
| requests | 2.34.2 |

Des avertissements de dépréciation d'Affine signalent l'opérateur de multiplication historique ; ils n'ont pas fait échouer les tests. Ces contrôles ne constituent ni une validation sur données minières réelles ni une certification de précision scientifique.
