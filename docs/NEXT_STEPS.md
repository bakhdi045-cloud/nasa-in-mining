# Suite : cas minier Benguerir

Question : « Quelles zones du site présentent un changement du signal radar entre les acquisitions étudiées ? »

## Entrées à obtenir

1. Un périmètre GeoJSON WGS84 vérifié et sourcé. Le centroïde de l’ancien événement n’est pas une frontière.
2. Des paires GUNW comparables : même géométrie/CRID, durées proches, cohérence exploitable et baseline disponible.
3. Les couches nécessaires aux corrections, ou un relevé explicite de ce qui manque.
4. Une comparaison indépendante datée : images optiques, relevés du site ou observations de terrain.

## Développement à effectuer

- Définir un objet `MiningCase` propre au nouveau projet, sans reprendre l’énumération des quatre cas historiques.
- Produire un raster de changement et mesurer dans l’emprise vérifiée ; ne pas reprendre la surface d’un cercle
  de 5 km en l’étiquetant « surface de la mine ».
- Comparer aux zones témoins et au fond de scène. Une perte générale de cohérence ne prouve pas une excavation.
- Documenter la sensibilité et l’incertitude sans convertir arbitrairement l’une en σ.
- Produire cartes, masque de qualité, métadonnées de source, dates et limites. Les valeurs inconnues restent
  inconnues ; une variation mesurée nulle est une vraie observation, pas un placeholder.
- Ajouter ensuite une API et une interface FR/EN/AR, avec mode hors ligne à partir de résultats réellement enregistrés.

## Critères de validation

Une démonstration de traitement sur données synthétiques n’est pas une validation de Benguerir. Pour qualifier
un cas réel : provenance des produits, emprise vérifiée, qualité suffisante, méthode d’incertitude explicite,
comparaison indépendante et limites doivent être disponibles. La conclusion doit pouvoir être « aucune
détection exploitable » sans devenir « site sûr » ni « mine inactive ».

Les données volumineuses restent hors Git. Seuls des résultats et images dont la diffusion est autorisée,
accompagnés de leur provenance, pourront alimenter une future démonstration.
