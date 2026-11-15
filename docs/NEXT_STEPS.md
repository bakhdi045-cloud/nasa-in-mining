# Suite

L'étude de cas Benguerir est réalisée (voir `docs/SCIENTIFIC_VALIDATION.md`). Ce qui la ferait progresser, par
ordre d'effet attendu sur le niveau de preuve :

1. **Vérité terrain datée** : visites ou images très haute résolution aux points proposés par l'interface
   (« Vérifications suivantes »), calendrier d'exploitation de l'exploitant. Sans elles, la cause des changements
   reste inconnue et aucun observable n'est « validé indépendamment ».
2. **Périmètre 2026** : les parcelles minières cartographiées hors du polygone de 2020 sont actives. Un périmètre
   récent et sourcé (exploitant, administration, ou cartographie optique documentée) remplacerait l'emprise OSM.
3. **Produits validés** : relancer `case-run` quand des GUNW validés (CRID définitif, collection `NISAR_L2_GUNW_V1`)
   couvriront le site ; comparer les résultats à ceux des produits provisoires.
4. **Couverture optique d'automne** : aucune paire après le 9 septembre n'a de scènes Sentinel-2 claires à moins de
   8 jours ; ajouter Landsat 8/9 ou des images commerciales datées.
5. **LOS** : soustraire l'écran ionosphérique fourni dans les GUNW, corriger la troposphère, vérifier le signe sur un
   point de contrôle, puis seulement construire une série temporelle sur les pixels cohérents (verses).
6. **Rétrodiffusion GCOV** : second observable (eau, matériau remanié) pour distinguer humidification et excavation.
7. **Accessibilité** : audit outillé (axe) et test avec lecteur d'écran.
