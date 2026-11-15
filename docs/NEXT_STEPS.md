# Suite

Ordre fixé après l'itération 2. Ne pas commencer une interprétation LOS ni un nouveau classifieur avant d'avoir une
observation indépendante datée.

1. **Vérification de la zone Z1** (fiche dans l'interface et `exports/verification_sheets.md`) : images très haute
   résolution datées encadrant les fenêtres, journal d'exploitation, visite datée, pluie et arrosage aux dates radar.
   C'est la seule voie vers un niveau « validé indépendamment ».
2. **Périmètre récent et sourcé**, indépendant des signalements radar (voir `docs/BOUNDARY.md`) ; conserver la version
   2020 et comparer, sans agrandir le polygone pour englober les zones signalées.
3. **Optique d'automne** : aucune comparaison stricte après le 9 septembre (scènes nuageuses aux dates radar). Chercher
   d'autres images datées (Landsat 8/9, commerciales) avec les mêmes critères stricts.
4. **Produits validés** : réinterroger `NISAR_L2_GUNW_V1` (vide au 2026-11-15) ; s'ils couvrent le site, les traiter
   dans un lot séparé et comparer aux provisoires (même méthode, même périmètre).
5. **GCOV (conditionnel)** : la rétrodiffusion (3 GCOV validés P05036 depuis le 25 octobre) pourrait aider à séparer
   humidification et remaniement ; à n'ajouter qu'après le point 1 et avec ses propres témoins.
6. **LOS (conditionnelle)** : soustraire l'écran ionosphérique fourni, corriger la troposphère, vérifier le signe sur un
   point de contrôle ; seulement ensuite envisager une série temporelle sur pixels cohérents.
7. **Accessibilité** : test avec lecteur d'écran (NVDA, VoiceOver) en arabe et en français.
